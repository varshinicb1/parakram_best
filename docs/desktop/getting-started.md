# Getting Started with Parakram

## Prerequisites

- **Python 3.10+** — Backend
- **Node.js 18+** — Frontend
- **PlatformIO CLI** — Firmware compilation (optional for AI-only mode)

## Quick Install

```bash
# 1. Clone the repository
git clone https://github.com/varshinicb1/parakram.git
cd parakram

# 2. Start the backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
uvicorn main:app --reload --port 8000

# 3. Start the frontend (new terminal)
cd desktop
npm install
npm run dev
```

## First Project

1. Open **http://localhost:3000** in your browser
2. Click **"New Project"** on the Home screen
3. Type: `Blink LED on ESP32 GPIO2`
4. Watch Parakram generate firmware, check MISRA compliance, and prepare the build

## API Keys

Parakram works with **6 LLM providers**. You need at least one:

| Provider | Key Variable | Free Tier |
|----------|-------------|-----------|
| OpenRouter | `OPENROUTER_API_KEY` | ✅ Free models available |
| Ollama | (local, no key) | ✅ Fully free |
| Groq | `GROQ_API_KEY` | ✅ Free tier |
| Gemini | `GEMINI_API_KEY` | ✅ Free tier |
| OpenAI | `OPENAI_API_KEY` | ❌ Paid |
| Anthropic | `ANTHROPIC_API_KEY` | ❌ Paid |

## Architecture

```
http://localhost:8000/docs  →  Swagger UI (29 endpoints)
http://localhost:3000       →  Parakram Desktop UI
```

## Next Steps

- [API Reference](api-reference.md)
- [Board Database](boards.md)
- [Build Extensions](extensions.md)

---

*A product by [Vidyutlabs](https://vidyutlabs.co.in)*
