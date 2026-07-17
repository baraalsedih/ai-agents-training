"""Consistency-auditor agent -- Session 5.

Scans the Session 3 knowledge base *itself* (not one new document) for four
kinds of problems that accumulate naturally as an archive grows: near-
duplicate chunks, contradicting decisions/evidence, open questions with no
resolving decision or evidence nearby (gaps), and inconsistent terminology
across documents. Reuses Session 3's config, embedding model, and chat
model directly -- no separate model stack, no separate knowledge base.

Usage:
    python3 consistency_auditor.py                    # full audit
    python3 consistency_auditor.py --category decision # scope the audit to one category
    python3 consistency_auditor.py --yes                # skip the confirmation prompt

Everything runs locally through Ollama -- no external API calls. The
auditor only ever *suggests* -- see the report's closing note and chapter 3
of the Session 5 handbook for why nothing here rewrites the archive
automatically.
"""

import argparse
import itertools
import json
import sys
import warnings
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Literal, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

# labs/session3/ is a sibling of labs/session5/, not an installed package --
# add it to sys.path before importing its config, exactly like Session 4's
# nodes.py already does for the same reason.
SESSION3_DIR = Path(__file__).resolve().parent.parent.parent / "session3"
sys.path.insert(0, str(SESSION3_DIR))

import config as kb_config  # noqa: E402 -- Session 3's knowledge-base config

import numpy as np  # noqa: E402
from langchain_chroma import Chroma  # noqa: E402
from langchain_ollama import ChatOllama, OllamaEmbeddings  # noqa: E402
from pydantic import BaseModel, Field, create_model  # noqa: E402

# session6: tracing added -- labs/session6/ is a sibling directory, not an
# installed package, same import convention this lab already uses for
# labs/session3/.
SESSION6_DIR = Path(__file__).resolve().parent.parent.parent / "session6"
sys.path.insert(0, str(SESSION6_DIR))
import tracing  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
GLOSSARY_PATH = Path(__file__).resolve().parent.parent / "glossary.json"

# ------------------------------------------------------------------------
# Tunables -- calibrated against this lab's real fictional-startup archive (see the
# Session 5 handbook, chapter 3, for the actual distance numbers). Distances
# are Chroma's own similarity_search_with_score output, the same metric
# Session 4's suggest_links already uses -- not a separately computed one.
# ------------------------------------------------------------------------
NEIGHBOR_K = 5  # neighbors considered per chunk when generating candidates
DUPLICATE_DISTANCE_MAX = 0.20  # near word-for-word restatements land well under this
CONTRADICTION_DISTANCE_MAX = 0.42  # deliberately generous -- see note below
GAP_NEARBY_HINT = 0.20  # nearest decision/evidence closer than this gets a "maybe already addressed" hint
TERM_SIMILARITY_MIN = 0.86  # cosine similarity between two candidate-term embeddings to cluster them

# ------------------------------------------------------------------------
# Structured-output schemas -- one Pydantic model per judgment the local
# LLM is asked to make. Candidate generation (embeddings) proposes pairs;
# these schemas are how the LLM confirms or rejects each candidate.
# ------------------------------------------------------------------------
class DuplicateJudgment(BaseModel):
    verdict: Literal["duplicate", "rephrase", "different"] = Field(
        description="'duplicate' if near word-for-word the same content, 'rephrase' if the "
        "same fact/decision stated in different words, 'different' if they are not actually "
        "the same information even though the topic overlaps"
    )
    explanation: str = Field(description="One short sentence justifying the verdict")


class ContradictionJudgment(BaseModel):
    verdict: Literal["contradict", "compatible", "unrelated"] = Field(
        description="'contradict' if the two chunks make incompatible claims about the same "
        "specific topic, 'compatible' if they are about the same topic but do not conflict, "
        "'unrelated' if they are not actually about the same topic"
    )
    explanation: str = Field(description="One short sentence justifying the verdict")


class TermExtraction(BaseModel):
    terms: list[str] = Field(
        description="2-5 short recurring domain terms or key phrases mentioned in this chunk "
        "(feature names, pricing-model names, decision topics). Each term 1-4 words, written "
        "in the chunk's own language."
    )


def _cluster_judgment_model(variants: list):
    # canonical_term is constrained to the EXACT variants seen (Literal enum,
    # schema-enforced) rather than freely generated -- a small local model
    # asked to freely write a new Arabic phrase here would sometimes produce
    # garbled, non-existent text instead of picking a real option (observed
    # during testing). Picking from a fixed list removes that failure mode.
    return create_model(
        "TermClusterJudgment",
        are_synonyms=(bool, Field(description="True if these candidate terms genuinely refer to the same underlying concept")),
        canonical_term=(Literal[tuple(variants)], Field(description="The clearest variant to standardize on, chosen from the exact list given")),
        explanation=(str, Field(description="One short sentence justifying the decision")),
    )


