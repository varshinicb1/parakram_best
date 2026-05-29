"""
Multi-Provider LLM Router — supports any provider with user-managed API keys.

Free OpenRouter models are used by default. Users can add their own API keys
for any provider (OpenAI, Anthropic, etc.) via the settings API.

Providers:
  - OpenRouter (free models: DeepSeek, Gemma, Llama, Qwen, Mistral)
  - OpenRouter (paid models: Claude, GPT-4o — requires user API key)
  - Ollama (local inference)
  - Parakram Custom (fine-tuned model)
  - Any OpenAI-compatible endpoint (user-configurable)
"""

import os
import re
import json
import aiohttp
from pathlib import Path
from typing import Optional
from enum import Enum


# ─── Configuration ──────────────────────────────────────────
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CODE_MODEL = os.environ.get("OLLAMA_CODE_MODEL", "qwen2.5-coder:7b-instruct")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# User settings file
SETTINGS_FILE = Path(os.environ.get("PARAKRAM_SETTINGS_DIR", "./storage")) / "llm_settings.json"

# ESP32 system prompt
ESP32_SYSTEM_PROMPT = """You are an expert ESP32 firmware engineer specializing in Arduino framework development.

Rules:
1. Generate ONLY valid, compilable C++ code for ESP32 Arduino
2. Use proper #include guards in headers (#ifndef / #define / #endif)
3. Prefix all functions with the module name (e.g., bme280_setup, bme280_loop)
4. Always include error handling and Serial debug output
5. Use static variables for module state (avoid globals)
6. Initialize hardware with retry logic where applicable
7. Include proper library #includes
8. Follow this response format EXACTLY when generating modules:

===HEADER===
(complete .h file content)
===SOURCE===
(complete .cpp file content)
"""


# ─── Free OpenRouter Models ─────────────────────────────────
FREE_MODELS = [
    {
        "id": "qwen/qwen3-coder:free",
        "name": "Qwen3 Coder",
        "provider": "openrouter",
        "category": "coding",
        "context": 65536,
        "free": True,
    },
    {
        "id": "nvidia/nemotron-3-super-120b-a12b:free",
        "name": "Nemotron 3 Super 120B",
        "provider": "openrouter",
        "category": "coding",
        "context": 131072,
        "free": True,
    },
    {
        "id": "mistralai/mistral-small-3.1-24b-instruct:free",
        "name": "Mistral Small 3.1 24B",
        "provider": "openrouter",
        "category": "coding",
        "context": 96000,
        "free": True,
    },
    {
        "id": "stepfun/step-3.5-flash:free",
        "name": "Step 3.5 Flash",
        "provider": "openrouter",
        "category": "general",
        "context": 131072,
        "free": True,
    },
    {
        "id": "openai/gpt-oss-120b:free",
        "name": "GPT-OSS 120B",
        "provider": "openrouter",
        "category": "coding",
        "context": 131072,
        "free": True,
    },
    {
        "id": "google/gemma-3n-e4b-it:free",
        "name": "Gemma 3n E4B",
        "provider": "openrouter",
        "category": "general",
        "context": 32768,
        "free": True,
    },
    {
        "id": "nvidia/nemotron-nano-9b-v2:free",
        "name": "Nemotron Nano 9B v2",
        "provider": "openrouter",
        "category": "coding",
        "context": 131072,
        "free": True,
    },
    {
        "id": "qwen/qwen3-4b:free",
        "name": "Qwen3 4B",
        "provider": "openrouter",
        "category": "general",
        "context": 32768,
        "free": True,
    },
]


# ─── User Settings Management ────────────────────────────────

def _load_settings() -> dict:
    """Load user LLM settings from disk."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {
        "active_model": "groq-llama",
        "api_keys": {},
        "custom_providers": [],
    }


def _save_settings(settings: dict):
    """Save user LLM settings to disk."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def get_settings() -> dict:
    return _load_settings()


def update_settings(updates: dict) -> dict:
    settings = _load_settings()
    settings.update(updates)
    _save_settings(settings)
    return settings


def set_api_key(provider: str, key: str) -> dict:
    """Set an API key for a provider."""
    settings = _load_settings()
    settings.setdefault("api_keys", {})[provider] = key
    _save_settings(settings)
    return {"status": "saved", "provider": provider}


def get_api_key(provider: str) -> str:
    """Get the API key for a provider."""
    settings = _load_settings()
    keys = settings.get("api_keys", {})
    # Check user-stored keys first, then env vars
    if provider in keys and keys[provider]:
        return keys[provider]
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    return os.environ.get(env_map.get(provider, ""), "")


