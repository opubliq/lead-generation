# Run Lead Generation Pipeline

Execute the complete lead generation pipeline with all stages: extraction, LLM analysis, qualification, and reporting.

## Instructions

You are being asked to run the complete lead generation pipeline. Follow these steps carefully:

1. **Ask for confirmation and scope**:
   - Ask the user which data source(s) to process:
     - Google News RSS (most common for weekly monitoring)
     - Registre québécois des lobbyistes
     - Calendrier de l'Assemblée nationale
     - All sources
   - Ask for the date range or use default (last 7 days for Google News)

2. **Verify environment**:
   - Check that required Python dependencies are installed
   - Verify that the LLM service (Ollama or similar) is running
   - Check for configuration files

3. **Execute the pipeline stages**:

   a. **Data Extraction**:
      - Run the appropriate extractor script(s)
      - Monitor progress and handle any errors
      - Verify data was saved to the data directory

   b. **LLM Analysis**:
      - Run the LLM analysis script to process extracted data
      - Generate organization summaries and extract key signals
      - Save analyzed data

   c. **Lead Qualification**:
      - Run the qualification script to score and rank leads
      - Apply Opubliq's qualification criteria
      - Filter for high-quality prospects
      - Save qualified leads JSON

   d. **Report Generation**:
      - Use the Task tool to launch the lead-report-generator agent
      - Generate the markdown report from qualified leads
      - Save report to reports/ directory

4. **Summary and next steps**:
   - Provide a summary of results (number of leads found, top scores, etc.)
   - Show the path to the generated report
   - Suggest any follow-up actions

## Important Notes

- **File modifications**: You have permission to create and modify files during pipeline execution
- **Execution time**: The full pipeline may take several minutes depending on data volume
- **Error handling**: If any stage fails, report the error clearly and suggest fixes
- **Data privacy**: Handle organization data responsibly
- **Rate limiting**: Respect rate limits when accessing external data sources

## Example Usage

User: `/run-pipeline`

Expected flow:
1. Claude asks which sources to monitor
2. User selects "Google News RSS"
3. Claude runs extraction → analysis → qualification → report generation
4. Claude provides summary and report path
