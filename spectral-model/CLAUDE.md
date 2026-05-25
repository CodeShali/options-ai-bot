# Spectral-IAM Training Data Pipeline

## Purpose
Multi-source training data pipeline for the Spectral-IAM AI model — an expert assistant for Identity and Access Management (IAM). Generates high-quality instruction-output pairs from RFC documents, vendor docs, Stack Overflow Q&A, and synthetic generation.

## Quick Start

```bash
# Setup
cd spectral-model/
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your ANTHROPIC_API_KEY

# Run Week 1 pipeline (all data sources, ~4-8 hours)
python cli.py week1-full

# Individual commands
python cli.py fetch-rfcs RFC4511 RFC6749 RFC7636
python cli.py build-corpus ldap --n 5
python cli.py synthetic-loop oauth 50
python cli.py stackoverflow ldap active-directory oauth-2.0
python cli.py scrape-vendor "Okta" https://developer.okta.com/docs/ okta
python cli.py report
```

## Environment Setup
Copy `.env.example` to `.env` and set:
- `ANTHROPIC_API_KEY` — required for all Claude-based generation
- `TAVILY_API_KEY` — optional, enables web search in synthetic loop
- `STACK_EXCHANGE_API_KEY` — optional, raises Stack Exchange rate limits
- `QUALITY_SCORE_THRESHOLD` — default 0.7, filter sensitivity

## Architecture

```
cli.py                          # Typer CLI entry point
orchestrator/
  pipeline_runner.py            # Wires all pipelines with QF + dedup + storage
  progress.py                   # Rich progress display
  main.py                       # build_week1() / build_full() entry points
pipelines/
  shared/
    claude_client.py            # Async Claude API wrapper with retry
    dedup.py                    # Semantic dedup via sentence-transformers + ChromaDB
    quality_filter.py           # Programmatic quality gates (no LLM)
    rate_limiter.py             # Token bucket rate limiting per domain
    search_client.py            # Tavily search wrapper
  p1_authoritative_docs/        # Pipeline 1: RFCs, NIST SPs
  p2_vendor_docs/               # Pipeline 2: vendor doc crawling
  p3_protocols/                 # Pipeline 3: LDAP/protocol corpus generation
  p4_real_problems/             # Pipeline 4: Stack Overflow Q&A
  p5_synthetic_loop/            # Pipeline 5: Invent→Solve→Critique→Refine
storage/
  db.py                         # aiosqlite async database
  jsonl_writer.py               # JSONL output (per-domain + unified)
  chroma_store.py               # ChromaDB vector store wrapper
config/
  settings.py                   # Pydantic Settings
  sources.yaml                  # Full source catalog (RFCs, vendors, SO tags)
  topics.yaml                   # Domain/subtopic taxonomy
schemas/
  training_pair.py              # Core TrainingPair model
  document.py                   # SourceDocument + DocumentChunk
  problem.py                    # RealWorldProblem
  enums.py                      # Domain, TaskType, SourceType enums
```

## Pipelines

- **P1 Authoritative Docs**: Downloads RFC/NIST PDFs, chunks by section, generates 5 pairs per chunk
- **P2 Vendor Docs**: BFS crawls vendor doc sites, extracts text, generates vendor-specific pairs
- **P3 Protocol Corpus**: LDAP topic taxonomy (7 topics × ~12 subtopics), generates per subtopic
- **P4 Real Problems**: Stack Exchange API → accepted Q&A → Claude-refined training pairs
- **P5 Synthetic Loop**: Invent problem → Solve → Critique (score 1-5) → Refine if needed

## Output Format
JSONL with OpenAI-style messages:
```json
{"id": "...", "domain": "ldap", "task_type": "explain_concept",
 "messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}],
 "citations": [...], "metadata": {...}}
```

## Tests
```bash
pytest tests/ -v
```
Tests are fully offline (no network, no Claude API calls).

## Key Design Decisions
- All imports are absolute from `spectral-model/` as root
- Claude client uses sync Anthropic SDK wrapped in `run_in_executor` for asyncio compatibility
- SemanticDedup lazy-initializes on first use (sentence-transformers is slow to load)
- QualityFilter is purely programmatic — no LLM calls in the filter pipeline
- ChromaDB and SQLite both persist to `data/` directory