def add_custom_provider(provider: dict) -> dict:
    """Add a custom OpenAI-compatible provider."""
    settings = _load_settings()
    settings.setdefault("custom_providers", [])
    # Remove existing with same id
    settings["custom_providers"] = [
        p for p in settings["custom_providers"] if p.get("id") != provider.get("id")
    ]
    settings["custom_providers"].append(provider)
    _save_settings(settings)
    return {"status": "added", "provider": provider}


def remove_custom_provider(provider_id: str) -> dict:
    """Remove a custom provider."""
    settings = _load_settings()
    settings["custom_providers"] = [
        p for p in settings.get("custom_providers", []) if p.get("id") != provider_id
    ]
    _save_settings(settings)
    return {"status": "removed", "id": provider_id}


# ─── Code Extraction ─────────────────────────────────────────

def _extract_code(response: str) -> dict:
    """Extract header and source from LLM response."""
    header = ""
    source = ""

    if not response:
        return {"header": "", "source": ""}

    if "===HEADER===" in response and "===SOURCE===" in response:
        parts = response.split("===SOURCE===")
        header = parts[0].replace("===HEADER===", "").strip()
        source = parts[1].strip() if len(parts) > 1 else ""
    elif "```" in response:
        code_blocks = re.findall(r'```(?:cpp|c|arduino)?\s*\n(.*?)```', response, re.DOTALL)
        if len(code_blocks) >= 2:
            header = code_blocks[0].strip()
            source = code_blocks[1].strip()
        elif len(code_blocks) == 1:
            code = code_blocks[0].strip()
            if "#ifndef" in code and "#endif" in code:
                header = code
            else:
                source = code
    else:
        if "#ifndef" in response and "#include" in response:
            endif_pos = response.find("#endif")
            if endif_pos > 0:
                header = response[:endif_pos + len("#endif")].strip()
                source = response[endif_pos + len("#endif"):].strip()
            else:
                source = response.strip()
        else:
            source = response.strip()

    for fence in ["```cpp", "```c", "```arduino", "```"]:
        header = header.replace(fence, "")
        source = source.replace(fence, "")

    return {"header": header.strip(), "source": source.strip()}


# ─── Provider Implementations ────────────────────────────────

class OpenRouterProvider:
    """OpenRouter provider — routes to any model via OpenRouter API."""

    def __init__(self, model_id: str, api_key: str = ""):
        self.model_id = model_id
        self.api_key = api_key or get_api_key("openrouter")
        self.base_url = OPENROUTER_BASE_URL

    async def generate(self, prompt: str, max_tokens: int = 2000,
                       system: str = None, temperature: float = 0.3) -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            headers = {
                "Content-Type": "application/json",
                "HTTP-Referer": "https://vidyutlabs.com",
                "X-Title": "Parakram by Vidyutlabs",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                        return ""
                    else:
                        body = await resp.text()
                        print(f"[OpenRouter] HTTP {resp.status}: {body[:300]}")
                        return ""
        except Exception as e:
            print(f"[OpenRouter] Generate error: {e}")
            return ""

    async def generate_code(self, prompt: str, max_tokens: int = 3000) -> dict:
        response = await self.generate(
            prompt=prompt, max_tokens=max_tokens,
            system=ESP32_SYSTEM_PROMPT, temperature=0.2,
        )
        return _extract_code(response)

    async def embed(self, text: str) -> list[float]:
        # Fall back to Ollama for embeddings
        ollama = OllamaProvider()
        return await ollama.embed(text)

    def is_available(self) -> bool:
        # Free models don't require API key
        return self.model_id.endswith(":free") or bool(self.api_key)

    @property
    def name(self) -> str:
        return f"OpenRouter ({self.model_id})"


class GeminiProvider:
    """Google Gemini API provider — free tier, 1M context, excellent code generation.
    Get a free API key at: https://aistudio.google.com/apikey
    """

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str = ""):
        self.model = model
        self.api_key = api_key or get_api_key("google") or os.environ.get("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, prompt: str, max_tokens: int = 3000,
                       system: str = None, temperature: float = 0.3) -> str:
        if not self.api_key:
            print("[Gemini] No API key. Get one free at https://aistudio.google.com/apikey")
            return ""
        try:
            contents = []
            if system:
                contents.append({"role": "user", "parts": [{"text": system}]})
                contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature,
                },
            }

            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            return parts[0].get("text", "") if parts else ""
                        return ""
                    else:
                        body = await resp.text()
                        print(f"[Gemini] HTTP {resp.status}: {body[:300]}")
                        return ""
        except Exception as e:
            print(f"[Gemini] Generate error: {e}")
            return ""

    async def generate_code(self, prompt: str, max_tokens: int = 4000) -> dict:
        response = await self.generate(
            prompt=prompt, max_tokens=max_tokens,
            system=ESP32_SYSTEM_PROMPT, temperature=0.2,
        )
        return _extract_code(response)

    async def embed(self, text: str) -> list[float]:
        ollama = OllamaProvider()
        return await ollama.embed(text)

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"


