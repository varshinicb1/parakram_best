# API Reference

> **Base URL:** `http://localhost:8000`  
> **Swagger UI:** `http://localhost:8000/docs`

## Endpoints (	29 routers)

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/project/create` | Create a new firmware project |
| GET | `/api/project/list` | List all projects |
| POST | `/api/project/generate` | AI-generate firmware from prompt |

### Build & Flash
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/build/compile` | Compile firmware with PlatformIO |
| POST | `/api/flash/upload` | Flash firmware to connected board |
| GET | `/api/flash/ports` | List available serial ports |

### AI Engine
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/generate` | Run autonomous 7-step pipeline |
| POST | `/api/agent/v2/generate` | Enhanced agent with knowledge base |
| POST | `/api/pipeline/run` | Full pipeline with self-healing |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analysis/misra` | MISRA C:2012 compliance check |
| POST | `/api/analysis/protocol/decode` | Decode I2C/SPI/UART/CAN frames |
| POST | `/api/analysis/crash/decode` | Decode crash dumps |
| POST | `/api/rt/memory/analyze` | Analyze Flash/RAM usage |
| GET | `/api/rt/pinout/{board}` | Get board pinout data |

### Hardware
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/hardware/boards` | List all 30+ supported boards |
| POST | `/api/store/wiring/generate` | Generate wiring diagram |
| POST | `/api/hardware/export` | Export project as zip |

### Marketplace & Snippets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/store/marketplace` | Browse community extensions |
| POST | `/api/store/marketplace/search` | Search extensions |
| GET | `/api/code/snippets` | List code snippets |
| GET | `/api/code/snippets/search?q=wifi` | Search snippets |

### User Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/signup` | Register new user |
| POST | `/api/auth/login` | Login (JWT) |
| GET | `/api/users/admin/stats` | Admin signup stats |

### Subscription
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/subscription/plans` | List subscription plans |
| POST | `/api/store/stripe/webhook` | Stripe payment webhook |

---

*All endpoints return JSON. See Swagger UI at `/docs` for full request/response schemas.*
