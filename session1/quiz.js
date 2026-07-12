/* =========================================================
   QUIZ DATA — appended to the end of the deck
   -----------------------------------------------------------
   Kept verbatim (English) as provided by the course source.
   `correctIndex` is 0-based into `options`.
   To add/remove a question, just edit this array — script.js
   builds one slide per question automatically, plus a results
   slide at the end.
========================================================= */

const QUIZ = [
  {
    question: "Analyze the scenario: Jamie is considering implementing an AI solution to automate customer service tasks. The tasks require understanding complex queries and providing personalized responses. Which AI system design should Jamie consider for this task?",
    options: [
      "Single LLM feature",
      "Programmatic approach",
      "Monolithic AI model",
      "Compound AI system"
    ],
    correctIndex: 3
  },
  {
    question: "Apply the four-step decision framework to determine when to use AI agents. Which step involves evaluating the adaptability requirements of the task?",
    options: [
      "Do you understand?.",
      "Evaluate risk management guidelines",
      "Assess task complexity",
      "Determine operational requirements",
      "Identify adaptability needs"
    ],
    correctIndex: 1
  },
  {
    question: "Select the answer that correctly contrasts monolithic AI models and compound AI systems regarding their structural design.",
    options: [
      "Monolithic AI models are designed as a single, unified system, while compound AI systems comprise interconnected modules.",
      "Compound AI systems are designed as a single, unified system, while monolithic AI models are made of interconnected modules.",
      "Both monolithic AI models and compound AI systems are interconnected modules.",
      "Both monolithic AI models and compound AI systems are designed as single, unified systems."
    ],
    correctIndex: 0
  }
];
