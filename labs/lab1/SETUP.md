# Environment Setup Guide — Tool Calling Labs

This guide walks through setting up your machine to run everything in
`labs/`. All tools are free and open-source — no OpenAI key or paid
subscription required.

**Expected setup time:** 15-25 minutes (mostly download waiting).

---

## 1. Prerequisites

### Python 3.11 or newer (3.12 recommended)

- Download from: https://www.python.org/downloads/
- Check your version:
  ```bash
  python3 --version
  ```
- ⚠️ If your machine has the very latest Python (3.14+), some ML
  libraries (e.g. `chromadb` and `torch`) may not yet ship prebuilt
  wheels for it. If you hit install errors, install Python 3.12
  specifically and create the virtual environment with it (on Mac:
  `brew install python@3.12`).

### Git

- Download from: https://git-scm.com/downloads

### Docker Desktop

Docker lets us run supporting services in a way that's consistent
across every trainee's machine (e.g. a standalone vector database
instead of local Chroma, in future exercises).

- **Windows / Mac**: download Docker Desktop from
  https://www.docker.com/products/docker-desktop/
- **Linux**: follow the official instructions for your distro:
  https://docs.docker.com/engine/install/
- After installing, verify:
  ```bash
  docker --version
  ```
- Note: this session's labs (00-04) do **not** actually require
  Docker — Chroma runs locally inside Python directly, no containers
  needed. Install it now anyway, since later sessions in the course
  will need it.

---

## 2. Create the virtual environment

From inside the `labs/` folder:

```bash
# Create the environment
python3 -m venv venv

# Activate — macOS / Linux
source venv/bin/activate

# Activate — Windows (Command Prompt)
venv\Scripts\activate.bat

# Activate — Windows (PowerShell)
venv\Scripts\Activate.ps1
```

Once activated, you should see `(venv)` at the start of your prompt.
Then install the required packages (versions are pinned so everyone
runs the exact same set):

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This pulls in a few fairly large libraries (`torch`, `transformers`,
`chromadb`) — it can take a few minutes depending on connection speed.

---

## 3. Get a HuggingFace API token (free)

This is **only** needed if you later choose the HuggingFace path
instead of local Ollama (section 5). If you'll use Ollama only, you
can skip this section for now.

1. Create a free account at https://huggingface.co
2. Go to: **Settings → Access Tokens → New Token**
3. Choose the **Read** permission type
4. Copy the token (starts with `hf_...`)

Now create a `.env` file from the provided template:

```bash
cp .env.example .env
```

Then open `.env` and set the token:

```
HUGGINGFACEHUB_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ `.env` is already listed in `.gitignore` — never commit it to any
public repository.

---

## 4. Install and run Ollama (primary local option)

[Ollama](https://ollama.com) runs open-source language models
entirely on your own machine — no internet needed after the download,
and no cost.

### Install

- **macOS**: `brew install --cask ollama` or download from https://ollama.com/download
- **Windows**: download from https://ollama.com/download
- **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`

### Pull a tool-calling-capable model

⚠️ **Important**: not every model supports tool calling. The
following are tested and do support it:

| Model | Command | Approx. size | Recommended RAM |
|---|---|---|---|
| **qwen2.5:7b** (used in these labs, recommended) | `ollama pull qwen2.5:7b` | ~4.7 GB | 8 GB+ |
| llama3.1:8b (popular alternative) | `ollama pull llama3.1:8b` | ~4.9 GB | 8 GB+ |
| qwen2.5:3b (low-spec machines) | `ollama pull qwen2.5:3b` | ~1.9 GB | 4 GB+ |
| llama3.2:3b (low-spec machines) | `ollama pull llama3.2:3b` | ~2 GB | 4 GB+ |

All `labs/` files default to `qwen2.5:7b`. If you pull a different
model, update the value in `.env`:

```
OLLAMA_MODEL=qwen2.5:3b
```

### Run and test

After installing Ollama (the macOS/Windows app runs the service
automatically in the background; on Linux you may need `ollama serve`
manually):

```bash
ollama run qwen2.5:7b "hello"
```

If the model replies with text, everything works. Exit by typing
`/bye`.

---

## 5. Alternative path: no local model (HuggingFace Inference API)

If your machine is underpowered and can't comfortably run a local
model, you can use the HuggingFace Inference API over the network
instead of Ollama.

1. Make sure you created `.env` and set `HUGGINGFACEHUB_API_TOKEN`
   (section 3).
2. In `.env`, set:
   ```
   USE_HUGGINGFACE=1
   ```
3. Every file in `labs/` reads this variable automatically and
   switches paths — no code changes needed.

Note: this path is slower (network latency) and may be subject to
rate limits on the free tier.

---

## 6. Final verification

Run the full check script:

```bash
python 00_check_setup.py
```

You should see ✅ next to every item (except
`HUGGINGFACEHUB_API_TOKEN` if you're using Ollama only — that will
show as ⚠️, not ❌, which is expected).

If everything shows ✅ (or just one warning), you're ready. Move on
to `01_hello_world.py`.

---

## Quick troubleshooting

See the "Troubleshooting" section in `README.md` too.
