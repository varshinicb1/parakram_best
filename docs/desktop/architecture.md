# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PARAKRAM by VIDYUTLABS                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │  React UI    │   │  FastAPI      │   │  PlatformIO  │   │
│  │  13 Spaces   │◄─►│  29 Routers  │◄─►│  Build CLI   │   │
│  │  Zustand     │   │  20 Services │   │  Flash Tool  │   │
│  └──────────────┘   └──────┬───────┘   └──────────────┘   │
│                            │                                │
│                    ┌───────┴───────┐                        │
│                    │  AI Engine    │                        │
│                    ├───────────────┤                        │
│                    │ • LLM Router  │ 6 providers            │
│                    │ • Chip KB     │ 7 MCU families          │
│                    │ • Board DB    │ 30+ variants            │
│                    │ • Datasheet   │ PDF parser              │
│                    │ • MISRA       │ 13 rules                │
│                    │ • Self-Heal   │ 3-attempt compile       │
│                    └───────────────┘                        │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │  Extensions  │   │  Marketplace │   │  SQLite DB   │   │
│  │  8 built-in  │   │  10 community│   │  Users       │   │
│  │  Hook system │   │  Ratings     │   │  Downloads   │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Autonomous Firmware Pipeline

```
User Prompt → Parse Intent → Knowledge Lookup → Generate Code
                                                      ↓
                                                Compile (PlatformIO)
                                                      ↓
                                              ┌───── Pass? ─────┐
                                              │                  │
                                             Yes                 No
                                              │                  │
                                        MISRA Check        Self-Heal (×3)
                                              │                  │
                                       Verify Output      Fix & Retry
                                              │                  │
                                        Deploy/Flash       ──────┘
```

## Frontend Spaces (13)

| Space | Purpose |
|-------|---------|
| HomeSpace | Command center, AI planner, gallery |
| WorkspaceSpace | Monaco editor, file tree, MISRA panel |
| DebugSpace | Serial monitor, protocol analyzer, crash decoder |
| CanvasSpace | Visual block programming |
| TelemetrySpace | Real-time sensor dashboard |
| DevicesSpace | Connected board management |
| BlocksSpace | Node-based visual programming |
| SettingsSpace | LLM config, API keys, themes |
| ExtensionSpace | Extension management |
| SimulationSpace | Wokwi integration |
| DocsSpace | Documentation viewer |
| ProfileSpace | User account |
| AnalyticsSpace | Usage analytics |

## Data Flow

1. **Frontend** (React + Zustand) sends HTTP/WebSocket to backend
2. **Backend** (FastAPI) routes to appropriate service
3. **AI Engine** uses LLM provider + Chip KB to generate code
4. **PlatformIO** compiles and flashes firmware
5. **WebSocket** streams real-time progress back to frontend

---

*A product by [Vidyutlabs](https://vidyutlabs.co.in)*
