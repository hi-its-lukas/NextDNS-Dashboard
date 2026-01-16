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
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker Compose configuration
├── docker-requirements.txt  # Python dependencies for Docker
├── pyproject.toml           # Python dependencies (Replit)
└── replit.md                # This file
```

## Running on Docker Desktop

### Option 1: Docker Compose (Recommended)
```bash
docker-compose up --build
```
Then open http://localhost:5050 in your browser.

### Option 2: Docker Build & Run
```bash
docker build -t nextdns-dashboard .
docker run -p 5050:5050 nextdns-dashboard
```
Then open http://localhost:5050 in your browser.

### Stop the Container
```bash
docker-compose down
```

## Running on Replit
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
- 2026-01-16: Added PostgreSQL database for persistent storage of credentials and logs
- 2026-01-16: Improved GAFAM analysis with more domains and detailed statistics
- 2026-01-16: Added extended time ranges (6, 12, 24 months) and credential persistence
- 2026-01-16: Changed from log count to time-based data fetching (no limit on log count)
- 2026-01-16: Added Docker support (Dockerfile, docker-compose.yml)
- 2026-01-16: Initial implementation with all core features
