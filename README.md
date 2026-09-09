# README.md
# Entry point for anyone opening the repo for the first time.

# AI Developer Workspace

A Repository Intelligence Platform. A non-AI **Repository Intelligence
Engine** parses an uploaded repo into a graph model; five deterministic
modules (Health Index, Similarity, Pattern Detector, Dead Code Detection,
Impact Analyzer) compute results from that graph; an optional AI layer
explains the results in natural language.

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Everything via Nginx: http://localhost

## Project layout

- `backend/app/engine/` — Repository Intelligence Engine (parsing + graph model, non-AI)
- `backend/app/modules/` — the 5 deterministic modules (Health Index, Similarity,
  Pattern Detector, Dead Code Detection, Impact Analyzer)
- `backend/app/ai_layer/` — optional RAG/LLM explanation layer
- `backend/app/api/` — FastAPI routes tying it all together
- `backend/app/workers/` — Celery background tasks for slow repo analysis
- `frontend/` — React/TypeScript dashboard
- `nginx/` — reverse proxy config

## Team split suggestion

1. Engine + DB (`engine/`, `db/`)
2. The 5 deterministic modules (`modules/`)
3. Optional AI layer + frontend (`ai_layer/`, `frontend/`)


## Project Structure
```
ai-developer-workspace/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db/
│       │   ├── database.py
│       │   └── models.py
│       ├── engine/                  # Repository Intelligence Engine (non-AI)
│       │   ├── parser.py
│       │   ├── graph_builder.py
│       │   └── graph_models.py
│       ├── modules/                 # 5 deterministic modules
│       │   ├── health_index.py
│       │   ├── pattern_detector.py
│       │   ├── dead_code.py
│       │   ├── impact_analyzer.py
│       │   └── similarity.py
│       ├── ai_layer/                # optional RAG/LLM explanation layer
│       │   ├── embeddings.py
│       │   ├── vector_store.py
│       │   └── rag_chat.py
│       ├── api/
│       │   └── routes.py
│       └── workers/
│           └── tasks.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts
│       └── pages/Dashboard.tsx
└── nginx/
    └── nginx.conf

```