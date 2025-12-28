# FoodLogr.app - Claude Code Project Guide

## Overview

FoodLogr is a persistent food logging agent for Claude, built as an MCP (Model Context Protocol) server. Users can track daily food intake, monitor macros, and generate weekly reports with a "fat added" metric.

## Architecture

```
                     foodlogr.app
                          |
         +----------------+----------------+
         |                                 |
   Cloud Run                        Firebase Hosting
   (MCP Server)                     (React Landing Page)
   /mcp endpoint                    foodlogr.app
         |
    Firestore
   (Multi-User DB)
```

**Pattern**: Functional Core, Imperative Shell (FCIS)
- `src/core/` - Pure functions (models, macros, reports)
- `src/shell/` - I/O operations (Firestore, auth, MCP server)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastMCP, Starlette, Uvicorn |
| Database | Google Cloud Firestore |
| Hosting | Cloud Run (backend), Firebase Hosting (web) |
| Auth | Custom API key (flr_ prefix, SHA256 hashed to user_id) |

## Project Structure

```
foodlogr.app/
├── backend/
│   ├── src/
│   │   ├── core/                    # FUNCTIONAL CORE (pure functions)
│   │   │   ├── models.py            # Pydantic models
│   │   │   ├── macros.py            # Macro calculations
│   │   │   └── reports.py           # Report generation
│   │   ├── shell/                   # IMPERATIVE SHELL (I/O)
│   │   │   ├── firestore_client.py  # Firestore operations
│   │   │   ├── auth.py              # API key auth
│   │   │   └── mcp_server.py        # MCP tool definitions
│   │   └── main.py                  # Entry point (Starlette + MCP)
│   ├── tests/
│   │   └── core/                    # Unit tests for pure functions
│   ├── Dockerfile
│   └── requirements.txt
├── web/                             # React landing page
│   ├── src/
│   ├── package.json
│   └── firebase.json
└── CLAUDE.md                        # This file
```

## Deployment

### Backend (Cloud Run)

```bash
cd backend
gcloud run deploy foodlogr-mcp \
  --source . \
  --region us-central1 \
  --project foodlogr-app \
  --allow-unauthenticated
```

**Service URL**: `https://foodlogr-mcp-504360050716.us-central1.run.app`

### Frontend (Firebase Hosting)

```bash
cd web
npm run build
firebase deploy --only hosting --project foodlogr-app
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check for Cloud Run |
| `/auth/register` | POST | Register user, returns API key |
| `/auth/validate` | POST | Validate an API key |
| `/mcp` | POST | MCP protocol endpoint |

## MCP Tools (10 total)

| Tool | Description |
|------|-------------|
| `setup_user` | Configure calorie/macro goals and resting energy |
| `get_settings` | Get current user settings |
| `log_food` | Add food entry to today's log |
| `update_food` | Modify existing entry |
| `delete_food` | Remove entry |
| `get_today` | Today's log + summary |
| `get_day` | Specific day's log |
| `get_weekly_report` | Weekly summary + fat_added metric |
| `search_cache` | Search user's saved foods |
| `add_to_cache` | Save food for quick reuse |

## Firestore Data Model

```
users/{user_id}/
  ├── settings (document)
  │     └── { calorie_goal, protein_goal, carb_goal, fat_goal, resting_energy }
  ├── logs/{YYYY-MM-DD} (documents)
  │     └── { log_date, entries: [...] }
  └── cache/{food_id} (documents)
        └── { name, calories, protein, carbs, fat, use_count }
```

## Authentication Flow

1. User registers via `POST /auth/register` with email
2. Server generates API key: `flr_` + 32 random chars (URL-safe base64)
3. API key is SHA256 hashed to create `user_id`
4. User configures Claude with: `claude mcp add --transport http foodlogr <URL>/mcp --header "Authorization: Bearer <API_KEY>"`
5. Auth middleware extracts Bearer token, validates, sets `current_user_id` context var

## Key Implementation Details

### FastMCP Configuration

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "localhost:*",
        "127.0.0.1:*",
        "*.run.app:*",
        "*.run.app",
        "foodlogr-mcp-504360050716.us-central1.run.app:*",
        "foodlogr-mcp-504360050716.us-central1.run.app",
    ],
)

mcp = FastMCP(
    "foodlogr",
    stateless_http=True,
    transport_security=transport_security,
)
```

### Starlette App Setup (main.py)

```python
def create_app() -> Starlette:
    mcp_app = mcp.streamable_http_app()

    routes = [
        Route("/health", health_check, methods=["GET"]),
        Route("/auth/register", register_user, methods=["POST"]),
        Route("/auth/validate", validate_key, methods=["POST"]),
        Mount("/", app=mcp_app),  # MCP handles /mcp/ internally
    ]

    app = Starlette(
        routes=routes,
        middleware=[Middleware(AuthMiddleware)],
        lifespan=mcp_app.router.lifespan_context,  # Required for MCP task group
    )
    return app
```

### User Context (ContextVar)

