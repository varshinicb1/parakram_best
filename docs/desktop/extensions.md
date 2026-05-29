# Building Extensions

## Overview

Parakram uses a **VS Code-style extension system**. Extensions can:
- Add new board support
- Create custom code generators
- Add protocol analyzers
- Build custom UI panels
- Integrate with external services

## Extension Structure

```
my-extension/
├── extension.json     # Manifest
├── main.py            # Entry point
├── templates/         # Code templates
└── README.md          # Documentation
```

## Manifest (extension.json)

```json
{
  "id": "my-custom-extension",
  "name": "My Custom Extension",
  "version": "1.0.0",
  "description": "What this extension does",
  "author": "Your Name",
  "category": "connectivity",
  "boards": ["esp32dev", "pico"],
  "hooks": ["on_generate", "on_compile", "on_flash"],
  "dependencies": ["WiFi.h"]
}
```

## Available Hooks

| Hook | When It Fires | Use Case |
|------|--------------|----------|
| `on_project_create` | New project created | Add default files |
| `on_generate` | AI generates code | Inject custom code |
| `on_compile` | Before compilation | Add build flags |
| `on_compile_success` | Build passes | Run post-build scripts |
| `on_compile_error` | Build fails | Custom error handling |
| `on_flash` | Before flashing | Verify firmware |
| `on_flash_success` | Flash completes | Run post-flash tests |
| `on_serial_data` | Serial data received | Custom protocol parsing |

## Example: Custom Sensor Extension

```python
# main.py
class MySensorExtension:
    def on_generate(self, context):
        """Inject sensor initialization code."""
        if "my_sensor" in context.get("components", []):
            return {
                "includes": ["#include <MySensor.h>"],
                "setup": ["mySensor.begin();"],
                "loop": ["float val = mySensor.read();"],
                "libraries": ["MySensorLib"],
            }
        return None
```

## Publishing to Marketplace

1. Fork the [extensions repository](https://github.com/varshinicb1/parakram-extensions)
2. Add your extension folder
3. Submit a Pull Request
4. Vidyutlabs reviews and publishes

---

*A product by [Vidyutlabs](https://vidyutlabs.co.in)*
