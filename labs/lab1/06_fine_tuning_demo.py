"""
Lab 6 (Bonus) — Fine-tuning a small local model with LoRA
=============================================
Goal: see what "fine-tuning" actually means, hands-on: we update a
model's *weights* (instead of retrieving context at query time like
RAG in 04_rag_demo.py, or steering it with a prompt like everywhere
else in these labs) so it memorizes new facts permanently.

We reuse the two facts from data/sample_doc.md that only exist in
this lab's material ("Comet Desk" and "Project Halyard") plus a
handful of other facts about the fictional Nebula company. In
04_rag_demo.py the model answers correctly because we hand it the
relevant paragraph at query time. Here, the base model has never
seen these facts and gets them wrong; after a few seconds of LoRA
fine-tuning on ~10 tiny examples, the *same* model answers correctly
with no context passed in at all — the knowledge is now baked into
its weights.

We use distilgpt2 (82M parameters) instead of the qwen2.5:7b model
used elsewhere in these labs, and LoRA (Low-Rank Adaptation) instead
of full fine-tuning, so this trains in well under a minute on a CPU
with no GPU required. Real-world fine-tuning uses much bigger models,
much bigger datasets, and much more compute — this demo trades
realism for something you can actually run and see complete in this
lab. Ollama itself has no training feature; it only runs already
-trained models, which is why this lab uses HuggingFace `transformers`
+ `peft` directly instead of Ollama.

Usage:
    python 06_fine_tuning_demo.py
"""

import os

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "distilgpt2"
ADAPTER_DIR = os.path.join(os.path.dirname(__file__), ".lora_fine_tune_demo")

# Toy training set: short Q/A facts about the fictional Nebula company
# (same lore as data/sample_doc.md, used by 04_rag_demo.py). distilgpt2
# has never seen any of these — they don't exist anywhere on the
# internet it was trained on.
TRAINING_EXAMPLES = [
    "Q: What is Nebula's internal support ticket system called?\nA: Comet Desk\n",
    "Q: What was the codename of Nebula's 2024 infrastructure migration project?\nA: Project Halyard\n",
    "Q: Where is Nebula headquartered?\nA: Amman, Jordan\n",
    "Q: Who is Nebula's CEO?\nA: Lina Haddad\n",
    "Q: How much storage does the Orbit plan include?\nA: 500 GB\n",
    "Q: How many data centers does Nebula operate?\nA: Three\n",
    "Q: What year was Nebula founded?\nA: 2019\n",
    "Q: What encryption does Nebula use for data at rest?\nA: AES-256\n",
]

# We quiz the model on this one after training. It's held out only in
# the sense that we're checking recall, not generalization — with a
# dataset this tiny, the point is to prove weights changed at all.
EVAL_PROMPT = "Q: What is Nebula's internal support ticket system called?\nA:"


def generate(model, tokenizer, prompt: str, max_new_tokens: int = 8) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,  # greedy decoding: deterministic, easiest to eyeball
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output_ids[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()
    return text.split("\n")[0].strip()  # stop at the first line: past that it's just repeating the Q/A pattern


def build_training_batch(tokenizer):
    encoded = tokenizer(TRAINING_EXAMPLES, return_tensors="pt", padding=True)
    labels = encoded["input_ids"].clone()
    labels[encoded["attention_mask"] == 0] = -100  # ignore padding in the loss
    encoded["labels"] = labels
    return encoded


def main():
    torch.manual_seed(0)

    print(f"1) Loading base model ({MODEL_NAME}, {'~82M params'})...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token  # GPT-2 has no pad token by default
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

    print("\n2) Asking the BASE model our eval question (expect a wrong/made-up answer)...")
    before_answer = generate(model, tokenizer, EVAL_PROMPT)
    print(f"   {EVAL_PROMPT!r} -> {before_answer!r}")

    print("\n3) Wrapping the model with a LoRA adapter (trains ~0.3% of the weights)...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["c_attn"],  # GPT-2's combined query/key/value projection
    )
    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"   Trainable params: {trainable:,} / {total:,} ({100 * trainable / total:.2f}%)")

    print(f"\n4) Building a tiny training batch ({len(TRAINING_EXAMPLES)} examples)...")
    batch = build_training_batch(tokenizer)

    print("\n5) Training (LoRA fine-tuning, all on CPU)...")
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    model.train()
    epochs = 60
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        optimizer.step()
        if epoch == 1 or epoch % 10 == 0:
            print(f"   epoch {epoch:>3}/{epochs} — loss: {loss.item():.4f}")

    print("\n6) Asking the FINE-TUNED model the same eval question...")
    model.eval()
    after_answer = generate(model, tokenizer, EVAL_PROMPT)
    print(f"   {EVAL_PROMPT!r} -> {after_answer!r}")

    print("\n7) Saving the LoRA adapter (a few hundred KB, not a full model copy)...")
    model.save_pretrained(ADAPTER_DIR)
    print(f"   Saved to {ADAPTER_DIR}")

    print(f"\n{'=' * 60}")
    print("Before fine-tuning:", before_answer)
    print("After fine-tuning: ", after_answer)
    print(f"{'=' * 60}")

    # =========================================================
    # Try it yourself:
    # 1. Change EVAL_PROMPT to one of the other Q/A pairs from
    #    TRAINING_EXAMPLES and see if it also learned that one.
    # 2. Ask a question that's NOT in TRAINING_EXAMPLES (e.g. "Q: What
    #    is Nebula's refund policy?\nA:") — the model won't know it,
    #    since fine-tuning only teaches what's in the training data.
    #    Compare that to 04_rag_demo.py, where you could add a
    #    paragraph to sample_doc.md and the model would answer
    #    correctly immediately, with no training step at all.
    # 3. Lower `epochs` to 5 and rerun — undertrained, so the "after"
    #    answer stays close to the "before" one.
    # 4. Raise `r` in LoraConfig from 8 to 32 — more trainable
    #    capacity, usually faster convergence on more/harder examples.
    # =========================================================


if __name__ == "__main__":
    main()
