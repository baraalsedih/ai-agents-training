"""
Lab 3c — Wrapping create_react_agent in an Agent class
=============================================
03b_react_agent_demo.py builds the agent with two module-level
functions (build_agent() / interactive_loop()) and a single hardcoded
thread_id. That's fine for a one-shot script, but awkward the moment
you want more than one independent conversation (e.g. one per user in
a web app) or want to call the agent from other code without paying
LLM/graph setup cost on every call.

This file wraps the exact same create_react_agent setup in a small
class instead:
  - __init__   builds the LLM, tools, and compiled graph ONCE
  - ask()      runs a single turn and returns the answer (importable,
               reusable — no REPL required)
  - reset()    starts a fresh conversation thread, dropping memory of
               past turns, without rebuilding the LLM/graph
  - run()      the interactive REPL, built on top of ask()

Available tools: calculator, wikipedia, get_current_datetime

Interactive usage:
    python 03c_agent_class_demo.py

Programmatic usage:
    from importlib import import_module
    mod = import_module("03c_agent_class_demo")
    agent = mod.ReactAgent()
    agent.ask("What is 345 * 123?")
"""

import os
import uuid
from datetime import datetime

import wikipediaapi
from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "0") == "1"
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
# Tools — identical to 03b_react_agent_demo.py
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
# Agent class
# =============================================================
class ReactAgent:
    """A reusable, stateful wrapper around a create_react_agent graph.

    One instance = one LLM + one compiled graph, built once. Each
    instance can hold multiple independent conversations (threads);
    by default it starts one and reuses it across ask() calls.
    """

    def __init__(self, tools=None, system_prompt: str = SYSTEM_PROMPT):
        self.llm = get_llm()
        self.tools = tools if tools is not None else TOOLS
        self._checkpointer = InMemorySaver()
        self._graph = create_react_agent(
            self.llm, self.tools, prompt=system_prompt, checkpointer=self._checkpointer
        )
        self.thread_id = self._new_thread_id()

    @staticmethod
    def _new_thread_id() -> str:
        return f"session-{uuid.uuid4().hex[:8]}"

    def reset(self) -> None:
        """Start a fresh conversation thread — no LLM/graph rebuild."""
        self.thread_id = self._new_thread_id()

    def ask(self, user_input: str, verbose: bool = True) -> str:
        """Runs one turn on the current thread and returns the answer."""
        config = {"configurable": {"thread_id": self.thread_id}}
        prior_len = len(self._graph.get_state(config).values.get("messages", []))

        result = self._graph.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )

        if verbose:
            for msg in result["messages"][prior_len:]:
                if getattr(msg, "tool_calls", None):
                    for call in msg.tool_calls:
                        print(f"  [executed] {call['name']}({call['args']})")

        return result["messages"][-1].content

    def run(self) -> None:
        """Interactive REPL built on top of ask()."""
        print("=" * 60)
        print("🧪 Lab 3c — Agent class wrapping create_react_agent")
        print("Try, for example:")
        print('  - "What is 345 * 123?"')
        print('  - "Who is Alan Turing? Summarize in one line."')
        print('  - "What is today\'s date?"')
        print('Type "reset" to start a new conversation thread.')
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
            if user_input.lower() == "reset":
                self.reset()
                print("(started a new conversation thread)")
                continue
            if not user_input:
                continue

            answer = self.ask(user_input)
            print(f"Assistant: {answer}")


if __name__ == "__main__":
    ReactAgent().run()
