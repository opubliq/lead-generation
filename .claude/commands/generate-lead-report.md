# Generate Lead Report

Generate a formatted markdown report from qualified lead data for a specific date.

## Instructions

You are being asked to generate a lead report. Follow these steps:

1. Ask the user which date they want the report for (format: YYYY-MM-DD). If they don't specify, use today's date (2025-11-03).

2. Use the Task tool to launch the lead-report-generator agent with the following prompt:
   ```
   Generate a markdown lead report for [DATE].

   Look for the qualified leads JSON file in the data output directory.
   The file should be named something like: qualified_leads_google_news_[DATE].json

   Create a structured markdown report with:
   - Report header with date
   - Executive summary
   - Top leads ranked by score
   - Detailed organization profiles
   - Recommended actions

   Save the report as: reports/lead_report_[DATE].md
   ```

3. Once the agent completes, show the user the path to the generated report.

## Notes

- The lead-report-generator agent has access to all necessary tools
- It will read the qualified leads JSON and format it into markdown
- The report follows Opubliq's standard format for client prospecting
