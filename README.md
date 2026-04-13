# AgentNexLiFy

AI-powered lead capture and qualification chatbot for real estate agents. Each client gets an embeddable chat widget that captures leads, qualifies them, and books appointments — powered by Claude.

## Quick Start

### 1. Prerequisites
- Python 3.11 or 3.12. Python 3.14 is not supported by the pinned backend dependency set.
- A [Supabase](https://supabase.com) project
- An [Anthropic API key](https://console.anthropic.com)

### 2. Setup

```bash
cd agentnexlify
cp .env.example .env
# Edit .env with your keys

python3 -m pip install -r backend/requirements.txt
```

### 3. Database

Apply the SQL files in `migrations/` in numeric order. The active schema is documented in `docs/dev-knowledge/canonical-schema.md`; do not use the old archived `backend/models/tables.sql` path.

Verify connectivity:
```bash
python3 -m scripts.setup_supabase
```

### 4. Seed Demo Client

```bash
python3 -m scripts.seed_demo_client
```

Save the printed API key.

### 5. Run the Server

```bash
uvicorn backend.main:app --reload --port 8000
```

### 6. Test in Terminal

```bash
python3 -m scripts.test_conversation --api-key <YOUR_API_KEY>
```

### 7. Test the Widget

Open the checked-in widget preview in a browser (update the `data-api-key` attribute first), or visit:
```
http://localhost:8000/widget/preview.html
```

## Docker

```bash
docker compose up --build
```

## Embedding the Widget

Add to any website:
```html
<script src="https://your-domain.com/widget/agentnexlify-widget.js"
  data-api-key="anx_xxxxx"></script>
```

Optional attributes:
- `data-brand-color="#6cff5c"` — custom accent color
- `data-api-base="https://api.agentnexlify.com"` — custom API URL

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/chat/message` | widget API key | Send a chat message |
| GET | `/api/chat/history/{session_id}` | widget API key | Get chat history |
| GET | `/api/chat/config` | widget API key | Get widget config |
| GET | `/api/leads/{client_id}` | API secret | Get all leads |
| GET | `/api/leads/{client_id}/hot` | API secret | Get hot leads |
| GET | `/api/leads/{client_id}/summary` | API secret | Lead summary |
| POST | `/api/clients` | API secret | Create a client |
| GET | `/api/clients` | API secret | List clients |
| POST | `/api/webhooks/twilio/sms` | Twilio | Inbound SMS |
| GET | `/api/health` | none | Health check |

## Architecture

```
Widget (JS) → FastAPI → Claude API (with tools) → Supabase
                ↓
         Tool handlers → Supabase (leads)
                       → Email/SMS notifications
                       → Calendly (optional)
```
