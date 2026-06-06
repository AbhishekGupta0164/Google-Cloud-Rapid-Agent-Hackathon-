# 🛡️ DevSentinel
### Autonomous Production Safety Agent — Google Cloud × MongoDB Hackathon

> **DevSentinel** watches every GitHub pull request in real-time, uses **Atlas Vector Search** to find similar past production incidents, tests queries at 10× scale, and posts an evidence-backed risk brief to the PR — before it merges and breaks production.

---

## 🏗️ System Architecture

```
GitHub PR Opened
      │
      ▼
┌─────────────────┐
│  Agent 1        │  HarvesterAgent — stores PR in Atlas with Voyage AI embeddings
│  Harvester      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │  (parallel)
    ▼         ▼
┌───────┐ ┌──────────┐
│ Agent │ │ Agent 3  │
│   2   │ │  Scale   │  AnalystAgent — Atlas Vector Search for similar incidents
│Analyst│ │  Tester  │  ScaleTester  — 10× query performance simulation
└───┬───┘ └────┬─────┘
    └────┬─────┘
         │
         ▼
┌─────────────────┐
│  Agent 4        │  RiskNarratorAgent — Gemini 2.5 Flash synthesises risk brief
│  Risk Narrator  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent 5        │  ActionAgent — posts GitHub comment + audit log
│  Action Agent   │
└─────────────────┘
```

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/devsentiinel.git
cd devsentiinel
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your keys:
#   MONGODB_URI=mongodb+srv://...
#   GEMINI_API_KEY=...
#   VOYAGE_API_KEY=...
#   GITHUB_TOKEN=...
#   GITHUB_WEBHOOK_SECRET=...
```

### 3. Seed Past Incidents (Atlas Vector Search memory)

```bash
python migrations/seed_incidents.py
```

> ⚠️ **Before seeding:** Create the Atlas Vector Search index on the `embedding` field (1024 dims, cosine similarity) on both `past_incidents` and `query_patterns` collections.

### 4. Run the API

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 5. Run the Dashboard

```bash
streamlit run dashboard/app.py --server.port 8501
```

---

## 📁 Project Structure

```
devsentiinel/
├── main.py                     # FastAPI app — webhook + pipeline orchestration
├── query_watcher.py            # Atlas Change Stream watcher
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── agents/
│   ├── harvester.py            # Agent 1 — PR ingestion + Voyage AI embedding
│   ├── analyst.py              # Agent 2 — Atlas Vector Search + confidence scoring
│   ├── scale_tester.py         # Agent 3 — 10× query performance simulation
│   ├── risk_narrator.py        # Agent 4 — Gemini 2.5 Flash risk brief generation
│   └── action_agent.py         # Agent 5 — GitHub comment + audit log
│
├── config/
│   ├── settings.py             # All env vars + thresholds
│   └── database.py             # Singleton MongoDB connection
│
├── tools/
│   ├── embedding_tool.py       # Voyage AI embedding (async, non-blocking)
│   ├── github_tool.py          # PyGitHub wrapped as ADK FunctionTools
│   └── atlas_tool.py           # MongoDB Atlas ops as ADK FunctionTools
│
├── dashboard/
│   └── app.py                  # Streamlit monitoring dashboard (5 pages)
│
├── migrations/
│   └── seed_incidents.py       # Seeds 6 realistic past incidents
│
├── tests/
│   └── test_pipeline.py        # pytest test suite (30+ tests)
│
└── .github/
    └── workflows/
        └── deploy.yml          # CI/CD — test + deploy to Cloud Run
```

---

## 🔧 MongoDB MCP Tools Used

| # | Tool | Agent | Purpose |
|---|------|-------|---------|
| 1 | `collection-schema` | Harvester | Auto-discovers collection field structure |
| 2 | `find` | Analyst | Retrieves full incident documents after Vector Search |
| 3 | `aggregate` | Analyst + ScaleTester | Confidence scoring + 10× load simulation |
| 4 | **Atlas Vector Search** | Analyst | Semantic incident matching (1024-dim Voyage AI) |
| 5 | `insert-many` + Voyage AI autoEmbed | Harvester | Stores PRs with auto-generated embeddings |
| 6 | `update-one` | ActionAgent | Updates PR status after action taken |
| 7 | `collection-indexes` | Analyst | Checks for active indexes on renamed fields |
| 8 | `atlas-get-performance-advisor` | ScaleTester | Real Atlas index recommendations |
| 9 | `atlas-search-index-create` | ActionAgent | Creates recommended compound index |
| 10 | `confirmationRequiredTool` | ActionAgent | MCP Elicitation before every external action |
| 11 | **Atlas Change Streams** | query_watcher.py | Proactive query pattern monitoring |
| 12 | `atlas-list-clusters` | Dashboard | Cluster health in monitoring UI |
| 13 | `atlas-create-index-suggestion` | ActionAgent | Suggests optimal compound index |

---

## 🌐 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check + DB status |
| `POST` | `/webhook/github` | GitHub PR webhook receiver |
| `POST` | `/trigger/pr` | Manual pipeline trigger (testing) |
| `POST` | `/trigger/query` | Atlas Change Stream query trigger |
| `GET` | `/dashboard/stats` | Dashboard KPI data |
| `GET` | `/dashboard/recent` | Recent PR analyses |
| `GET` | `/dashboard/audit` | Audit log feed |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 🐳 Docker

```bash
docker build -t devsentiinel .
docker run -p 8080:8080 --env-file .env devsentiinel
```

---

## ☁️ Deploy to Cloud Run

```bash
gcloud run deploy devsentiinel \
  --image gcr.io/YOUR_PROJECT/devsentiinel \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --set-secrets "MONGODB_URI=MONGODB_URI:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

---

## 🔑 Required Secrets (Google Cloud Secret Manager)

| Secret Name | Description |
|-------------|-------------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `GEMINI_API_KEY` | Google Gemini API key |
| `VOYAGE_API_KEY` | Voyage AI embedding API key |
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `GITHUB_WEBHOOK_SECRET` | GitHub webhook HMAC secret |

---

## 📊 Atlas Vector Search Index

Create this index on **both** `past_incidents` and `query_patterns` collections:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1024,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "severity"
    }
  ]
}
```

Name them `incident_vector_index` and `query_vector_index` respectively.

---

## 📄 License

MIT License — Built for the Google Cloud × MongoDB Hackathon 2026.
