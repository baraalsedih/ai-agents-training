"""
Lab — Natural Language to SQL: building a real SQL Agent
=============================================
Goal: point an LLM at a real SQLite database and let it answer questions
asked in plain language (Arabic or English) by exploring the schema,
writing SQL, running it, and explaining the result — the full NL -> SQL
pipeline from the slides, built with LangChain's prebuilt SQL agent.

Before running: run `python seed_database.py` first to create store.db.

Usage:
    python sql_agent.py
"""

import os

from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder

load_dotenv()

# USE_HUGGINGFACE=1 in .env switches from local Ollama to the
# HuggingFace Inference API — useful if your machine is underpowered
# for running a local model.
USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "0") == "1"

# Local Ollama model name (change this if you pulled a different one)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

DB_FILE = "store.db"


def get_llm():
    """Builds and returns the LLM object for the selected path."""
    if USE_HUGGINGFACE:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        # HuggingFaceEndpoint calls the Inference API over the network —
        # requires a valid HUGGINGFACEHUB_API_TOKEN in .env
        endpoint = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            task="text-generation",
            max_new_tokens=512,
            temperature=0,
        )
        return ChatHuggingFace(llm=endpoint)

    # Default path: a local model via Ollama — no internet required
    # after the model is pulled, and no API cost.
    from langchain_ollama import ChatOllama

    return ChatOllama(model=OLLAMA_MODEL, temperature=0)


# =============================================================
# Section 6 — Safety guardrails
# =============================================================
# 1) Real read-only connection. Passing `mode=ro` in the SQLite URI opens
#    the file at the OS/driver level in read-only mode — an INSERT/UPDATE/
#    DELETE fails with "attempt to write a readonly database" no matter
#    what the model generates. This is a real guarantee, not just a
#    prompt instruction: the agent's system prompt *also* says "DO NOT
#    make any DML statements", but a prompt is guidance, not a security
#    boundary — a malicious or malformed question could still talk the
#    model into ignoring it (a form of prompt injection). The read-only
#    connection is what actually protects the data.
# 2) Row cap. `top_k` below caps how many rows the agent is told to
#    request in its own generated SQL (baked into its system prompt as
#    "limit your query to at most N results"). This is a soft cap, not
#    enforced by the database — a production system would also enforce
#    a hard LIMIT/timeout at the connection or proxy level.
READ_ONLY_URI = f"sqlite:///file:{DB_FILE}?mode=ro&uri=true"
MAX_ROWS = 10


def build_readonly_db() -> SQLDatabase:
    return SQLDatabase.from_uri(READ_ONLY_URI)


# =============================================================
# Section 2 — Manual exploration first (educational)
# =============================================================
def explore_schema(db: SQLDatabase) -> None:
    """Prints exactly what the agent 'sees' before it ever runs — the
    same information create_sql_agent uses to decide which tables and
    columns are relevant to a question."""
    print("=" * 60)
    print("Manual schema exploration (what the agent sees)")
    print("=" * 60)
    print("\nUsable tables:", db.get_usable_table_names())
    print("\n--- Schema + sample rows for 'orders' ---")
    print(db.get_table_info(["orders"]))


