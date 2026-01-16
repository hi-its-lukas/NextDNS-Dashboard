# NextDNS Advanced Analytics Dashboard

## Overview
A Python/Streamlit web application that connects to the NextDNS API to fetch, analyze, and visualize DNS query logs. Provides advanced analytics beyond the standard NextDNS dashboard including interactive charts, heatmaps, device forensics, and GAFAM tracking analysis.

## Features
- **KPI Dashboard**: Total queries, block rate, top device, top blocked domain
- **Time-Series Analysis**: Interactive timeline showing query volume over time (Blocked vs Allowed)
- **Activity Heatmap**: Day of Week vs Hour of Day visualization
- **Device Forensics**: Filter all charts by specific device
- **GAFAM Analysis**: Track requests to Google, Apple, Meta, Amazon, Microsoft
- **Log Explorer**: Searchable, filterable log viewer with color-coded status
- **CSV Export**: Download filtered data for external reporting

## Tech Stack
- `streamlit` - Frontend/UI
- `pandas` - Data manipulation
- `plotly` - Interactive charts
- `requests` - API calls
- `pytz` - Timezone handling

## Project Structure
```
├── app.py                    # Main Streamlit application
├── .streamlit/
│   └── config.toml          # Streamlit configuration (dark theme)
├── pyproject.toml           # Python dependencies
└── replit.md                # This file
```

## Running the Application
The app runs on port 5000 using the command:
```
streamlit run app.py --server.port 5000
```

## Usage
1. Enter your NextDNS API Key (from my.nextdns.io/account)
2. Enter your Profile ID
3. Select number of logs to fetch
4. Click "Fetch Data"

## API Reference
- Base URL: `https://api.nextdns.io`
- Authentication: `X-Api-Key` header
- Main endpoint: `GET /profiles/{profile_id}/logs`

## Recent Changes
- 2026-01-16: Initial implementation with all core features