# ------------------------------------------------------------------------
# Prompts -- English instructions, same convention as Session 3's
# CLASSIFICATION_PROMPT: English instructions work fine on non-English
# (e.g. Arabic) source text.
# ------------------------------------------------------------------------
DUPLICATE_PROMPT = """You are auditing a founder's strategic knowledge base for duplicate or near-duplicate content.

Compare the two chunks below and decide whether they express the same underlying information.

Chunk A:
\"\"\"{text_a}\"\"\"

Chunk B:
\"\"\"{text_b}\"\"\"

Classify the relationship as exactly one of: duplicate, rephrase, or different. Then write one short sentence explaining your verdict."""

CONTRADICTION_PROMPT = """You are auditing a founder's strategic knowledge base for contradictions between recorded decisions and evidence.

Compare the two chunks below, which come from different points in the archive.

Chunk A ({category_a}):
\"\"\"{text_a}\"\"\"

Chunk B ({category_b}):
\"\"\"{text_b}\"\"\"

Classify the relationship as exactly one of: contradict (incompatible claims about the same specific topic -- e.g. two different decisions about the same question), compatible (same topic, no real conflict -- e.g. one adds detail to the other), or unrelated (not actually about the same topic). Then write one short sentence explaining your verdict."""

TERM_EXTRACTION_PROMPT = """Read the chunk below from a founder's strategic archive and extract the recurring domain terms it uses -- names for features, pricing models, customer segments, or decision topics. Skip generic words.

Chunk:
\"\"\"{text}\"\"\""""

TERM_CANONICAL_PROMPT = """These phrases were all found in a founder's knowledge base, possibly describing the same recurring concept: {variants}

If they truly refer to the same underlying concept, pick the clearest and most standard phrase as the single canonical term to standardize on, and confirm they are synonyms. If they are not actually the same concept, say so."""


# ------------------------------------------------------------------------
# Knowledge-base access
# ------------------------------------------------------------------------
def build_resources():
    embeddings = OllamaEmbeddings(model=kb_config.EMBEDDING_MODEL)
    llm = ChatOllama(model=kb_config.CHAT_MODEL, temperature=0)
    vectorstore = Chroma(
        collection_name=kb_config.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(kb_config.CHROMA_DIR),
    )
    return embeddings, llm, vectorstore


def load_chunks(vectorstore, category_filter: Optional[str] = None) -> list:
    raw = vectorstore.get(include=["metadatas", "documents"])
    chunks = [
        {"id": id_, "text": text, **meta}
        for id_, text, meta in zip(raw["ids"], raw["documents"], raw["metadatas"])
    ]
    if category_filter:
        chunks = [c for c in chunks if c.get("category") == category_filter]
    return chunks


def _chunk_key(source: str, text: str) -> tuple:
    # Chroma's similarity_search_with_score returns Documents (metadata +
    # content) without their stored id, so pairs are de-duplicated by
    # (source file, text prefix) instead -- a collision would require two
    # chunks from the same file starting with the same 60 characters, which
    # would itself be worth flagging as a duplicate anyway.
    return (source, text[:60])


# ------------------------------------------------------------------------
# 1. Duplicates
# ------------------------------------------------------------------------
def find_duplicate_candidates(vectorstore, chunks: list) -> list:
    """Candidate generation via Chroma's own nearest-neighbor search, scoped
    to each chunk's OWN category and to its top NEIGHBOR_K neighbors --
    never a full N^2 scan of every possible pair in the archive. On a large
    knowledge base this keeps candidate generation to O(N * k) vector
    lookups (cheap, no LLM call) instead of O(N^2); only the much smaller
    surviving candidate set below the distance cutoff goes to the LLM."""
    seen, candidates = set(), []
    for chunk in chunks:
        results = vectorstore.similarity_search_with_score(
            chunk["text"], k=NEIGHBOR_K, filter={"category": chunk["category"]}
        )
        for doc, distance in results:
            if doc.page_content == chunk["text"] or distance > DUPLICATE_DISTANCE_MAX:
                continue
            key = frozenset([_chunk_key(chunk["source"], chunk["text"]), _chunk_key(doc.metadata["source"], doc.page_content)])
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"a": chunk, "b": {"text": doc.page_content, **doc.metadata}, "distance": distance})
    return candidates


