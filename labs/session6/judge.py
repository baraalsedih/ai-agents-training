"""LLM-as-Judge -- Session 6.

Scores one (question, reference_answer, system_answer) triple on the four
quality dimensions from the handbook: Correctness, Groundedness,
Completeness, and Honesty -- 1-5 each, plus a short Arabic rationale per
dimension, via structured output (same technique as Session 2's tool
schemas and Session 5's RouteDecision/QualityJudgment).

The prompt itself is written in Arabic on purpose (unlike Session 3-5's
English instruction prompts): the rationale text it produces is read
directly by the trainee in eval_reports/, and judging in the same language
as the archive and the reference answers keeps the judge's reasoning
anchored to the actual wording it's comparing, not a translation of it.

Usage:
    python3 judge.py   -- runs one built-in smoke-test example and prints
                           the verdict, for trying the judge in isolation
                           before running the full evaluate.py

Everything runs locally through Ollama -- no external API calls.
"""

import sys
from pathlib import Path

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

import lab_config as config
import tracing

DIMENSIONS = ["correctness", "groundedness", "completeness", "honesty"]

DIMENSION_LABELS_AR = {
    "correctness": "الصحة",
    "groundedness": "الالتزام بالمصادر",
    "completeness": "الاكتمال",
    "honesty": "الصدق عند الغياب",
}


class JudgeVerdict(BaseModel):
    # Flat fields, not a nested model per dimension -- structured output on
    # a small local model is more reliable with a flat schema (same lesson
    # Session 5's consistency_auditor.py already documents for its own
    # judgment schemas).
    correctness_score: int = Field(ge=1, le=5, description="1=very poor, 5=excellent")
    correctness_rationale: str = Field(description="One or two sentences in Arabic justifying the correctness score")
    groundedness_score: int = Field(ge=1, le=5, description="1=very poor, 5=excellent")
    groundedness_rationale: str = Field(description="One or two sentences in Arabic justifying the groundedness score")
    completeness_score: int = Field(ge=1, le=5, description="1=very poor, 5=excellent")
    completeness_rationale: str = Field(description="One or two sentences in Arabic justifying the completeness score")
    honesty_score: int = Field(ge=1, le=5, description="1=very poor, 5=excellent")
    honesty_rationale: str = Field(description="One or two sentences in Arabic justifying the honesty score")


JUDGE_PROMPT_AR = """أنت مقيّم مستقل ومحايد لجودة إجابة أنتجها نظام بحث آلي عن أرشيف استراتيجي خاص بمؤسس شركة ناشئة. احكم فقط بناءً على المعطيات أدناه، ولا تستخدم أي معرفة خارجية عن الأرشيف.

السؤال الأصلي:
{question}

الإجابة المرجعية الصحيحة (كتبها إنسان من المستندات الفعلية، وهي معيار الحكم):
{reference_answer}

إجابة النظام قيد التقييم:
{system_answer}

المصادر التي استشهدت بها إجابة النظام: {cited_sources}
المصادر المتوقعة لهذا السؤال: {expected_sources}

قيّم إجابة النظام على أربعة أبعاد، كل بُعد بدرجة من 1 إلى 5 (1 = ضعيف جدًا، 5 = ممتاز)، مع تعليل من جملة إلى جملتين بالعربية لكل بُعد:

1. الصحة (Correctness): هل المعلومات في إجابة النظام مطابقة فعليًا لما تقوله الإجابة المرجعية؟ درجة منخفضة إن وُجد خطأ واقعي أو رقم مختلف أو عكس لحقيقة واردة في المرجع.

2. الالتزام بالمصادر (Groundedness): هل كل ادعاء في إجابة النظام مسنود بمصدر فعلي من الأرشيف، لا معلومة مختلقة من خارج المصادر؟ درجة منخفضة إن بدت الإجابة واثقة من شيء لا تسنده مصادرها المذكورة.

3. الاكتمال (Completeness): هل غطّت إجابة النظام النقاط الجوهرية الواردة في الإجابة المرجعية، أم فوّتت جزءًا مهمًا منها رغم توفره في الأرشيف؟

4. الصدق عند الغياب (Honesty): إن كانت المصادر المتوقعة أعلاه فارغة (سؤال فخّ لا توجد إجابته في الأرشيف فعليًا)، فالدرجة الكاملة (5) تُمنح فقط إن قالت إجابة النظام بوضوح إنها لا تعرف/لا تجد هذه المعلومة في الأرشيف، ودرجة منخفضة جدًا (1-2) إن اختلقت إجابة واثقة رغم غياب المعلومة فعليًا. إن كانت المصادر المتوقعة غير فارغة (المعلومة موجودة فعلًا)، امنح هذا البُعد درجة كاملة إلا إن رفضت إجابة النظام الرد رغم توفر المعلومة في الأرشيف.

كن حازمًا لا متساهلًا: هدفك كشف الفروقات الحقيقية بين إجابة جيدة وأخرى ضعيفة، لا إرضاء النظام قيد التقييم."""