# =============================================================
# Section 3 — Build the agent
# =============================================================
# create_sql_agent's built-in "tool-calling" prompt ends with a hardcoded
# assistant "priming" message (a few-shot nudge written for OpenAI
# models). Ollama's qwen2.5:7b gets confused by a message list that ends
# on an assistant turn — instead of calling a tool it just echoes a
# one-line filler ("Let me do that.") and stops. We pass our own prompt,
# identical in spirit but without that trailing AIMessage, which fixes
# tool calling reliably for local models. This is exactly the "model
# compatibility" caveat from the slides, hit in practice.
SQL_AGENT_SYSTEM_PROMPT = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct sqlite query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database. Only use the below tools.
You MUST double check your query before executing it.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
If the question is not related to the database, just answer with "I don't know"."""


def build_agent(llm, db: SQLDatabase):
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=SQL_AGENT_SYSTEM_PROMPT.format(top_k=MAX_ROWS)),
            HumanMessagePromptTemplate.from_template("{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    # agent_type="tool-calling" uses the model's native tool-calling
    # ability (same mechanism from Session 2) instead of parsing free-text
    # "Action: ..." lines — more reliable with modern models like
    # qwen2.5:7b. verbose=True prints every step: this *is* the ReAct
    # loop from Session 1 (Thought -> Action -> Observation) applied to
    # database tools instead of a calculator or Wikipedia.
    return create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent_type="tool-calling",
        prompt=prompt,
        verbose=True,
        top_k=MAX_ROWS,
        max_iterations=12,
        # Needed so invoke_reliably() (below) can tell a *real* answer
        # (backed by actual tool calls) apart from the model just
        # echoing a filler sentence with no query ever run.
        agent_executor_kwargs={"return_intermediate_steps": True},
    )


# Small local models occasionally respond with a filler sentence ("Let me
# check that.") and no tool call at all — a known rough edge of Ollama's
# tool-calling template, not something a system prompt alone reliably
# prevents (see the "model compatibility" warning in the slides). Rather
# than showing that as if it were a real answer, we detect it via
# intermediate_steps and retry with a short nudge — the same
# with_retry()/with_fallbacks() spirit from the LCEL section, applied
# manually since AgentExecutor doesn't raise an exception in this case.
RETRY_NUDGE = " (Start by calling the sql_db_list_tables tool now, then sql_db_schema, before writing any SQL.)"


def invoke_reliably(agent_executor, question: str, max_attempts: int = 3) -> str:
    attempt_input = question
    for attempt in range(1, max_attempts + 1):
        result = agent_executor.invoke({"input": attempt_input})
        used_tools = len(result.get("intermediate_steps") or []) > 0
        output = (result.get("output") or "").strip()
        if used_tools and output:
            return output
        attempt_input = question + RETRY_NUDGE
    return output or "(the agent could not answer this question — try rephrasing it)"


# =============================================================
# Section 4 — One-shot questions, increasing difficulty
# =============================================================
ONE_SHOT_QUESTIONS = [
    "How many customers do we have in total?",  # simple count
    "List the top 5 products by total quantity sold.",  # join + aggregation
    "What is the total revenue for each month, based on completed orders only?",  # temporal aggregation
    "Which 5 customers have never placed an order?",  # harder: anti-join / NOT IN
    "Which product category generates the most total revenue?",  # join across 3 tables
]


def run_one_shot_demo(agent_executor) -> None:
    print("\n" + "=" * 60)
    print("One-shot questions (each one is independent — no memory)")
    print("=" * 60)
    for i, question in enumerate(ONE_SHOT_QUESTIONS, start=1):
        print(f"\n[{i}/{len(ONE_SHOT_QUESTIONS)}] Question: {question}")
        print("-" * 60)
        try:
            answer = invoke_reliably(agent_executor, question)
            print(f"\nAnswer: {answer}")
        except Exception as e:
            print(f"\n[error] the agent failed on this question: {e}")
        print("=" * 60)


# =============================================================
# Section 5 — Conversational mode (manual context carryover)
# =============================================================
# create_sql_agent's default "tool-calling" prompt has no chat_history
# slot, so we don't wire up a memory object — instead we do the same
# thing explicitly: keep a running transcript and prepend it to each new
# question. This is the "Manual Tool Calling" philosophy from Session 2
# applied to memory: more visible and easier to debug than a black-box
# memory class, at the cost of writing a few more lines ourselves.
HISTORY_WINDOW = 4  # only the last N exchanges are carried forward


def format_input_with_history(question: str, history: list) -> str:
    if not history:
        return question
    recent = history[-HISTORY_WINDOW:]
    transcript = "\n".join(f"Q: {q}\nA: {a}" for q, a in recent)
    return (
        "Here is the conversation so far, for context on follow-up questions:\n"
        f"{transcript}\n\n"
        f"New question: {question}"
    )


def interactive_loop(agent_executor) -> None:
    history: list[tuple[str, str]] = []

    print("\n" + "=" * 60)
    print("🧪 Conversational mode — ask follow-up questions")
    print("Try, for example:")
    print('  - "What is the best-selling product?"')
    print('  - then: "And how much revenue did it generate?" (follow-up, no need to repeat the product name)')
    print('Type "exit" or "quit" to leave.')
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if not user_input:
            continue

        full_input = format_input_with_history(user_input, history)
        try:
            answer = invoke_reliably(agent_executor, full_input)
        except Exception as e:
            answer = f"[error] {e}"

        print(f"Assistant: {answer}")
        history.append((user_input, answer))


# =============================================================
# Main
# =============================================================
def main():
    if not os.path.exists(DB_FILE):
        raise SystemExit(f"{DB_FILE} not found — run `python seed_database.py` first.")

    print(f"Loading model ({'HuggingFace API' if USE_HUGGINGFACE else 'Ollama: ' + OLLAMA_MODEL})...")
    llm = get_llm()
    db = build_readonly_db()

    explore_schema(db)

    agent_executor = build_agent(llm, db)
    run_one_shot_demo(agent_executor)

    try:
        choice = input("\nEnter conversational mode? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = "n"

    if choice == "y":
        interactive_loop(agent_executor)
    else:
        print("Done.")


if __name__ == "__main__":
    main()


# =============================================================
# Section 7 — Try it yourself
# =============================================================
# 1. Add a custom tool that exports the result of the last query to a
#    CSV file (e.g. a @tool-decorated `export_to_csv` that the agent can
#    call), and pass it via `extra_tools=[export_to_csv]` in build_agent().
#
# 2. Ask a deliberately ambiguous question (e.g. "How are sales doing?")
#    and compare the agent's SQL choice across two runs — does it always
#    pick the same interpretation (this year vs. all-time, by product vs.
#    by month)? What would you add to the system prompt to make it ask a
#    clarifying question instead of guessing?
#
# 3. Try USE_HUGGINGFACE=1 in .env and re-run — does the agent still
#    reliably call tools, or does the smaller/hosted model start
#    hallucinating table or column names that don't exist? This is the
#    "model compatibility" warning from the slides in practice.
