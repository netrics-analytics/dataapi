# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Flask-based REST API that serves as a data gateway for extracting advertising and conversion data from StackAdapt's GraphQL API and Snowflake. The API is deployed on Windows IIS using FastCGI and provides authenticated endpoints for multiple clients to query campaign performance metrics and conversion journeys.

## High-Level Architecture

The application follows a modular architecture where:

1. **Main Application** (`flaskIIS.py`): Flask app that defines HTTP endpoints with Basic Auth
2. **Data Modules**: Each module handles a specific GraphQL query or data source:
   - `MSCampaignGroupInsights.py`: Campaign group-level metrics and insights
   - `MSCampaignInsights.py`: Campaign-level metrics and insights
   - `MSConversionJourney.py`: Conversion path tracking from StackAdapt
   - `MSAdvertiserDeliveryStats.py`: Advertiser delivery statistics by granularity
   - `iMarketConversionJourney.py`: Conversion data from Snowflake for iMarket client
3. **Configuration** (`Cred.py`): Centralized credentials and connection utilities
4. **Web Server** (`web.config`): IIS/FastCGI configuration for Windows deployment

### Data Flow
```
Client Request → Flask Endpoint (Basic Auth) → Data Module → External API (StackAdapt GraphQL or Snowflake) → Paginated Fetch → DataFrame → JSON Response
```

### Authentication & Authorization
- All endpoints use HTTP Basic Authentication via `flask_httpauth`
- User credentials stored in `Cred.apiUsers`
- Special route restriction: `iMarketSolutions` user can only access `/iMarketSolutions/*` endpoints

## Common Development Commands

### Virtual Environment Setup
```bash
# Activate virtual environment (Windows)
FlaskWebVenv\Scripts\activate.bat

# Activate virtual environment (PowerShell)
FlaskWebVenv\Scripts\Activate.ps1

# Activate virtual environment (macOS/Linux - if testing locally)
source FlaskWebVenv/bin/activate
```

### Running the Application

#### Local Development
```bash
# Activate venv first, then:
python flaskIIS.py
# Server runs on http://localhost:5000 in debug mode
```

#### IIS Deployment (Windows Production)
The application is configured to run via IIS FastCGI using `web.config`:
- FastCGI handler points to `FlaskWebVenv\Scripts\python.exe`
- Uses `wfastcgi.py` as the script processor
- Deployed path: `C:\inetpub\wwwroot\dataapi\`

### API Endpoint Usage

All endpoints require HTTP Basic Auth headers and specific query parameters:

#### MarketStorm Endpoints

**Conversion Journey**
```bash
curl -u "username:password" -H "APIKey: your-stackadapt-key" \
  "http://localhost:5000/conversionJourney?startDate=2024-01-01&endDate=2024-01-31&campaignIds=123,456&trackerIds=789"
```

**Advertiser Delivery Stats**
```bash
curl -u "username:password" -H "APIKey: your-stackadapt-key" \
  "http://localhost:5000/advertiserDeliveryStats?startDate=2024-01-01&endDate=2024-01-31&granularity=DAILY"
```

**Campaign Group Insights**
```bash
curl -u "username:password" -H "APIKey: your-stackadapt-key" \
  "http://localhost:5000/campaignGroupInsights?startDate=2024-01-01&endDate=2024-01-31"
```

**Campaign Insights**
```bash
curl -u "username:password" -H "APIKey: your-stackadapt-key" \
  "http://localhost:5000/campaignInsights?startDate=2024-01-01&endDate=2024-01-31"
```

#### iMarketSolutions Endpoint

**Conversion Journey (Snowflake)**
```bash
curl -u "iMarketSolutions:password" \
  "http://localhost:5000/iMarketSolutions/conversionJourney?startDate=2024-01-01&endDate=2024-01-31&AdvertiserID=12345"
```

### Response Format
All endpoints return JSON with:
```json
{
  "#records": 150,
  "data": [
    { /* record 1 */ },
    { /* record 2 */ }
  ]
}
```

## Key Implementation Details

### GraphQL Data Fetching Pattern
All StackAdapt modules (`MS*.py`) implement:
- `fetch_graphql_data()`: Single GraphQL request with error handling
- `fetch_all_data()`: Pagination handler that loops through cursor-based pages
- `pullData()`: Public interface that formats dates and returns DataFrame dictionaries

### Error Handling & Retry Logic
- `MSCampaignGroupInsights.py` and `MSCampaignInsights.py` include sophisticated retry mechanisms with:
  - Exponential backoff for transient failures
  - Specific handling for missing 'records' responses
  - Maximum retry limits (default: 10 retries)
- Other modules have simpler pagination without retry logic

### Date Handling
- StackAdapt endpoints use ISO8601 format: `YYYY-MM-DDTHH:MM:SS+0000`
- End dates are adjusted by +1 day in some queries to include the full end date
- Conversion journey tracks timezone offsets via `extract_timezone_offset_in_minutes()`

### Data Processing
- All modules use `pandas.json_normalize()` with `sep="_"` for nested JSON flattening
- Empty values filled with `''` (empty string) via `.fillna('')`
- DataFrame converted to dictionary with `orient='records'` before JSON serialization

## Technology Stack

- **Framework**: Flask 2.x with Flask-HTTPAuth
- **Data Processing**: pandas, json_normalize
- **HTTP Client**: requests library
- **Database**: Snowflake (via snowflake-connector-python and SQLAlchemy)
- **Server**: Windows IIS with FastCGI (wfastcgi)
- **Python Version**: 3.12 (based on venv structure)

## External Dependencies

### StackAdapt GraphQL API
- Endpoint: `https://api.stackadapt.com/graphql`
- Authentication: Bearer token in `Authorization` header
- API key stored in `Cred.APIKey`

### Snowflake Database
- Used exclusively by `iMarketConversionJourney.py`
- Connection details in `Cred.py`: account `hmimopy-dvb53256`, warehouse `PROD`
- Queries `IMARKET_CONVERSION_JOURNEY` table with conversion tracker filters

## Security Considerations

- `Cred.py` contains hardcoded credentials (API keys, passwords, Snowflake credentials)
- **IMPORTANT**: Never commit `Cred.py` to version control
- In production, credentials should be moved to environment variables or secure vault
- The existing `Cred.py` should be added to `.gitignore`

## Code Modification Guidelines

### Adding New Endpoints
1. Create new data module following pattern: `def pullData(APIKey, startDate, endDate, ...)`
2. Import module in `flaskIIS.py`
3. Add route with `@auth.login_required` decorator
4. Call `restrict_access()` if needed for user-specific routes
5. Extract parameters, call module's `pullData()`, format response with `#records`

### Modifying GraphQL Queries
1. Update the `query` string in the respective module
2. Test pagination still works with `pageInfo` and `nodes` structure
3. Ensure `json_normalize(data, sep="_")` properly flattens new nested fields
4. Update any specific field processing (e.g., date conversions)

### Changing Retry Behavior
- Adjust `max_retries` and `retry_delay` parameters in `fetch_all_data()` calls
- Modify exponential backoff formula: `delay = retry_delay * (2 ** retries) + random.uniform(0, 1)`
- Consider adding retry logic to simpler modules if reliability issues occur
