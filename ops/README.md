# ops/ – Scripts & Runbooks

This folder contains **operational scripts** for running and deploying Bijou AI. All paths assume you run commands **from the project root** or **from `ops/`** as indicated below.

---

## Quick reference

| Script | Platform | Purpose |
|--------|----------|--------|
| `start-all.bat` | Windows | Start Bridge, Bijou AI, and Dashboard locally |
| `connect-whatsapp.bat` | Windows | Run WhatsApp Bridge in Docker and open QR code |
| `api_bijou.py` | Any | Run API-based Bijou AI (polling bridge REST API) |
| `deploy-saas.sh` | Bash (WSL/Git Bash) | Deploy Bijou AI to Fly.io with feature flags |

---

## How to run

### From project root (recommended)

```bash
# Windows
ops\start-all.bat
ops\connect-whatsapp.bat

# Start API-based Bijou (Python)
python ops/api_bijou.py
```

### From `ops/` directory

```bash
cd ops

# Windows
start-all.bat
connect-whatsapp.bat

# API-based Bijou
python api_bijou.py
```

Scripts use relative paths like `../whatsapp-bridge` and `../w3j-bijou-enterprise`, so they work when run from **project root** or from **ops/**.

---

## Script details

- **start-all.bat** – Starts WhatsApp Bridge (`../whatsapp-bridge`), then Bijou AI (`../w3j-bijou-enterprise`), then Dashboard. Bridge on :8080, Dashboard on :5000.
- **connect-whatsapp.bat** – Builds and runs the bridge in Docker, then opens http://localhost:8080 for QR linking.
- **api_bijou.py** – Connects to the bridge REST API, loads TRACE agents from `w3j-bijou-enterprise/src`, and runs the message polling loop. Requires `BRIDGE_URL`, `GEMINI_API_KEY` (or `OPENAI_API_KEY`) in env or `.env`.
- **deploy-saas.sh** – Interactive Fly.io deploy for `w3j-bijou-enterprise` (pre-flight, migrations, feature flags, deploy). Run from repo root: `bash ops/deploy-saas.sh` or from `ops/`: `./deploy-saas.sh`.

---

## Other scripts in `ops/`

- `get-qr.bat` / `get-cloud-qr.ps1` – Get QR code (local or cloud).
- `kill-all.bat` / `stop-all.bat` – Stop local services.
- `deploy-bridge.bat`, `deploy-render.ps1`, `deploy-phase2.ps1`, etc. – Deployment helpers; see script headers for usage.

For full deployment and architecture, see **PROJECT_STATUS.md** and **w3j-bijou-enterprise/docs/ARCHITECTURE.md**.
