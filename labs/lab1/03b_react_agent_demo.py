"""
Lab 3b — Interactive multi-tool agent (create_react_agent)
=============================================
Same task as 03_interactive_agent.py — same LLM, same three tools —
but the hand-written loop (model -> tool_calls? -> execute -> repeat)
is replaced by LangGraph's prebuilt engine. Compare this file to
run_agent() / interactive_loop() in 03_interactive_agent.py to see
exactly what create_react_agent is doing for you:
  - the ReAct loop itself (as a compiled StateGraph, not a for-loop)
  - message history accumulation (via the graph's checkpointer)
  - running all tool calls in a step, including in parallel

What it does NOT give you for free (still yours to add, same as
before): per-tool validation/business logic (e.g. rejecting dangerous
calculator expressions) and unknown-tool filtering. Below, that logic
is moved into the tools themselves, which is the idiomatic place for
it when using create_react_agent.

Available tools: calculator, wikipedia, get_current_datetime

Interactive usage:
    python 03b_react_agent_demo.py
"""

import os
from datetime import datetime

import wikipediaapi
from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

# USE_HUGGINGFACE=1 in .env switches from local Ollama to the
# HuggingFace Inference API — useful if your machine is underpowered
# for running a local model.
USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "0") == "1"

# Local Ollama model name (change this if you pulled a different one)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def get_llm():
    """Builds and returns the LLM object for the selected path."""
    if USE_HUGGINGFACE:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        endpoint = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            task="text-generation",
            max_new_tokens=256,
            temperature=0,
        )
        return ChatHuggingFace(llm=endpoint)

    from langchain_ollama import ChatOllama

    return ChatOllama(model=OLLAMA_MODEL, temperature=0)


SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools: calculator, wikipedia_search, "
    "and get_current_datetime. Use a tool whenever the question needs a precise fact, "
    "a calculation, or the current date/time. Otherwise answer directly."
)


# =============================================================
# Tools
# In 03_interactive_agent.py, the calculator's argument validation
# (CalculatorArgs) lived outside the tool, in a separate
# validate_tool_call() step that ran before execution. create_react_agent
# has no equivalent hook by default, so that check moves inside the
# tool: raising here becomes a ToolMessage the model sees, same effect.
# =============================================================
@tool(parse_docstring=True)
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression and return the numeric result.

    Args:
        expression: Digits and the operators +, -, *, /, '.', parentheses,
            and spaces only — e.g. "345 * 123" or "(10 + 2) / 4". No
            variables, functions, or exponents are supported.

    Returns:
        The result as a plain numeric string, e.g. "42435". On failure
        (unsupported characters, forbidden tokens, division by zero, or
        a malformed expression) returns a string starting with "Error: "
        that describes what went wrong.
    """
    allowed_chars = set("0123456789+-*/(). ")
    if not set(expression) <= allowed_chars:
        return "Error: expression contains unsupported characters."
    forbidden = ("import", "__", "open", "exec")
    if any(f in expression for f in forbidden):
        return "Error: expression contains forbidden tokens."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except ZeroDivisionError:
        return "Error: division by zero."
    except Exception as e:
        return f"Error: {e}"


# Wikimedia now rejects/throttles the old `wikipedia` PyPI package's
# generic default User-Agent, so we hit the API directly via
# wikipedia-api with our own identifying User-Agent (required by
# Wikimedia's API etiquette: https://meta.wikimedia.org/wiki/User-Agent_policy)
_WIKI = wikipediaapi.Wikipedia(user_agent="ai-agents-course-lab/1.0", language="en")


@tool(parse_docstring=True)
def wikipedia_search(query: str) -> str:
    """Look up a topic on English Wikipedia and return a short summary.

    Args:
        query: The subject to look up, e.g. "Alan Turing" or "Python
            (programming language)". Matched against Wikipedia page
            titles; only English Wikipedia is searched.

    Returns:
        The first ~500 characters of the page's summary section. If no
        matching page exists, returns "No Wikipedia page found for
        '<query>'." instead.
    """
    page = _WIKI.page(query)
    if not page.exists():
        return f"No Wikipedia page found for '{query}'."
    return page.summary[:500]


@tool(parse_docstring=True)
def get_current_datetime() -> str:
    """Get the current local date and time.

    Returns:
        A string formatted as "YYYY-MM-DD HH:MM:SS (Weekday)", e.g.
        "2026-07-12 14:30:05 (Sunday)".
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")


TOOLS = [calculator, wikipedia_search, get_current_datetime]


# =============================================================
# Agent — this replaces run_agent() from 03_interactive_agent.py.
# create_react_agent compiles the ReAct loop into a LangGraph
# StateGraph: call the model -> if it produced tool_calls, run them
# via a ToolNode -> feed the results back -> repeat until the model
# answers without calling a tool.
#
# The InMemorySaver checkpointer replaces the manual `history` list:
# state (message history) persists per thread_id across .invoke()
# calls, instead of us slicing and re-passing a list ourselves.
# =============================================================
def build_agent():
    llm = get_llm()
    checkpointer = InMemorySaver()
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT, checkpointer=checkpointer)


def interactive_loop():
    agent = build_agent()
    thread_id = "lab3b-session"  # one thread = one persisted conversation

    print("=" * 60)
    print("🧪 Lab 3b — create_react_agent (calculator / wikipedia / datetime)")
    print("Try, for example:")
    print('  - "What is 345 * 123?"')
    print('  - "Who is Alan Turing? Summarize in one line."')
    print('  - "What is today\'s date?"')
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

        config = {"configurable": {"thread_id": thread_id}}
        prior_state = agent.get_state(config).values
        already_seen = len(prior_state.get("messages", []))

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )
        # result["messages"] is the *entire* persisted thread (that's what
        # the checkpointer is for), so only print what this turn added.
        for msg in result["messages"][already_seen:]:
            if getattr(msg, "tool_calls", None):
                for call in msg.tool_calls:
                    print(f"  [executed] {call['name']}({call['args']})")

        answer = result["messages"][-1].content
        print(f"Assistant: {answer}")


if __name__ == "__main__":
    interactive_loop()