class GroqProvider:
    """Groq API provider — free tier, Llama 3.3 70B, blazing fast inference.
    Get a free API key at: https://console.groq.com/keys
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile", api_key: str = ""):
        self.model = model
        self.api_key = api_key or get_api_key("groq") or os.environ.get("GROQ_API_KEY", "")
        self.base_url = "https://api.groq.com/openai/v1"

    async def generate(self, prompt: str, max_tokens: int = 3000,
                       system: str = None, temperature: float = 0.3) -> str:
        if not self.api_key:
            print("[Groq] No API key. Get one free at https://console.groq.com/keys")
            return ""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                        return ""
                    else:
                        body = await resp.text()
                        print(f"[Groq] HTTP {resp.status}: {body[:300]}")
                        return ""
        except Exception as e:
            print(f"[Groq] Generate error: {e}")
            return ""

    async def generate_code(self, prompt: str, max_tokens: int = 4000) -> dict:
        response = await self.generate(
            prompt=prompt, max_tokens=max_tokens,
            system=ESP32_SYSTEM_PROMPT, temperature=0.2,
        )
        return _extract_code(response)

    async def embed(self, text: str) -> list[float]:
        ollama = OllamaProvider()
        return await ollama.embed(text)

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def name(self) -> str:
        return f"Groq ({self.model})"

class GenericOpenAIProvider:
    """Any OpenAI-compatible API endpoint (user-configured)."""

    def __init__(self, base_url: str, model: str, api_key: str = "", name_str: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._name = name_str or f"Custom ({model})"

    async def generate(self, prompt: str, max_tokens: int = 2000,
                       system: str = None, temperature: float = 0.3) -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                        return ""
                    else:
                        body = await resp.text()
                        print(f"[{self._name}] HTTP {resp.status}: {body[:300]}")
                        return ""
        except Exception as e:
            print(f"[{self._name}] Generate error: {e}")
            return ""

    async def generate_code(self, prompt: str, max_tokens: int = 3000) -> dict:
        response = await self.generate(
            prompt=prompt, max_tokens=max_tokens,
            system=ESP32_SYSTEM_PROMPT, temperature=0.2,
        )
        return _extract_code(response)

    async def embed(self, text: str) -> list[float]:
        return []

    def is_available(self) -> bool:
        return bool(self.base_url)

    @property
    def name(self) -> str:
        return self._name


class OllamaProvider:
    """Ollama-based LLM provider for local inference."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.code_model = OLLAMA_CODE_MODEL
        self.embed_model = EMBED_MODEL

    async def generate(self, prompt: str, max_tokens: int = 2000,
                       system: str = None, temperature: float = 0.3) -> str:
        try:
            payload = {
                "model": self.code_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
            }
            if system:
                payload["system"] = system

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "")
                    else:
                        body = await resp.text()
                        print(f"[Ollama] HTTP {resp.status}: {body[:200]}")
                        return ""
        except Exception as e:
            print(f"[Ollama] Generate error: {e}")
            return ""

    async def generate_code(self, prompt: str, max_tokens: int = 3000) -> dict:
        response = await self.generate(
            prompt=prompt, max_tokens=max_tokens,
            system=ESP32_SYSTEM_PROMPT, temperature=0.2,
        )
        return _extract_code(response)

    async def embed(self, text: str) -> list[float]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.embed_model, "input": text},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embs = data.get("embeddings", [])
                        return embs[0] if embs else []
                    return []
        except Exception as e:
            print(f"[Ollama] Embed error: {e}")
            return []

    def is_available(self) -> bool:
        return bool(self.base_url)

    @property
    def name(self) -> str:
        return f"Ollama ({self.code_model})"