def confirm_duplicates(llm, candidates: list) -> list:
    structured_llm = llm.with_structured_output(DuplicateJudgment)
    confirmed = []
    for c in candidates:
        # session6: tracing added
        result = tracing.traced_llm_call(
            structured_llm, DUPLICATE_PROMPT.format(text_a=c["a"]["text"], text_b=c["b"]["text"]), agent="consistency_auditor", purpose="confirm_duplicate"
        )
        if result.verdict in ("duplicate", "rephrase"):
            confirmed.append({**c, "verdict": result.verdict, "explanation": result.explanation})
    return confirmed


# ------------------------------------------------------------------------
# 2. Contradictions
# ------------------------------------------------------------------------
def find_contradiction_candidates(vectorstore, chunks: list) -> list:
    """Same neighbor-search strategy as duplicates, but restricted to the
    decision/evidence subset of the archive (contradictions can only really
    happen between claims, not ideas or open questions) and with a more
    generous distance cutoff. Calibration against this lab's real archive
    showed that two chunks stating opposite decisions about the same topic
    don't always land as tight neighbors the way near-duplicate phrasing
    does -- so this step deliberately favors recall (catching the real
    contradiction) over precision, and leaves precision to the LLM
    confirmation step below."""
    pool = [c for c in chunks if c["category"] in ("decision", "evidence")]
    seen, candidates = set(), []
    for chunk in pool:
        results = vectorstore.similarity_search_with_score(
            chunk["text"], k=NEIGHBOR_K, filter={"category": {"$in": ["decision", "evidence"]}}
        )
        for doc, distance in results:
            if doc.page_content == chunk["text"] or distance > CONTRADICTION_DISTANCE_MAX:
                continue
            key = frozenset([_chunk_key(chunk["source"], chunk["text"]), _chunk_key(doc.metadata["source"], doc.page_content)])
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "a": chunk,
                    "b": {"text": doc.page_content, **doc.metadata},
                    "distance": distance,
                }
            )
    return candidates


def confirm_contradictions(llm, candidates: list) -> list:
    structured_llm = llm.with_structured_output(ContradictionJudgment)
    confirmed = []
    for c in candidates:
        # session6: tracing added
        result = tracing.traced_llm_call(
            structured_llm,
            CONTRADICTION_PROMPT.format(
                text_a=c["a"]["text"], category_a=c["a"]["category"], text_b=c["b"]["text"], category_b=c["b"]["category"]
            ),
            agent="consistency_auditor",
            purpose="confirm_contradiction",
        )
        if result.verdict == "contradict":
            confirmed.append({**c, "verdict": result.verdict, "explanation": result.explanation})
    return confirmed


# ------------------------------------------------------------------------
# 3. Gaps -- no LLM call needed, purely structural (nearest decision/
# evidence neighbor distance for each open question).
# ------------------------------------------------------------------------
def find_gaps(vectorstore, chunks: list) -> list:
    open_questions = [c for c in chunks if c["category"] == "open_question"]
    gaps = []
    for oq in open_questions:
        results = vectorstore.similarity_search_with_score(
            oq["text"], k=1, filter={"category": {"$in": ["decision", "evidence"]}}
        )
        nearest_doc, distance = results[0] if results else (None, None)
        gaps.append(
            {
                "chunk": oq,
                "nearest_distance": distance,
                "nearest_source": nearest_doc.metadata.get("source") if nearest_doc else None,
                "nearest_summary": nearest_doc.metadata.get("summary") if nearest_doc else None,
                "likely_addressed": distance is not None and distance < GAP_NEARBY_HINT,
            }
        )
    # Most isolated (largest nearest-neighbor distance, or no decision/
    # evidence in scope at all) first -- treated as the highest-priority
    # gap, since nothing in the archive comes close to resolving it.
    gaps.sort(key=lambda g: g["nearest_distance"] if g["nearest_distance"] is not None else float("inf"), reverse=True)
    return gaps


# ------------------------------------------------------------------------
# 4. Terminology unification
# ------------------------------------------------------------------------
def extract_terms(llm, chunks: list) -> dict:
    structured_llm = llm.with_structured_output(TermExtraction)
    occurrences = defaultdict(list)
    for chunk in chunks:
        # session6: tracing added
        result = tracing.traced_llm_call(structured_llm, TERM_EXTRACTION_PROMPT.format(text=chunk["text"]), agent="consistency_auditor", purpose="extract_terms")
        for term in result.terms:
            normalized = term.strip().lower()
            if normalized:
                occurrences[normalized].append({"term": term.strip(), "source": chunk["source"], "category": chunk["category"]})
    return occurrences


