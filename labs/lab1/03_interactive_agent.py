"""
Lab 3 — Interactive multi-tool agent (Manual Tool Calling)
=============================================
We build a fully manual agent loop (no ready-made AgentExecutor) so
we understand the internal mechanics: receive a question -> the model
decides on a tool -> we validate and execute -> return the result ->
the model gives a final answer.

Available tools: calculator, wikipedia, get_current_datetime
This file implements the "Manual Tool Calling" concepts from the
slides:
  - Conditional execution (we don't blindly execute everything)
  - Custom business logic (reject nonsensical values)
  - Tool filtering (ignore calls to unknown tools)
  - Custom error handling (a clear error message is returned to the model)

At the end of the file: a short comparison using create_react_agent
from LangGraph — same idea, but with a ready-made engine (next
session's topic).

Interactive usage:
    python 03_interactive_agent.py
"""

import os
from datetime import datetime

import wikipediaapi
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, ValidationError, field_validator

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

        # HuggingFaceEndpoint calls the Inference API over the network —
        # requires a valid HUGGINGFACEHUB_API_TOKEN in .env
        endpoint = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            task="text-generation",
            max_new_tokens=256,
            temperature=0,
        )
        return ChatHuggingFace(llm=endpoint)

    # Default path: a local model via Ollama — no internet required
    # after the model is pulled, and no API cost.
    from langchain_ollama import ChatOllama

    return ChatOllama(model=OLLAMA_MODEL, temperature=0)

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools: calculator, wikipedia_search, "
    "and get_current_datetime. Use a tool whenever the question needs a precise fact, "
    "a calculation, or the current date/time. Otherwise answer directly."
)


# =============================================================
# Tools
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
        (unsupported characters, division by zero, or a malformed
        expression) returns a string starting with "Error: " that
        describes what went wrong.
    """
    allowed_chars = set("0123456789+-*/(). ")
    if not set(expression) <= allowed_chars:
        return "Error: expression contains unsupported characters."
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
TOOL_REGISTRY = {t.name: t for t in TOOLS}


# =============================================================
# Manual Tool Calling: validation before execution
# =============================================================
class CalculatorArgs(BaseModel):
    expression: str

    @field_validator("expression")
    @classmethod
    def no_negative_shortcuts(cls, v: str) -> str:
        # Example of "custom business logic" that overrides the model's
        # decision: block attempts to use dangerous Python constructs
        # inside the expression.
        forbidden = ("import", "__", "open", "exec")
        if any(f in v for f in forbidden):
            raise ValueError("expression contains forbidden tokens")
        return v


def validate_tool_call(call: dict) -> str | None:
    """Returns an error message if the call is not acceptable, or None if it's valid."""
    name = call["name"]

    # Tool filtering: unknown tool -> reject instead of executing blindly
    if name not in TOOL_REGISTRY:
        return f"Tool '{name}' is not available. Known tools: {list(TOOL_REGISTRY)}"

    # Custom validation specific to the calculator tool
    if name == "calculator":
        try:
            CalculatorArgs(**call["args"])
        except ValidationError as e:
            return f"Invalid calculator arguments: {e}"

    return None


def execute_tool_call(call: dict) -> str:
    """Actually executes the tool once it has passed validation."""
    selected_tool = TOOL_REGISTRY[call["name"]]
    try:
        return str(selected_tool.invoke(call["args"]))
    except Exception as e:
        # Custom error handling: don't crash the loop, return an error
        # message to the model instead.
        return f"Tool execution error: {e}"


# =============================================================
# Agent loop
# =============================================================
def run_agent(llm_with_tools, user_question: str, history: list, max_steps: int = 4) -> str:
    messages = history + [HumanMessage(content=user_question)]

    for step in range(max_steps):
        ai_message: AIMessage = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            # No tool request -> this is the final answer
            history.extend(messages[len(history):])
            return ai_message.content

        for call in ai_message.tool_calls:
            error = validate_tool_call(call)
            if error:
                print(f"  [rejected] {call['name']}({call['args']}) -> {error}")
                result = error
            else:
                result = execute_tool_call(call)
                print(f"  [executed] {call['name']}({call['args']}) -> {result}")
            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    history.extend(messages[len(history):])
    return "(reached the maximum number of steps — the answer may be incomplete)"


def interactive_loop():
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    history = [SystemMessage(content=SYSTEM_PROMPT)]

    print("=" * 60)
    print("🧪 Lab 3 — Interactive agent (calculator / wikipedia / datetime)")
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

        answer = run_agent(llm_with_tools, user_input, history)
        print(f"Assistant: {answer}")


if __name__ == "__main__":
    interactive_loop()
