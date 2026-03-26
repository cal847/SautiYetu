# Civic Intelligence System
### Kenyan Parliamentary Bills — Public Transparency Platform

A backend system that automatically collects, parses, and analyses Kenyan parliamentary bills using AI, then notifies citizens via SMS when legislation affects them.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Project Structure](#project-structure)
- [Services](#services)
- [API Reference](#api-reference)
- [Notification Rules](#notification-rules)
- [Data Models](#data-models)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [GitHub Issues & Epics](#github-issues--epics)

---

## Overview

The Civic Intelligence System bridges the gap between parliamentary activity and public awareness. It runs a fully automated pipeline:

1. **Scrapes** bills from the Parliament of Kenya on a schedule
2. **Parses** PDF and HTML documents into structured JSON
3. **Analyses** each bill with AI — generating plain-English summaries, economic impact assessments, sector tags, and risk flags
4. **Stores** raw documents, parsed content, and AI insights in a relational database
5. **Notifies** citizens via SMS when a bill is passed or requires public participation

---

## Architecture

```mermaid
graph TD
    subgraph Pipeline["Ingestion Pipeline"]
        A[Scraper Service\nAPScheduler · 6 hrs] -->|ScrapedBill| B[Parser Service\nPDF + HTML]
        B -->|ParsedBill| C[(Database\nPostgreSQL)]
        C -->|ParsedBill| D[AI Service\nDeepInfra API]
        D -->|AIInsight| C
    end

    C -->|bills + insights| E[REST API\nFastAPI]
    C -->|trigger events| F[Notification Service]

    E -->|JSON| G[Frontend /\nAPI Consumers]
    F -->|SMS| H[Africa's Talking API]

    style Pipeline fill:#f8f9fa,stroke:#dee2e6
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Scraper Service** | Fetches bill listings and documents from parliament.go.ke on a 6-hour schedule |
| **Parser Service** | Converts PDF and HTML bill documents into structured `ParsedBill` JSON |
| **AI Service** | Sends parsed bill text to DeepInfra API; returns summary, impact analysis, and risk flags |
| **Database (ORM)** | Persists raw documents, parsed content, AI insights, and notification logs via SQLAlchemy |
| **API Service** | Exposes a REST API (FastAPI) for frontend consumption with filtering and pagination |
| **Notification Service** | Sends SMS alerts via Africa's Talking when trigger conditions are met |

---

## Data Flow

```mermaid
flowchart TD
    A([Parliament Website]) --> B[Scraper]
    B --> C{Duplicate?}
    C -->|unchanged| D([Skip])
    C -->|new / updated| E[Parser]
    E -->|PDF| F[PDF Parser]
    E -->|HTML| G[HTML Parser]
    F & G -->|ParsedBill| H[(bills + bill_content)]
    H --> I[AI Service\nDeepInfra API]
    I -->|AIInsight| J[(ai_insights)]
    J --> K{Trigger\ncondition?}
    K -->|bill passed\nor public participation| L{Already\nnotified?}
    K -->|no trigger| M([Done])
    L -->|yes| N([Skip · log])
    L -->|no| O[Africa's Talking SMS]
    O --> P[(notification_log)]
```

### Error Handling at Each Stage

| Stage | Behaviour on Failure |
|-------|---------------------|
| Scraper | Retry 3× with exponential backoff, log and skip |
| Parser | Retry 3×, raise `ParserError`, log for manual review |
| AI Service | Retry 2×, fill missing fields with defaults, log |
| SMS | Skip if duplicate, log `SMSDeliveryError`, do not retry |

---

## Project Structure

```
.
├── app/
│   ├── main.py                        # FastAPI app entrypoint
│   ├── config.py                      # Pydantic BaseSettings (env vars)
│   ├── logger.py                      # Structured JSON logging
│   ├── dependencies.py                # FastAPI dependency injection
│   │
│   ├── scraper/
│   │   ├── scraper.py                 # HTTP scraper — parliament.go.ke
│   │   ├── scheduler.py               # APScheduler cron (every 6 hrs)
│   │   ├── deduplication.py           # CREATED | UPDATED | SKIPPED logic
│   │   ├── models.py                  # ScrapedBill Pydantic model
│   │   └── parsers/
│   │       └── html_parser.py         # Listing page HTML parser
│   │
│   ├── parser/
│   │   ├── pdf_parser.py              # pdfplumber-based PDF extraction
│   │   ├── html_parser.py             # BeautifulSoup HTML extraction
│   │   ├── section_extractor.py       # Clause/section segmentation
│   │   └── models.py                  # ParsedBill Pydantic model
│   │
│   ├── ai/
│   │   ├── client.py                  # DeepInfra API client wrapper
│   │   ├── analysis_service.py        # analyze_bill() orchestration
│   │   ├── prompts/
│   │   │   └── bill_analysis.py       # Versioned prompt templates
│   │   └── schemas/
│   │       └── insight_schema.py      # AIInsight Pydantic model
│   │
│   ├── db/
│   │   ├── base.py                    # SQLAlchemy declarative base
│   │   ├── session.py                 # Async session + DI factory
│   │   ├── models/
│   │   │   ├── bill.py                # Bill ORM model
│   │   │   ├── bill_content.py        # BillContent ORM model
│   │   │   ├── ai_insight.py          # AIInsight ORM model
│   │   │   └── notification_log.py    # NotificationLog ORM model
│   │   └── repositories/
│   │       ├── bill_repository.py     # Bill CRUD + upsert
│   │       ├── insight_repository.py  # AIInsight CRUD
│   │       └── notification_repository.py  # NotificationLog CRUD
│   │
│   ├── api/
│   │   ├── router.py                  # Route registration
│   │   ├── routes/
│   │   │   ├── bills.py               # GET /bills, GET /bills/{id}
│   │   │   └── alerts.py              # GET /alerts
│   │   └── schemas/
│   │       ├── bill_schema.py         # Bill request/response schemas
│   │       └── alert_schema.py        # Alert response schema
│   │
│   ├── notifications/
│   │   ├── sms_client.py              # Africa's Talking SDK wrapper
│   │   ├── notification_service.py    # Trigger logic + dedup
│   │   └── templates.py              # SMS message templates
│   │
│   ├── pipeline/
│   │   └── ingestion_pipeline.py      # End-to-end orchestration
│   │
│   ├── middleware/
│   │   └── logging_middleware.py      # Request/response logging
│   │
│   └── utils/
│       └── retry.py                   # @retry decorator (exponential backoff)
│
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py      # Initial DB migration
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── BillsPage.jsx          # Paginated bill listing
│       │   └── BillDetailPage.jsx     # Full bill + AI insights
│       ├── components/
│       │   ├── BillCard.jsx           # Bill summary card
│       │   └── ImpactBadge.jsx        # Sector/impact tag badge
│       └── api/
│           └── billsApi.js            # API client functions
│
├── tests/
│   ├── scraper/
│   │   └── test_deduplication.py
│   ├── parser/
│   │   ├── test_pdf_parser.py
│   │   └── test_html_parser.py
│   ├── ai/
│   │   ├── test_analysis_service.py
│   │   └── test_insight_schema.py
│   ├── api/
│   │   ├── test_bills.py
│   │   └── test_alerts.py
│   └── notifications/
│       └── test_deduplication.py
│
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## Services

### Scraper Service

Runs on a configurable schedule (default: every 6 hours) using APScheduler integrated into the FastAPI lifespan. On each run it:

- Fetches paginated bill listings from parliament.go.ke
- Computes a content hash for each bill
- Compares against existing records — returns `CREATED`, `UPDATED`, or `SKIPPED`
- Hands new/updated bills to the ingestion pipeline

A manual trigger is available at `POST /admin/scrape` for development and debugging.

### Parser Service

Accepts a bill document (PDF bytes or HTML string) and returns a `ParsedBill` object with a normalised structure regardless of source format:

```python
class ParsedBill(BaseModel):
    bill_id: str
    title: str
    raw_text: str
    sections: list[BillSection]
```

Both parsers implement the same interface so the pipeline does not need to know which format it received.

### AI Service

Sends the parsed bill text to the DeepInfra API using versioned prompt templates. Returns a validated `AIInsight` object:

```python
class AIInsight(BaseModel):
    bill_id: str
    summary: str                   # Plain-English summary
    economic_impact: str           # Economic impact narrative
    sector_impact: list[str]       # Affected sectors (e.g. ["finance", "health"])
    risk_flags: list[str]          # Notable risks or concerns
    public_participation: bool     # Whether public input is required
```

Partial AI responses are filled with typed defaults. Fully invalid responses trigger one retry before being logged and skipped.

### Notification Service

Evaluates trigger conditions after each pipeline run and sends SMS via Africa's Talking. Deduplication is enforced at the database level — a successful send for a given `bill_id + event_type` combination is never repeated.

---

## API Reference

### `GET /bills`

Returns a paginated list of bills.

**Query parameters**

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `limit` | int | Results per page (default: 20) |
| `status` | enum | Filter by status: `introduced`, `passed`, `rejected` |
| `category` | enum | Filter by category: `finance`, `health`, `education`, etc. |

---

### `GET /bills/{id}`

Returns full bill details including parsed sections and AI insights.

**Response includes:** title, status, dates, source URL, parsed sections, summary, economic impact, sector tags, risk flags, public participation flag.

---

### `GET /alerts`

Returns a feed of recent SMS notification events.

**Query parameters**

| Param | Type | Description |
|-------|------|-------------|
| `limit` | int | Number of alerts to return (default: 20) |

---

### `GET /health`

Returns `200 OK`. Used for uptime monitoring and deployment health checks.

---

## Notification Rules

| Event | Send SMS |
|-------|----------|
| New bill introduced | No |
| Bill passed | Yes |
| Public participation required | Yes |
| Minor bill update | No |

### SMS Template

```
New Bill Passed: {bill_title}
Summary: {ai_summary}
Impact: {economic_impact}
Take Action: Public participation open.
Read more: {bill_url}
```

---

## Data Models

```mermaid
erDiagram
    bills {
        string id PK
        string title
        string status
        date date_introduced
        date date_passed
        string source_url
    }
    bill_content {
        string bill_id FK
        text raw_text
        json parsed_sections
    }
    ai_insights {
        string bill_id FK
        text summary
        text economic_impact
        json sector_impact
        json risk_flags
        boolean public_participation
    }
    notification_log {
        string bill_id FK
        string type
        string event_type
        timestamp sent_at
        string status
    }

    bills ||--o| bill_content : "has"
    bills ||--o| ai_insights : "has"
    bills ||--o{ notification_log : "triggers"
```


| Column | Type | Notes |
|--------|------|-------|
| `id` | string (PK) | Bill ID from parliament |
| `title` | string | Full bill title |
| `status` | string | Current legislative status |
| `date_introduced` | date | |
| `date_passed` | date | Nullable |
| `source_url` | string (unique) | Source document URL |

### bill_content

| Column | Type | Notes |
|--------|------|-------|
| `bill_id` | string (FK) | References bills.id |
| `raw_text` | text | Full extracted text |
| `parsed_sections` | json | Structured section breakdown |

### ai_insights

| Column | Type | Notes |
|--------|------|-------|
| `bill_id` | string (FK) | References bills.id |
| `summary` | text | Plain-English summary |
| `economic_impact` | text | Economic impact narrative |
| `sector_impact` | json | List of affected sectors |
| `risk_flags` | json | List of identified risks |
| `public_participation` | boolean | Participation required flag |

### notification_log

| Column | Type | Notes |
|--------|------|-------|
| `bill_id` | string (FK) | References bills.id |
| `type` | string | Always `SMS` for now |
| `event_type` | string | `bill_passed` or `public_participation` |
| `sent_at` | timestamp | |
| `status` | string | `success` or `failed` |

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (frontend)
- Africa's Talking account (SMS)
- DeepInfra API key (AI analysis)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/civic-intelligence.git
cd civic-intelligence

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/civic_intelligence

# DeepInfra (AI analysis)
DEEPINFRA_API_KEY=your_key_here
DEEPINFRA_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct  # or any supported model

# Africa's Talking (SMS)
AT_USERNAME=your_username
AT_API_KEY=your_key_here
AT_SANDBOX=true               # Set to false in production

# Scraper
SCRAPER_INTERVAL_HOURS=6      # How often to scrape

# App
LOG_LEVEL=INFO                # DEBUG | INFO | WARNING | ERROR
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run a specific service
pytest tests/scraper/
pytest tests/ai/
pytest tests/api/

# With coverage
pytest --cov=app --cov-report=term-missing
```

---

## GitHub Issues & Epics

The project is broken into 7 epics and 21 independent issues. Each issue owns distinct files to enable conflict-free parallel development.

| Epic | Issues | Focus |
|------|--------|-------|
| Epic 1 — Scraper | #1 #2 #3 #4 | Project setup, scraping, scheduling, deduplication |
| Epic 2 — Parser | #5 #6 | PDF and HTML bill parsing |
| Epic 3 — AI Processing | #12 #13 #14 #15 | Prompts, DeepInfra API integration, pipeline wiring |
| Epic 4 — Database | #7 #8 | Schema, migrations, repository layer |
| Epic 5 — API | #9 #10 #11 #21 | REST endpoints, filtering, frontend UI |
| Epic 6 — Notifications | #16 #17 #18 | Africa's Talking, SMS triggers, deduplication |
| Epic 7 — Observability | #19 #20 | Logging, error tracking, retry mechanisms |

> See `github_issues.md` for full issue descriptions, file ownership, and acceptance criteria.

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Scraper latency | New bills processed within 10 minutes of publication |
| API response time | < 500ms at p95 |
| SMS deduplication | No citizen receives the same alert twice |
| Retry policy | 3 attempts for scraper/parser, 2 for AI |
| Idempotency | All pipeline operations are safe to re-run |

---

## License

MIT