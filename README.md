# nba repository

A Streamlit-based NBA web app scaffold for exploring teams, players, and recent game results.

## Project Structure

```text
.
├── nba/app/
│   └── main.py                # Streamlit entry point
├── nba/analysis/
│   └── data_processing.py     # Data wrangling and validation helpers
├── nba/services/
│   └── nba_client.py          # NBA API client
└── requirements.txt
```

## Setup

1. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the App

Start Streamlit from the repository root:

```bash
streamlit run nba/app/main.py
```

## Current UI Sections

- **Team selection** via multi-select in the sidebar.
- **Player selection** via search + dropdown.
- **Date filters** for start/end date ranges.
- **Result panels** including a game table and selection summary.
