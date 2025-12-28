# FoodLogr

Persistent food logging agent for Claude. Track your food and macros with AI assistance.

## Architecture

```
foodlogr.app/
├── backend/                 # Python MCP server (Cloud Run)
│   ├── src/
│   │   ├── core/           # Functional Core (pure functions)
│   │   │   ├── models.py   # Pydantic data models
│   │   │   ├── macros.py   # Macro calculations
│   │   │   └── reports.py  # Report generation
│   │   ├── shell/          # Imperative Shell (I/O)
│   │   │   ├── auth.py     # API key authentication
│   │   │   ├── firestore_client.py
│   │   │   └── mcp_server.py  # MCP tool definitions
│   │   └── main.py         # Entry point
│   └── tests/
└── web/                    # React landing page (Firebase Hosting)
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `setup_user` | Configure daily goals and resting energy |
| `get_settings` | Get current user settings |
| `log_food` | Add food entry to today's log |
| `update_food` | Modify existing entry |
| `delete_food` | Remove entry |
| `get_today` | Today's log with summary |
| `get_day` | Specific day's log |
| `get_weekly_report` | Weekly summary with fat metric |
| `search_cache` | Search user's foods |
| `add_to_cache` | Save food for reuse |

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start server locally
python -m src.main
```

### Web

```bash
cd web

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Deployment

### 1. Create Firestore Database

```bash
gcloud firestore databases create \
    --location=us-central1 \
    --type=firestore-native \
    --database=foodlogr
```

### 2. Deploy Backend to Cloud Run

```bash
cd backend
gcloud run deploy foodlogr-mcp \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
```

### 3. Map Custom Domain

```bash
gcloud run domain-mappings create \
    --service foodlogr-mcp \
    --domain mcp.foodlogr.app \
    --region us-central1
```

### 4. Deploy Web to Firebase Hosting

```bash
cd web
npm run build
firebase deploy --only hosting
```

## Connecting Claude

After getting your API key from foodlogr.app:

```bash
claude mcp add \
    --transport http \
    foodlogr \
    https://mcp.foodlogr.app/mcp \
    --header "Authorization: Bearer flr_YOUR_API_KEY"
```

## Usage

Start a Claude conversation:

```
> Set up my food goals: 2000 cal, 150g protein, 200g carbs, 1800 resting energy

> I had a cappuccino with 2% milk

> Log 2 scrambled eggs with butter

> Show me today's summary

> Give me my weekly report
```
