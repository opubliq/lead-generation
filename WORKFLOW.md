# Lead Generation Workflow

## Data Collection

Three scrapers run weekly to collect data:

1. **Google News RSS** (`scrapers/google_news_rss.py`)
   - Monitors Quebec media for organizations making public statements
   - Query: associations/federations/coalitions + action verbs (dénonce/réagit/demande)
   - Output: RSS feed entries with organization mentions

2. **Assemblée nationale Calendar** (TBD)
   - Tracks parliamentary committee witnesses
   - Output: Organizations presenting before committees

3. **Carrefour Lobby** (TBD)
   - Monitors new lobbying mandates in Quebec
   - Output: Client organizations, lobbying firms, mandate details

## Analysis Process

Manual analysis via Claude Code with access to scraped data files.

### Stage 1: Individual Contextualization

For each organization identified in scraped data:
- Extract key attributes (name, sector, public positions, activity type)
- Assess signals indicating need for public affairs services
- Generate enriched JSON with standardized fields

**Input**: Raw scraped data
**Output**: Structured JSON per organization

### Stage 2: Strategic Analysis

Aggregate analysis across all contextualized organizations:
- Score/rank by fit with Opubliq's services
- Identify top 10-15 priority leads
- Synthesize rationale for each lead

**Input**: Enriched JSON from Stage 1
**Output**: Markdown report

## Output Format

Simple markdown report containing:
- Top 10-15 qualified leads
- Organization name and context
- Why they may need Opubliq's services
- Data source(s) that surfaced the lead

## Frequency

Weekly collection and analysis cycle.

## Infrastructure

- Scrapers: Python scripts (manual execution)
- Data storage: Local files (JSON/CSV)
- Analysis: Claude Code with LLM reasoning
- No databases, automation, or scheduled jobs