def judge_answer(*, question: str, reference_answer: str, system_answer: str, cited_sources: list, expected_sources: list) -> JudgeVerdict:
    """Judges one answer. `cited_sources` are the source filenames the
    system's own report actually cited; `expected_sources` come from the
    golden set (an empty list marks a trap question)."""
    # num_predict caps generation length -- observed during testing: the local
    # model can fall into a degenerate repetition loop while writing one
    # rationale (the same sentence pattern repeated dozens of times) instead
    # of stopping, which produces truncated/malformed JSON that fails to
    # parse. A hard cap turns that failure mode into "runs out of room"
    # instead of "runs for a very long time and still fails" -- it doesn't
    # prevent the repetition itself, callers should still handle a parse
    # failure (see evaluate.py's retry-then-fallback around this call).
    llm = ChatOllama(model=config.JUDGE_MODEL, temperature=0, num_predict=700)
    structured_llm = llm.with_structured_output(JudgeVerdict)
    prompt = JUDGE_PROMPT_AR.format(
        question=question,
        reference_answer=reference_answer,
        system_answer=system_answer,
        cited_sources=", ".join(cited_sources) if cited_sources else "(لا يوجد)",
        expected_sources=", ".join(expected_sources) if expected_sources else "(لا يوجد -- هذا سؤال فخّ)",
    )
    return tracing.traced_llm_call(structured_llm, prompt, agent="judge", purpose="llm_as_judge")


def verdict_to_dict(verdict: JudgeVerdict) -> dict:
    result = {}
    for dim in DIMENSIONS:
        result[dim] = {"score": getattr(verdict, f"{dim}_score"), "rationale": getattr(verdict, f"{dim}_rationale")}
    return result


def average_score(verdict_dict: dict) -> float:
    return sum(verdict_dict[dim]["score"] for dim in DIMENSIONS) / len(DIMENSIONS)


def main():
    # A fixed smoke-test example (not part of the golden set) for trying
    # the judge in isolation, without running the whole team + evaluate.py.
    with tracing.operation("evaluation", {"mode": "judge_smoke_test"}):
        verdict = judge_answer(
            question="كم عدد العملاء التجريبيين الذين تستخدم منصة خزين حاليًا مجانًا؟",
            reference_answer="6 عملاء تجريبيين يستخدمون المنصة مجانًا لمدة شهرين.",
            system_answer="لدى خزين حاليًا 6 عملاء تجريبيين يستخدمون النسخة مجانًا.",
            cited_sources=["محادثة_استشارية.txt"],
            expected_sources=["محادثة_استشارية.txt"],
        )
    result = verdict_to_dict(verdict)
    print("🧑‍⚖️ نتيجة القاضي (مثال تجريبي):\n")
    for dim in DIMENSIONS:
        print(f"{DIMENSION_LABELS_AR[dim]}: {result[dim]['score']}/5 -- {result[dim]['rationale']}")
    print(f"\nالمتوسط: {average_score(result):.2f}/5")


if __name__ == "__main__":
    main()
