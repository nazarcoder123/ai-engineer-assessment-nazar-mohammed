# AI Engineer Chatbot: Dual-Source Intelligence

A production-oriented FastAPI chatbot that answers natural-language questions by intelligently routing queries across two knowledge sources:
1. **Curated Text Dataset**: Ancient Mythology & Legends (Norse, Greek, Egyptian, Mesopotamian).
2. **Superhero API**: Live comic book database (powerstats, alter-egos, biographies, and affiliations).
3. **Both Sources**: Cross-domain synthesis when queries compare or overlap both worlds (e.g., Marvel's Thor vs Norse Thor, or Superman vs Hercules).

Every response provides explicit source citations, latency metrics, and is synthesized using a real hosted LLM endpoint.

---

## Architecture Flow

```text
Client
  │
  ▼
POST /ask (or Web UI)
  │
  ▼
Request Validation (Pydantic)
  │
  ▼
Question Router (LLM-guided + Heuristic Fallback)
  │
  ├───► Route: "superhero" ───► Superhero API Client (/api/{token}/search/{name})
  ├───► Route: "dataset"   ───► BM25 Text Dataset Retriever (data/mythology_and_legends)
  └───► Route: "both"      ───► Queries Both Sources in Parallel
  │
  ▼
Context Builder (Evidence aggregation & Source attribution)
  │
  ▼
Hosted LLM (Groq or Google Gemini via REST)
  │
  ▼
Response (Answer + Explicit Sources + Route + Latency)
```

---

## Quick Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Free API keys (see `.env.example`):
  - **Superhero API Token**: Free from [superheroapi.com](https://superheroapi.com) (Sign in with GitHub).
  - **Hosted LLM Key**: Free from [Groq](https://console.groq.com) or [Google Gemini AI Studio](https://aistudio.google.com).

### 2. Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd <repo-folder>

# Create and activate virtual environment
python -m venv .venv

# Windows:
.\.venv\Scripts\activate

# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Secrets
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
SUPERHERO_API_TOKEN=your_superhero_api_token
GROQ_API_KEY=your_groq_api_key
# Or use Gemini:
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your_gemini_api_key
```

---

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running:
- **Interactive Web UI**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## API Usage

### `POST /ask`

#### Request:
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Compare Superman to Hercules in terms of physical strength."}'
```

#### Response:
```json
{
  "answer": "According to the Superhero API, Superman has a Strength powerstat of 100... Based on the Mythology Dataset (hercules_greek_mythology.txt), Hercules achieved legendary physical feats during his Twelve Labours...",
  "sources": [
    "Superhero API (Superman)",
    "Text Dataset (hercules_greek_mythology.txt)"
  ],
  "route": "both",
  "retrieved_superheroes": ["Superman"],
  "retrieved_documents": ["hercules_greek_mythology.txt"],
  "latency_ms": 310.45,
  "llm_provider": "Groq (llama-3.3-70b-versatile)"
}
```

---

## Running Tests

Run the full automated test suite (26 unit and integration tests with mocks):
```bash
pytest -v
```
