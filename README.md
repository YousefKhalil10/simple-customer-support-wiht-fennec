# 🦊 Fennec Customer Support System

> **Production-ready AI customer support powered by [Fennec RAG](https://fennec-community.vercel.app/)**
> — Conversational RAG · Semantic Routing · Arabic Support

---

## ✨ What This Does

A full-stack intelligent customer support system that:

| Feature | Description |
|---|---|
| 🧭 **Semantic Routing** | Automatically classifies queries into FAQ / Orders / Returns / Technical / Complaints / General |
| 🗣️ **Conversational Memory** | Remembers the last 8 messages per session — no need to repeat context |

| 📚 **Knowledge Base RAG** | Retrieves from your actual support docs — not hallucinated answers |
| ⚡ **Multi-Level Cache** | Speeds up repeated queries (L1 in-memory → L2 disk → L3 semantic) |
| 🌍 **Arabic + English** | Fully bilingual — auto-detects language and responds accordingly |
| 📊 **Live Admin Stats** | `/stats` endpoint shows routing counts, cache hits, hallucinations blocked |

---


---

## 🚀 Quick Start — Run Locally

### 1. Clone & Install

```bash
git clone https://github.com/YousefKhalil10/simple-customer-support-wiht-fennec
cd fennec-customer-support

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Add Your Knowledge Base

Drop your support documents into `knowledge_base/`:

```
knowledge_base/
├── faq.txt               ← your FAQ
├── returns_policy.txt    ← return/refund policy
├── technical_support.txt ← tech troubleshooting
├── orders.txt            ← order/shipping info
└── products.pdf          ← product catalog (PDFs work too!)
```

Supported formats: `.txt`, `.md`, `.pdf`, `.docx`, `.html`, `.csv`, `.json`

### 4. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** — the chat UI loads automatically.

---

## 🐳 Docker Deployment

### Build & Run

```bash
# Build
docker build -t fennec-support .

# Run
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key \
  -v $(pwd)/knowledge_base:/app/knowledge_base:ro \
  --name fennec-support \
  fennec-support
```

### Docker Compose (Recommended)

```bash
# Development
cp .env.example .env && nano .env
docker compose up --build

# Production (with Nginx)
docker compose --profile production up --build -d
```

---

## ☁️ Cloud Deployment

### Option A — Railway (Easiest, ~2 minutes)

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add environment variable: `OPENAI_API_KEY`
4. Done! Railway auto-detects `railway.json` and deploys

### Option B — Render

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service → Connect GitHub
3. Render auto-reads `render.yaml`
4. Add `OPENAI_API_KEY` in the Environment tab
5. Click Deploy

### Option C — Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch
fly launch --name fennec-support

# Set secrets
fly secrets set OPENAI_API_KEY=sk-your-key

# Deploy
fly deploy
```

### Option D — VPS (Ubuntu) with systemd

```bash
# Install dependencies
sudo apt update && sudo apt install python3.11 python3.11-venv nginx -y

# Clone and setup
git clone https://github.com/your-org/fennec-customer-support /opt/fennec-support
cd /opt/fennec-support
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/fennec-support.service > /dev/null <<EOF
[Unit]
Description=Fennec Customer Support
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/fennec-support
EnvironmentFile=/opt/fennec-support/.env
ExecStart=/opt/fennec-support/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable fennec-support
sudo systemctl start fennec-support
```

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Chat UI (HTML) |
| `GET`  | `/health` | System health check |
| `POST` | `/session/new` | Start new session |
| `POST` | `/chat` | Send message, get response |
| `DELETE` | `/session/{id}` | End session |
| `GET`  | `/stats` | Admin stats |
| `POST` | `/knowledge-base/reload` | Hot-reload KB |

### Chat Example

```bash
# 1. Create session
SESSION=$(curl -s -X POST "http://localhost:8000/session/new?user_name=Ahmed" | jq -r .session_id)

# 2. Ask a question
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"message\": \"What is your return policy?\", \"language\": \"auto\"}"
```

### Response Schema

```json
{
  "session_id": "abc-123",
  "message": "Our return policy allows you to return items within 30 days...",
  "route": "returns",
  "confidence": 0.94,
  "sources": ["returns_policy.txt"],
  "suggestions": [
    "How do I start a return?",
    "How long does a refund take?",
    "What items are non-returnable?"
  ],
  "timestamp": "2026-04-05T14:30:00"
}
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | **Required** | Your OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model for generation |
| `EMBED_MODEL` | `text-embedding-3-small` | Embedding model |
| `ANTHROPIC_API_KEY` | — | Optional: use Claude instead |
| `GEMINI_API_KEY` | — | Optional: use Gemini instead |

### Switching to Claude / Gemini

Edit `app/rag_engine.py`:

```python
# Use Claude instead of OpenAI
from fennec.llm import AnthropicInterface
self._llm = AnthropicInterface(
    model_name="claude-3-5-haiku-20241022",
    api_key=os.environ["ANTHROPIC_API_KEY"],
)

# Use Gemini instead of OpenAI
from fennec.llm import GeminiInterface
self._llm = GeminiInterface(
    model_name="gemini-2.0-flash-exp",
    api_key=os.environ["GEMINI_API_KEY"],
)
```

---

## 📁 Project Structure

```
customer-support/
├── app/
│   ├── main.py              # FastAPI app + all routes
│   ├── rag_engine.py        # Core Fennec RAG orchestration
│   ├── semantic_router.py   # 6-route query classifier
│   └── models.py            # Pydantic request/response models
├── knowledge_base/          # 📚 Your support documents go here
│   ├── faq.txt
│   ├── returns_policy.txt
│   ├── technical_support.txt
│   └── orders.txt
├── frontend/
│   └── index.html           # Beautiful dark chat UI
├── .github/workflows/
│   └── deploy.yml           # CI/CD pipeline
├── Dockerfile               # Production container
├── docker-compose.yml       # Local development + production
├── nginx.conf               # Reverse proxy config
├── railway.json             # Railway deployment config
├── render.yaml              # Render deployment config
├── Procfile                 # Heroku/Railway process file
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧪 Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## 📈 Scaling Tips

- **More RAM**: Sentence Transformers for the semantic router needs ~500MB. Use a 1GB+ instance.
- **Faster embeddings**: Switch to `text-embedding-3-large` for better quality, or use a local model.
- **Bigger knowledge base**: ChromaDB (persistent) instead of FAISS for large document sets:
  ```python
  from fennec.vector_database import ChromaVectorDatabase
  self._vector_db = ChromaVectorDatabase(persist_directory="./chroma_db", ...)
  ```
- **Multiple workers**: Increase `--workers` in CMD for higher concurrency (each worker loads the model).

---

## 📄 License

MIT License — built with [Fennec RAG](https://fennec-community.vercel.app/) 🦊
