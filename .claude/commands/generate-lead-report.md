# Generate Lead Report

Generate a formatted markdown report from qualified lead data for a specific date.

## Instructions

You are being asked to generate a lead report. Follow these steps:

1. Ask the user which date they want the report for (format: YYYY-MM-DD). If they don't specify, use today's date (2025-11-04).

2. Use the Task tool to launch the lead-report-generator agent with the following prompt that MUST include the date as "TODAY":
   ```
   TODAY'S DATE: [DATE]

   Generate a markdown lead report for the date [DATE].

   Look for the qualified leads JSON file at: data/marts/[DATE]/google_news_leads.json
   Look for the summaries file at: data/warehouse/google_news_summaries_[DATE].json

   IMPORTANT: The date [DATE] represents TODAY. When suggesting actions and contact timing:
   - All deadlines must be in the FUTURE relative to [DATE]
   - Never suggest past dates for contacts or actions
   - If source data mentions past events, re-contextualize to current situation

   Create a structured markdown report following the standard template with:
   - Report header with date
   - News summary section (1 page max, bullet points)
   - Top 10 qualified leads (re-scored and ranked)
   - Detailed organization profiles (6-8 lines each)
   - Metadata footer

   Save the report as: data/marts/[DATE]/rapport_leads.md
   Generate PDF as: data/marts/[DATE]/rapport_leads.pdf
   ```

3. Once the agent completes, show the user the paths to the generated markdown and PDF reports.

## Notes

- The lead-report-generator agent has access to all necessary tools
- It will read the qualified leads JSON and format it into markdown
- The report follows Opubliq's standard format for client prospecting