def cluster_terms(embeddings_model, occurrences: dict) -> list:
    """Clusters the small set of DISTINCT candidate terms by embedding
    similarity -- a full pairwise comparison here is cheap because it runs
    over unique terms (typically a few dozen even on a large archive), not
    over every chunk pair."""
    unique_terms = list(occurrences.keys())
    if len(unique_terms) < 2:
        return []

    vectors = np.array(embeddings_model.embed_documents(unique_terms))
    normalized = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    similarity = normalized @ normalized.T

    parent = list(range(len(unique_terms)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i, j in itertools.combinations(range(len(unique_terms)), 2):
        if similarity[i, j] >= TERM_SIMILARITY_MIN:
            union(i, j)

    clusters = defaultdict(list)
    for i, term in enumerate(unique_terms):
        clusters[find(i)].append(term)
    return [members for members in clusters.values() if len(members) > 1]


def suggest_canonical_terms(llm, clusters: list, occurrences: dict) -> list:
    glossary = []
    for cluster in clusters:
        variants = sorted({o["term"] for norm_term in cluster for o in occurrences[norm_term]})
        structured_llm = llm.with_structured_output(_cluster_judgment_model(variants))
        # session6: tracing added
        result = tracing.traced_llm_call(
            structured_llm, TERM_CANONICAL_PROMPT.format(variants=", ".join(variants)), agent="consistency_auditor", purpose="canonicalize_terms"
        )
        if result.are_synonyms:
            glossary.append(
                {
                    "canonical_term": result.canonical_term,
                    "variants": variants,
                    "occurrences": sum(len(occurrences[t]) for t in cluster),
                    "explanation": result.explanation,
                }
            )
    return glossary


def save_glossary(glossary: list) -> Path:
    # Only a proposal file is written -- no chunk text in the knowledge
    # base is ever rewritten automatically. A human decides whether/how to
    # apply each suggestion.
    GLOSSARY_PATH.write_text(json.dumps(glossary, ensure_ascii=False, indent=2), encoding="utf-8")
    return GLOSSARY_PATH


# ------------------------------------------------------------------------
# Report composition
# ------------------------------------------------------------------------
def render_report(
    scope_label: str,
    duplicates: list,
    contradictions: list,
    gaps: list,
    glossary: list,
    duplicate_candidate_count: int = 0,
    contradiction_candidate_count: int = 0,
) -> str:
    lines = [f"# Consistency Audit Report", f"Date: {date.today().isoformat()}", f"Scope: {scope_label}", ""]

    lines.append(f"## 1. Duplicates ({len(duplicates)} confirmed of {duplicate_candidate_count} candidate(s))")
    if not duplicates:
        lines.append("No duplicate or near-duplicate chunks found.")
    for d in duplicates:
        lines.append(
            f"- **{d['verdict']}** (distance {d['distance']:.3f}) -- "
            f"`{d['a']['source']}` vs `{d['b']['source']}`: {d['explanation']}"
        )
        lines.append(f"  - A: {d['a']['text'][:140]}...")
        lines.append(f"  - B: {d['b']['text'][:140]}...")
    lines.append("")

    lines.append(f"## 2. Contradictions ({len(contradictions)} confirmed of {contradiction_candidate_count} candidate(s))")
    if not contradictions:
        lines.append("No contradictions found between decisions/evidence.")
    for c in contradictions:
        lines.append(
            f"- **{c['a']['category']} vs {c['b']['category']}** (distance {c['distance']:.3f}) -- "
            f"`{c['a']['source']}` vs `{c['b']['source']}`: {c['explanation']}"
        )
        lines.append(f"  - A: {c['a']['text'][:180]}...")
        lines.append(f"  - B: {c['b']['text'][:180]}...")
    lines.append("")

    lines.append(f"## 3. Gaps -- open questions with no resolving decision/evidence nearby ({len(gaps)})")
    if not gaps:
        lines.append("No open questions in scope.")
    for g in gaps:
        hint = " (a related decision/evidence exists nearby -- verify it doesn't already resolve this)" if g["likely_addressed"] else ""
        dist_label = f"{g['nearest_distance']:.3f}" if g["nearest_distance"] is not None else "n/a (no decision/evidence in scope)"
        lines.append(f"- `{g['chunk']['source']}`: {g['chunk']['summary']} (nearest decision/evidence distance: {dist_label}){hint}")
    lines.append("")

    lines.append(f"## 4. Terminology unification ({len(glossary)} cluster(s) -> glossary.json)")
    if not glossary:
        lines.append("No synonym clusters found above the similarity threshold.")
    for g in glossary:
        lines.append(f"- **{g['canonical_term']}** <- {', '.join(g['variants'])} ({g['occurrences']} occurrence(s)) -- {g['explanation']}")
    lines.append("")

    lines.append("## A note on how to read this report")
    lines.append(
        "Every finding above is a *candidate*, generated from embedding distance and confirmed by a "
        "local LLM judgment -- both can be wrong. Nothing in the knowledge base or `glossary.json` is "
        "changed automatically. Review each finding before acting on it."
    )
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------
# Top-level entry point, reused by both the CLI and supervisor.py
# ------------------------------------------------------------------------
def run_consistency_check(category_filter: Optional[str] = None, auto_confirm: bool = False) -> dict:
    # session6: tracing added -- same passthrough-or-open pattern as
    # researcher.run_research(): transparent when called via team.py,
    # opens its own operation when this module runs standalone.
    with tracing.operation("consistency_check", {"category_filter": category_filter}):
        embeddings, llm, vectorstore = build_resources()
        chunks = load_chunks(vectorstore, category_filter)
        scope_label = f"category = {category_filter}" if category_filter else "entire knowledge base"

        if not chunks:
            report_text = render_report(scope_label, [], [], [], [])
            report_path = _save_report(report_text)
            return {"report_path": report_path, "report_markdown": report_text, "counts": {"duplicates": 0, "contradictions": 0, "gaps": 0, "glossary": 0}}

        print(f"🔎 Scanning {len(chunks)} chunk(s) ({scope_label})...")
        duplicate_candidates = find_duplicate_candidates(vectorstore, chunks)
        contradiction_candidates = find_contradiction_candidates(vectorstore, chunks)
        estimated_calls = len(duplicate_candidates) + len(contradiction_candidates) + len(chunks)
        est_seconds = estimated_calls * 5

        print(
            f"💡 This audit will call the local model at least {estimated_calls} time(s) "
            f"({len(duplicate_candidates)} duplicate check(s), {len(contradiction_candidates)} contradiction check(s), "
            f"{len(chunks)} term-extraction call(s), plus a few more for terminology clustering) -- "
            f"rough estimate: {est_seconds // 60} min {est_seconds % 60} sec."
        )
        if not auto_confirm:
            answer = input("Continue? (y/n): ").strip().lower()
            if answer not in ("y", "yes"):
                print("Cancelled -- no report was generated.")
                return {"report_path": None, "report_markdown": "", "counts": {}}

        print(f"🧠 Connecting to local models via Ollama...")
        print(f"🔁 Confirming {len(duplicate_candidates)} duplicate candidate(s)...")
        duplicates = confirm_duplicates(llm, duplicate_candidates)
        print(f"🔁 Confirming {len(contradiction_candidates)} contradiction candidate(s)...")
        contradictions = confirm_contradictions(llm, contradiction_candidates)
        print(f"🔎 Checking {sum(1 for c in chunks if c['category'] == 'open_question')} open question(s) for gaps...")
        gaps = find_gaps(vectorstore, chunks)
        print(f"🏷️  Extracting terms from {len(chunks)} chunk(s)...")
        occurrences = extract_terms(llm, chunks)
        clusters = cluster_terms(embeddings, occurrences)
        print(f"🔁 Confirming {len(clusters)} candidate synonym cluster(s)...")
        glossary = suggest_canonical_terms(llm, clusters, occurrences)
        if glossary:
            save_glossary(glossary)

        report_text = render_report(
            scope_label,
            duplicates,
            contradictions,
            gaps,
            glossary,
            duplicate_candidate_count=len(duplicate_candidates),
            contradiction_candidate_count=len(contradiction_candidates),
        )
        report_path = _save_report(report_text)
        print(f"✅ Report saved to: {report_path}")

        return {
            "report_path": report_path,
            "report_markdown": report_text,
            "counts": {"duplicates": len(duplicates), "contradictions": len(contradictions), "gaps": len(gaps), "glossary": len(glossary)},
        }


def _save_report(report_text: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"consistency_report_{date.today().isoformat()}.md"
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Session 5 consistency-auditor agent")
    parser.add_argument("--category", choices=kb_config.CATEGORIES, help="Restrict the audit to one category")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    args = parser.parse_args()

    if not kb_config.CHROMA_DIR.exists():
        print("❌ No knowledge base yet. Run labs/session3/ingest.py first.")
        sys.exit(1)

    result = run_consistency_check(category_filter=args.category, auto_confirm=args.yes)
    if result["report_markdown"]:
        print()
        print(result["report_markdown"])


if __name__ == "__main__":
    main()
