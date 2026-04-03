# CHAT Report Generator

AI-powered report generator for the **Climate Health Vulnerability Assessment Tool (CHAT)** by eHealth Africa (eHA).

Generates detailed PDF reports analyzing climate health vulnerability data across Nigerian states and LGAs using Llama AI via Groq.

## Features

- Filter data by State and LGA
- Three report depth levels: Comprehensive, Moderate, Short
- AI-generated report sections: Executive Summary, Introduction, Methodology, Discussion, Challenges, Recommendations, Conclusion
- Downloadable PDF reports with charts and visualizations

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add your Groq API key to `.env`:
   ```
   GROQ_API_KEY=your_key_here
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
app.py              - Streamlit UI
providers.py        - Groq/Llama API integration
prompts.py          - Report section prompts and generation
data_utils.py       - Data loading and statistics
report_builder.py   - PDF report generation
chart_export.py     - Chart/visualization generation
assets/             - Cover templates and fonts
CHAT Main Data.xlsx - Assessment dataset
```

## Requirements

- Python 3.10+
- Groq API key (free at [console.groq.com](https://console.groq.com))