class StubProvider:
    """Fallback when no LLM is available."""

    async def generate(self, prompt: str, **kwargs) -> str:
        return ""

    async def generate_code(self, prompt: str, **kwargs) -> dict:
        return {"header": "", "source": ""}

    async def embed(self, text: str) -> list[float]:
        return []

    def is_available(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return "Stub (no LLM)"


# ─── Provider Router (Singleton) ──────────────────────────────

class LLMRouter:
    """Routes LLM requests to the active provider. User-configurable."""

    def __init__(self):
        self._active_model_id = ""
        self._load_from_settings()

    def _load_from_settings(self):
        settings = _load_settings()
        self._active_model_id = settings.get("active_model", "gemini-flash")

    def _get_provider(self, model_id: str = None):
        """Dynamically create the correct provider for a model ID."""
        mid = model_id or self._active_model_id

        # Google Gemini models
        if mid == "gemini-flash":
            return GeminiProvider(model="gemini-2.0-flash")
        if mid == "gemini-pro":
            return GeminiProvider(model="gemini-2.5-pro-preview-06-05")
        if mid.startswith("gemini-"):
            return GeminiProvider(model=mid.replace("gemini-", ""))

        # Groq models
        if mid == "groq-llama":
            return GroqProvider(model="llama-3.3-70b-versatile")
        if mid.startswith("groq-"):
            return GroqProvider(model=mid.replace("groq-", ""))

        # Ollama local models
        if mid == "ollama" or mid.startswith("ollama/"):
            return OllamaProvider()

        # Parakram custom
        if mid == "parakram-custom":
            p = OllamaProvider()
            p.code_model = os.environ.get("PARAKRAM_CUSTOM_MODEL", "parakram-coder:latest")
            return p

        # Custom user-configured providers
        settings = _load_settings()
        for cp in settings.get("custom_providers", []):
            if cp.get("id") == mid:
                return GenericOpenAIProvider(
                    base_url=cp.get("base_url", ""),
                    model=cp.get("model", mid),
                    api_key=cp.get("api_key", ""),
                    name_str=cp.get("name", mid),
                )

        # Default: OpenRouter
        api_key = get_api_key("openrouter")
        return OpenRouterProvider(model_id=mid, api_key=api_key)

    @property
    def active(self):
        return self._get_provider()

    @property
    def active_model_id(self) -> str:
        return self._active_model_id

    def switch(self, model_id: str):
        self._active_model_id = model_id
        settings = _load_settings()
        settings["active_model"] = model_id
        _save_settings(settings)
        print(f"[LLM Router] Switched to: {model_id}")

    def list_models(self) -> list[dict]:
        """List all available models (free + user-configured)."""
        models = []

        # Free OpenRouter models
        for m in FREE_MODELS:
            models.append({
                **m,
                "active": m["id"] == self._active_model_id,
            })

        # Ollama local
        models.append({
            "id": "ollama",
            "name": "Ollama (Local)",
            "provider": "ollama",
            "category": "local",
            "context": 32768,
            "free": True,
            "active": self._active_model_id == "ollama",
        })

        # Parakram custom
        models.append({
            "id": "parakram-custom",
            "name": "Parakram Custom Model",
            "provider": "ollama",
            "category": "coding",
            "context": 32768,
            "free": True,
            "active": self._active_model_id == "parakram-custom",
        })

        # Google Gemini (free)
        models.append({
            "id": "gemini-flash",
            "name": "Gemini 2.0 Flash (Recommended)",
            "provider": "google",
            "category": "coding",
            "context": 1048576,
            "free": True,
            "active": self._active_model_id == "gemini-flash",
        })
        models.append({
            "id": "gemini-pro",
            "name": "Gemini 2.5 Pro",
            "provider": "google",
            "category": "reasoning",
            "context": 1048576,
            "free": True,
            "active": self._active_model_id == "gemini-pro",
        })

        # Groq (free)
        models.append({
            "id": "groq-llama",
            "name": "Llama 3.3 70B (Groq)",
            "provider": "groq",
            "category": "coding",
            "context": 131072,
            "free": True,
            "active": self._active_model_id == "groq-llama",
        })

        # User custom providers
        settings = _load_settings()
        for cp in settings.get("custom_providers", []):
            models.append({
                "id": cp.get("id"),
                "name": cp.get("name", cp.get("id")),
                "provider": cp.get("provider_name", "custom"),
                "category": cp.get("category", "custom"),
                "context": cp.get("context", 8192),
                "free": False,
                "active": cp.get("id") == self._active_model_id,
            })

        return models

    async def generate(self, prompt: str, **kwargs) -> str:
        return await self.active.generate(prompt, **kwargs)

    async def generate_code(self, prompt: str, **kwargs) -> dict:
        return await self.active.generate_code(prompt, **kwargs)

    async def embed(self, text: str) -> list[float]:
        return await self.active.embed(text)


# ─── Global Singleton ─────────────────────────────────────────
_router: Optional[LLMRouter] = None


def get_provider() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
        print(f"[LLM Router] Initialized. Active: {_router.active_model_id}")
    return _router


def get_router() -> LLMRouter:
    return get_provider()
