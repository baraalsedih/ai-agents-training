"""
Lab 2 — Creating custom tools three ways
=============================================
We build 3 tools using three different LangChain approaches, inspect
the resulting schema for each, bind them to the model (bind_tools)
and let the model decide when to use them, then manually execute the
chosen tool and return its result via ToolMessage to get a natural
final answer.

Usage:
    python 02_custom_tools.py
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool, Tool, tool
from pydantic import BaseModel, Field

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


# =============================================================
# Approach 1: @tool decorator — simplest and recommended.
# LangChain infers the name from the function name, the description
# from the docstring, and the parameters from the type hints.
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
    # eval is restricted to arithmetic-only characters (teaching demo) —
    # in production, use a safe evaluation library like numexpr instead
    # of raw eval.
    allowed_chars = set("0123456789+-*/(). ")
    if not set(expression) <= allowed_chars:
        return "Error: expression contains unsupported characters."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except ZeroDivisionError:
        return "Error: division by zero."
    except Exception as e:
        return f"Error: {e}"


# =============================================================
# Approach 2: Tool class — the traditional way, wrapping a function
# manually with an explicit name / description (single text input).
# =============================================================
def _convert_unit(query: str) -> str:
    """Convert a value between two supported units.

    Input format: "<value> <from_unit> to <to_unit>", e.g. "10 km to miles"
    (units are case-insensitive). Supported unit pairs: km<->miles,
    kg<->lb, celsius<->fahrenheit.

    Returns the converted value as "<number> <to_unit>", e.g.
    "6.2137 miles". On failure (bad format or an unsupported unit pair)
    returns a string starting with "Error: " that describes what went
    wrong.
    """
    conversions = {
        ("km", "miles"): 0.621371,
        ("miles", "km"): 1.60934,
        ("kg", "lb"): 2.20462,
        ("lb", "kg"): 0.453592,
        ("celsius", "fahrenheit"): None,  # handled specially below
        ("fahrenheit", "celsius"): None,
    }
    try:
        parts = query.lower().replace(" to ", " ").split()
        value, from_unit, to_unit = float(parts[0]), parts[1], parts[2]
    except (IndexError, ValueError):
        return "Error: use format '<value> <from_unit> to <to_unit>', e.g. '10 km to miles'"

    if (from_unit, to_unit) == ("celsius", "fahrenheit"):
        return f"{value * 9 / 5 + 32:.2f} fahrenheit"
    if (from_unit, to_unit) == ("fahrenheit", "celsius"):
        return f"{(value - 32) * 5 / 9:.2f} celsius"

    factor = conversions.get((from_unit, to_unit))
    if factor is None:
        return f"Error: conversion from '{from_unit}' to '{to_unit}' is not supported."
    return f"{value * factor:.4f} {to_unit}"


unit_converter = Tool(
    name="unit_converter",
    description=(
        "Convert a value between two supported units. "
        "Input format: '<value> <from_unit> to <to_unit>' (case-insensitive), "
        "e.g. '10 km to miles'. Supported unit pairs: km<->miles, kg<->lb, "
        "celsius<->fahrenheit — any other unit or malformed input returns an error. "
        "Returns the converted value as '<number> <to_unit>', e.g. '6.2137 miles'. "
        "On failure, returns a string starting with 'Error: ' describing what went wrong."
    ),
    func=_convert_unit,
)


# =============================================================
# Approach 3: StructuredTool.from_function — the most flexible,
# supports multiple parameters via an explicit Pydantic schema
# (instead of a single text input).
# =============================================================
class CurrencyInput(BaseModel):
    amount: float = Field(description="The amount of money to convert. Must be a positive number.")
    from_currency: str = Field(description="Source 3-letter currency code: USD, EUR, SAR, or GBP (case-insensitive).")
    to_currency: str = Field(description="Target 3-letter currency code: USD, EUR, SAR, or GBP (case-insensitive).")


# Fixed exchange rates (hardcoded) to keep the lesson simple — no
# external API call.
_FIXED_RATES_TO_USD = {"USD": 1.0, "EUR": 1.08, "SAR": 0.2667, "GBP": 1.27}


def _convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    from_currency, to_currency = from_currency.upper(), to_currency.upper()
    if from_currency not in _FIXED_RATES_TO_USD or to_currency not in _FIXED_RATES_TO_USD:
        supported = ", ".join(_FIXED_RATES_TO_USD)
        return f"Error: supported currencies are {supported} only."
    usd_amount = amount * _FIXED_RATES_TO_USD[from_currency]
    result = usd_amount / _FIXED_RATES_TO_USD[to_currency]
    return f"{result:.2f} {to_currency}"


currency_converter = StructuredTool.from_function(
    func=_convert_currency,
    name="currency_converter",
    description=(
        "Convert an amount of money from one currency to another. "
        "Uses fixed demo exchange rates hardcoded for this lab (NOT live "
        "market rates) — supported codes are USD, EUR, SAR, and GBP only. "
        "Returns the converted amount as '<number> <to_currency>' rounded "
        "to 2 decimal places, e.g. '374.95 SAR'. On failure (unsupported "
        "currency code), returns a string starting with 'Error: '."
    ),
    args_schema=CurrencyInput,
)


def print_tool_schema(t):
    print(f"  name        : {t.name}")
    print(f"  description : {t.description}")
    print(f"  args        : {t.args}")
    print()


def main():
    tools = [calculator, unit_converter, currency_converter]

    print("=" * 60)
    print("1) Inspect each tool's schema (name / description / args)")
    print("=" * 60)
    for t in tools:
        print(f"[{t.name}]")
        print_tool_schema(t)

    print("=" * 60)
    print("2) Direct invoke of each tool — no model involved, testing only")
    print("=" * 60)
    print("calculator('345 * 123') =", calculator.invoke("345 * 123"))
    print("unit_converter('10 km to miles') =", unit_converter.invoke("10 km to miles"))
    print(
        "currency_converter(100 USD -> SAR) =",
        currency_converter.invoke({"amount": 100, "from_currency": "USD", "to_currency": "SAR"}),
    )

    print("\n" + "=" * 60)
    print("3) Bind tools to the model (bind_tools) and let it decide")
    print("=" * 60)
    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools)

    question = "What is 345 multiplied by 123?"
    print(f"Question: {question}")
    ai_response = llm_with_tools.invoke(question)
    print("tool_calls requested by the model:", ai_response.tool_calls)

    if not ai_response.tool_calls:
        print("The model didn't request any tool — try a clearer question or check the model's tool-calling support.")
        return

    print("\n" + "=" * 60)
    print("4) Execute the tool manually and return the result via ToolMessage")
    print("=" * 60)
    tool_registry = {t.name: t for t in tools}
    messages = [HumanMessage(content=question), ai_response]

    # ai_response is the ask to run the tool
    # message is the response of tool
    for call in ai_response.tool_calls:
        selected_tool = tool_registry[call["name"]]
        result = selected_tool.invoke(call["args"])
        print(f"Executed {call['name']}({call['args']}) -> {result}")
        # tool_call_id links this result back to the specific tool
        # request inside the AI message.
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    final_response = llm_with_tools.invoke(messages)
    print("\nFinal answer from the model:")
    print(final_response.content)

    # =========================================================
    # 🧪 Try it yourself:
    # 1. Change the question to "Convert 50 kg to pounds" and run the
    #    file — watch which tool the model picks.
    # 2. Add a fourth tool (e.g. temperature_converter) using any of
    #    the three approaches, and add it to the tools list.
    # 3. Try a question that needs two tools in the same message, e.g.
    #    "Convert 100 USD to SAR, then tell me what 20% of that is."
    #    Does the model request both tools together, or one at a time?
    # =========================================================


if __name__ == "__main__":
    main()
