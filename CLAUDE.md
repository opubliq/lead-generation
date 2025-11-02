# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a lead generation monitoring service for Opubliq (https://opubliq.com/), a public affairs and communications firm. The system monitors multiple data sources to identify potential clients who may need public affairs, lobbying, communications, or government relations services.

### Target Organization Profile
Opubliq's clients typically include:
- Organizations engaging with government (lobbying activities)
- Companies appearing before parliamentary committees
- Organizations recruiting for communications/public affairs roles
- Entities receiving significant government funding
- Organizations active on key policy issues

### Data Sources & Collection Frequency

1. **Registre québécois des lobbyistes - Recherche de mandats**
   - URL: https://www.carrefourlobby.quebec/recherche-mandats
   - Monitors new lobbying mandates registered in Quebec
   - Identifies organizations and lobbyists starting new government relations activities
   - Key data: client organizations, lobbying firms, subject matters, public office holders targeted

2. **Calendrier des travaux de l'Assemblée nationale**
   - URL: https://www.assnat.qc.ca/fr/travaux-parlementaires/calendrier-travaux.html
   - Tracks parliamentary work calendar and committee schedules
   - Identifies organizations presenting/testifying before committees
   - Key data: witnesses, organizations, committee topics, hearing dates

3. **Google News RSS - Veille de saillance**
   - URL: Google News RSS API with custom search queries
   - Example: `https://news.google.com/rss/search?q=(association+OR+fédération+OR+coalition)+(dénonce+OR+réagit+OR+demande)+Québec+when:7d&hl=fr-CA&gl=CA&ceid=CA:fr`
   - Monitors media coverage for organizations on salient policy issues
   - Tracks associations, federations, coalitions making public statements
   - Query parameters:
     - Search operators: association OR fédération OR coalition (organization types)
     - Action verbs: dénonce OR réagit OR demande (signals of public engagement)
     - Location: Québec (geographic filter)
     - Timeframe: when:7d (last 7 days)
     - Language/Region: hl=fr-CA, gl=CA, ceid=CA:fr (French Canadian)
   - Key data: organization names, policy issues, public positions, media mentions

## Architecture

The system follows a data pipeline architecture:

```
Data Sources → Extractors → Storage → LLM Analysis → Lead Qualification → Output
```

### Key Components

- **Extractors**: Source-specific scrapers/API clients for each data source
- **Storage**: Database for raw data and processed leads
- **LLM Analysis**: Local LLM (Ollama or similar) for analyzing extracted data and qualifying leads
- **Lead Qualification**: Scoring/ranking system to prioritize potential clients

### LLM Integration

The project uses local LLM inference (Ollama or similar) to:
- Extract relevant entities and organizations from unstructured data
- Assess lead quality based on organization characteristics
- Identify signals indicating need for Opubliq's services
- Generate lead summaries and recommendations

## Development Context

### Language & Technology Stack
The project will likely use:
- Python for data extraction and orchestration
- Ollama or similar for local LLM inference
- Database (SQLite/PostgreSQL) for data storage
- Scheduling system for periodic data collection

### Key Development Considerations

1. **Data Source Reliability**: Each source has different update frequencies and access methods (APIs, web scraping, RSS feeds)
2. **Ethical Scraping**: Respect rate limits and robots.txt when scraping public data
3. **Data Privacy**: Handle organization information responsibly
4. **LLM Prompt Engineering**: Prompts must be tuned to identify genuine leads vs. noise
5. **Deduplication**: Same organization may appear across multiple sources

## Quebec/French Context

- Primary operating region: Quebec, Canada
- Content will be primarily in French
- LLM must handle French language effectively
- Government data sources are Quebec-specific (Assemblée nationale, registre des lobbyistes du Québec)