```python
from contextvars import ContextVar
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)

# In tools:
def get_user_id() -> str:
    user_id = current_user_id.get()
    if user_id is None:
        raise RuntimeError("No authenticated user")
    return user_id
```

## Testing

### Unit Tests (Core - Pure Functions)
```bash
cd backend
pytest tests/core/ -v
```

### Manual MCP Testing
```bash
# Initialize
curl -X POST "https://foodlogr-mcp-504360050716.us-central1.run.app/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <API_KEY>" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}'

# List tools
curl -X POST "https://foodlogr-mcp-504360050716.us-central1.run.app/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <API_KEY>" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}'
```

## Common Issues & Solutions

### "Invalid Host header" / 421 Misdirected Request
- **Cause**: FastMCP DNS rebinding protection
- **Fix**: Add Cloud Run domain to `allowed_hosts` in `TransportSecuritySettings`

### "Task group is not initialized"
- **Cause**: Missing lifespan context when mounting MCP app
- **Fix**: Pass `lifespan=mcp_app.router.lifespan_context` to Starlette

### MCP endpoint returns 404 at /mcp/
- **Cause**: Double-mounting (mounting at /mcp when app expects /mcp internally)
- **Fix**: Mount MCP app at root `/`, it handles `/mcp/` path internally

### "Client must accept both application/json and text/event-stream"
- **Cause**: Missing Accept header for streamable HTTP
- **Fix**: Include `Accept: application/json, text/event-stream` header

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8080 | Server port (set by Cloud Run) |
| `HOST` | 0.0.0.0 | Server host |
| `FIRESTORE_DATABASE` | foodlogr | Firestore database name |
| `BASE_URL` | (Cloud Run URL) | Base URL for registration response |

## Claude Code Configuration

```bash
# Add the MCP server
claude mcp add --transport http foodlogr \
  https://foodlogr-mcp-504360050716.us-central1.run.app/mcp \
  --header "Authorization: Bearer <YOUR_API_KEY>"

# Remove if needed
claude mcp remove foodlogr
```

## GCP Resources

- **Project**: `foodlogr-app`
- **Region**: `us-central1`
- **Cloud Run Service**: `foodlogr-mcp`
- **Firestore Database**: `foodlogr`

## Key Files to Know

| File | Purpose |
|------|---------|
| `backend/src/main.py` | Entry point, Starlette app setup, auth middleware |
| `backend/src/shell/mcp_server.py` | All 10 MCP tool definitions |
| `backend/src/shell/firestore_client.py` | Firestore CRUD operations |
| `backend/src/shell/auth.py` | API key generation, hashing, validation |
| `backend/src/core/models.py` | Pydantic models (UserSettings, FoodEntry, etc.) |
| `backend/src/core/reports.py` | Weekly report generation, fat_added calculation |
| `.github/workflows/deploy.yml` | GitHub Actions auto-deploy workflow |

## GitHub Actions (CI/CD)

Auto-deployment is configured via `.github/workflows/deploy.yml`. On merge to `main`:
- Detects changes in `backend/` or `web/` directories
- Runs tests for backend changes
- Deploys backend to Cloud Run (if changed)
- Deploys web to Firebase Hosting (if changed)

### Required Secrets

Set these in GitHub repo Settings → Secrets and variables → Actions:

| Secret | Description |
|--------|-------------|
| `WIF_PROVIDER` | Workload Identity Federation provider |
| `WIF_SERVICE_ACCOUNT` | GCP service account for WIF |
| `FIREBASE_SERVICE_ACCOUNT_FOODLOGR_APP` | Firebase service account JSON |

### Setting Up Workload Identity Federation

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions" \
  --project=foodlogr-app

# Grant permissions
gcloud projects add-iam-policy-binding foodlogr-app \
  --member="serviceAccount:github-actions@foodlogr-app.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding foodlogr-app \
  --member="serviceAccount:github-actions@foodlogr-app.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding foodlogr-app \
  --member="serviceAccount:github-actions@foodlogr-app.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool" \
  --project=foodlogr-app

# Create Provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --project=foodlogr-app

# Allow GitHub repo to impersonate service account
gcloud iam service-accounts add-iam-policy-binding \
  github-actions@foodlogr-app.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/504360050716/locations/global/workloadIdentityPools/github-pool/attribute.repository/ravigummadi/foodlogr.app" \
  --project=foodlogr-app

# Get the WIF_PROVIDER value (save this as secret)
echo "projects/504360050716/locations/global/workloadIdentityPools/github-pool/providers/github-provider"

# WIF_SERVICE_ACCOUNT value
echo "github-actions@foodlogr-app.iam.gserviceaccount.com"
```

### Firebase Service Account

Generate via Firebase Console → Project Settings → Service Accounts → Generate new private key.
Save the JSON content as `FIREBASE_SERVICE_ACCOUNT_FOODLOGR_APP` secret.

### Manual Trigger

The workflow can also be triggered manually from GitHub Actions tab with options to deploy backend, web, or both.
