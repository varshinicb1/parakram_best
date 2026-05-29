# FAQ

## General

**Q: What is Parakram?**  
Parakram is an AI-powered operating system for hardware development. Describe your project in plain English, and it generates production-ready firmware for ESP32, STM32, RP2040, and 30+ other boards.

**Q: Is it really free?**  
Yes. The core product is open source (MIT license) and free forever. We offer Pro ($9/mo) and Team ($29/mo) plans for power users who need more builds and priority LLM access.

**Q: Does it work offline?**  
Yes, with [Ollama](https://ollama.ai). Install Ollama, pull a model (`ollama pull codellama`), and Parakram connects to it locally. No API key needed.

**Q: How accurate is the generated code?**  
Our AI engine uses a 7-step pipeline with 3-attempt self-healing. If the first generation doesn't compile, it analyzes errors and fixes them automatically. Average success rate: ~85% on first attempt, ~95% with self-healing.

## Technical

**Q: Which LLM models does it use?**  
6 providers: OpenRouter (free models available), Ollama (local), Google Gemini, Anthropic Claude, OpenAI GPT-4, and Groq.

**Q: Can I use my own LLM?**  
Yes. Add any OpenAI-compatible API endpoint in Settings → LLM Models → Advanced. 

**Q: Does it need PlatformIO?**  
For compilation and flashing: yes. For AI code generation, MISRA checking, power analysis, and wiring: no. Install PlatformIO for full functionality.

**Q: What about Arduino IDE?**  
Parakram generates PlatformIO projects, but the code is standard Arduino/ESP-IDF. You can copy the generated `.ino` or `.cpp` files into Arduino IDE.

## Security & Privacy

**Q: Where is my data stored?**  
Everything runs locally on your machine. Projects are stored in your workspace directory. No code is sent to external servers except the LLM API you choose.

**Q: Are my API keys safe?**  
API keys are stored in your local `.env` file and masked in the UI. They're only sent to the respective LLM provider.

## Troubleshooting

**Q: "Build failed" — what do I do?**  
1. Check the error in Debug Terminal → Serial Monitor
2. Ensure PlatformIO CLI is installed: `pio --version`
3. Try a different LLM model (some produce better code for specific boards)
4. Use the self-healing feature: it automatically retries up to 3 times

**Q: "LLM connection failed"**  
1. Verify your API key in Settings → LLM Models
2. For Ollama: ensure `ollama serve` is running
3. Check your internet connection (for cloud providers)

---

*More questions? Email [hello@vidyutlabs.co.in](mailto:hello@vidyutlabs.co.in) or open a [GitHub Issue](https://github.com/varshinicb1/parakram/issues).*
