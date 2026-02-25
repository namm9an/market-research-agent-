# 🧠 Market Research AI Agent

> **AI-powered market research agent** that generates comprehensive company reports in under 60 seconds — powered by NVIDIA Nemotron Nano on E2E Networks GPU infrastructure.

<p align="center">
  <img src="https://img.shields.io/badge/NVIDIA-Nemotron_Nano_30B-76B900?style=for-the-badge&logo=nvidia&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Tavily-AI_Search-5A67D8?style=for-the-badge" />
  <img src="https://img.shields.io/badge/E2E_Networks-A100_80GB-FF6B35?style=for-the-badge" />
</p>

---

## ✨ What It Does

Type a company name → get a professional market research report with:

- 📊 **Company Overview** — products, services, market position
- 🎯 **SWOT Analysis** — strengths, weaknesses, opportunities, threats
- 📈 **Market Trends** — 5-7 current industry trends with relevance ratings
- 🏆 **Competitive Landscape** — competitor analysis and positioning
- 💡 **Key Findings** — 10+ actionable insights
- 🔗 **40+ Sources** — all findings backed by real web sources
- 🔎 **4-Tab Command Center** — Instant Web Searches, Web Crawling, Structured Extraction, and Deep Research pipelines.

**All running on your own GPU infrastructure. No OpenAI. No data leaving your cloud.**

---

## 🏗️ Architecture

```
Your Laptop (Docker)                    E2E GPU Instance
┌──────────────────────────┐           ┌───────────────────────┐
│                          │           │                       │
│  Frontend ──► Backend ───── SSH ────►│  vLLM Server          │
│  (Next.js)    (FastAPI)  │  Tunnel   │  Nemotron Nano 30B    │
│  :3000        :8080      │           │  :8000                │
│               │          │           │                       │
│               ▼          │           │  NVIDIA A100 80GB     │
│          Tavily API      │           └───────────────────────┘
│          (web search)    │
│               │          │
│               ▼          │
│          JSON Files      │
│     (cache + reports)    │
└──────────────────────────┘
```

### How It Works

1. **Search Agent** — Runs 4 strategic Tavily queries (overview, news, financial, competitors)
2. **Analyst Agent** — LLM generates SWOT analysis + market trends from search data
3. **Report Agent** — LLM compiles everything into a professional structured report

The pipeline runs in ~36 seconds, caches search results, and saves reports as JSON.

---

## 🛠️ Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **AI Model** | [NVIDIA Nemotron Nano 30B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16) | 30B params, 3.5B active (MoE). Fast + smart. 1M token context. |
| **Model Serving** | vLLM | OpenAI-compatible API. High throughput. |
| **GPU** | NVIDIA A100 80GB (E2E Networks) | BF16 precision. Self-hosted in India. |
| **Backend** | FastAPI + Python 3.12 | Async, fast, auto-docs. |
| **Web Search** | Tavily API | AI-native search. Returns cleaned, LLM-ready content. |
| **Frontend** | Next.js + Tailwind CSS | Dark theme. Professional dashboard. |
| **Deployment** | Docker + SSH tunnel | Backend/frontend local, model on GPU cloud. |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker + docker-compose
- E2E Networks GPU instance with vLLM running

### 1. Clone & Setup

```bash
git clone https://github.com/namm9an/market-research-agent-.git
cd market-research-agent-
cp .env.example .env
# Edit .env with your Tavily API key
```

### 2. Start the SSH Tunnel (GPU connection)

```bash
ssh -L 8000:localhost:8000 root@<your-e2e-instance-ip>
```

### 3. Start the Backend

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 4. Test It

```bash
# Health check
curl http://localhost:8080/api/health | python3 -m json.tool

# Start research
curl -X POST http://localhost:8080/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Zomato", "type": "company"}'

# Get results (replace YOUR_JOB_ID)
curl http://localhost:8080/api/research/YOUR_JOB_ID | python3 -m json.tool

# Export as markdown
curl "http://localhost:8080/api/research/YOUR_JOB_ID/export?format=md"
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check — vLLM + Tavily status |
| `POST` | `/api/research` | Start heavy 35-sec deep research job |
| `POST` | `/api/search` | Lightweight raw generic web search (Bypasses LLM) |
| `POST` | `/api/extract` | Target URLs to extract firmographics (Funding, ICP, Portfolio) |
| `POST` | `/api/crawl` | Target domains to extract full structured company profiles |
| `GET` | `/api/research/{job_id}` | Get job status + results |
| `GET` | `/api/research/{job_id}/export` | Export report (markdown/PDF/JSON) |
| `GET` | `/api/jobs` | List all research jobs |

### Example Response

```json
{
  "status": "completed",
  "duration_seconds": 36.5,
  "report": {
    "company_overview": "Zomato Ltd. is a leading Indian food-delivery...",
    "swot": {
      "strengths": ["58% market share...", "..."],
      "weaknesses": ["...", "..."],
      "opportunities": ["...", "..."],
      "threats": ["...", "..."]
    },
    "trends": [{"title": "...", "relevance": "high"}],
    "key_findings": ["10+ actionable insights"],
    "sources": ["40+ verified web sources"]
  }
}
```

---

## 📁 Project Structure

```
market-research-agent/
├── app/
│   ├── main.py                    # FastAPI entry point + API endpoints
│   ├── config.py                  # Environment variables & settings
│   ├── models/
│   │   └── schemas.py             # Pydantic models (SWOT, Report, etc.)
│   ├── services/
│   │   ├── llm_service.py         # vLLM client (OpenAI-compatible)
│   │   ├── search_service.py      # Tavily 4-query search strategy
│   │   └── research_engine.py     # Pipeline: search → analyze → compile
│   └── prompts/
│       └── templates.py           # SWOT, Trends, Report prompt templates
├── data/
│   ├── cache/                     # Cached Tavily search results
│   ├── reports/                   # Generated report JSON files
│   └── fallback/                  # Pre-loaded demo data
├── setup_vllm.sh                  # GPU instance setup script
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔧 GPU Instance Setup

The model runs on an E2E Networks A100 80GB GPU instance:

```bash
# SSH into your E2E instance
ssh root@<instance-ip>

# Run the setup script
bash setup_vllm.sh
```

The script:
1. ✅ Checks GPU availability
2. ✅ Creates an isolated Python virtual environment
3. ✅ Installs vLLM + dependencies
4. ✅ Starts the model server in tmux
5. ✅ Waits for ready + runs a test

**Model**: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` (~64GB VRAM)

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| **Research time** | ~36 seconds |
| **Sources gathered** | 40 per report |
| **SWOT points** | 4 per category |
| **Market trends** | 5-7 per report |
| **Key findings** | 10+ per report |
| **Model VRAM usage** | ~64GB (BF16) |
| **API credits per report** | ~8 Tavily credits |

---

## 🤝 Built With

- **Model**: [NVIDIA Nemotron Nano 30B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16) — open-weight, MoE architecture
- **Infrastructure**: [E2E Networks](https://www.e2enetworks.com/) — Indian GPU cloud (A100 80GB)
- **Search**: [Tavily](https://tavily.com/) — AI-native search API
- **Serving**: [vLLM](https://github.com/vllm-project/vllm) — high-throughput LLM serving
