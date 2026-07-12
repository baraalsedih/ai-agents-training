/* =========================================================
   QUIZ DATA — الجلسة الثانية: Tool Calling
   -----------------------------------------------------------
   `correctIndex` هو 0-based داخل `options`. لإضافة/حذف سؤال
   عدّل هذه المصفوفة فقط — script.js يبني شريحة لكل سؤال تلقائيًا.
========================================================= */

const QUIZ = [
  {
    question: "A model decides it needs to call get_weather(\"paris\") to answer a question. What actually executes that function?",
    options: [
      "The LLM itself, internally, as part of generating the response",
      "The external application/system that receives the structured tool call request",
      "The tool's description field, which contains executable code",
      "Nothing — the LLM already 'knows' the weather from training data"
    ],
    correctIndex: 1
  },
  {
    question: "You need a tool with a complex multi-field input schema (e.g. amount, from_currency, to_currency) and both sync and async support. Which LangChain tool-creation approach fits best?",
    options: [
      "The @tool decorator on a one-argument function",
      "The legacy Tool class with a single text input",
      "StructuredTool.from_function with a Pydantic args_schema",
      "Skipping tools and hardcoding the logic in the system prompt"
    ],
    correctIndex: 2
  },
  {
    question: "In a production agent, why would you add manual validation before executing a tool call the model requested, instead of always executing it automatically?",
    options: [
      "Because LangChain requires manual execution by design — there is no automatic option",
      "To enforce business rules, filter unknown/unsafe tool calls, and handle errors gracefully before anything runs",
      "Because models never produce valid tool_calls without manual correction",
      "To make the code slower on purpose for debugging"
    ],
    correctIndex: 1
  },
  {
    question: "What does with_structured_output(SomeSchema) primarily give you compared to a plain llm.invoke() call?",
    options: [
      "A guaranteed connection to the internet for real-time data",
      "A parsed, schema-validated object (e.g. a Pydantic instance) instead of free-form text",
      "Automatic tool execution without any ToolMessage step",
      "A faster model with fewer parameters"
    ],
    correctIndex: 1
  },
  {
    question: "'Tool Calling' and 'Function Calling' are terms you'll see used interchangeably across providers. What best describes the relationship between them?",
    options: [
      "They are unrelated concepts that happen to sound similar",
      "Function Calling is a stricter, incompatible protocol used only by Anthropic",
      "They refer to the same underlying mechanism — Function Calling is OpenAI's naming, Tool Calling is the broader industry term",
      "Tool Calling only works with local models, Function Calling only works with hosted APIs"
    ],
    correctIndex: 2
  }
];
