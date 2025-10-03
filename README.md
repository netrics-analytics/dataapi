# MarketStorm Data API

Flask-based REST API serving as a data gateway for extracting advertising and conversion data from StackAdapt's GraphQL API and Snowflake. Deployed on Windows IIS with FastCGI for production use.

## 🏗️ Architecture

```
Client Request → Flask (Basic Auth) → Data Module → External API → Paginated Fetch → DataFrame → JSON Response
```

### Data Sources
- **StackAdapt GraphQL API**: Campaign metrics, conversion paths, delivery statistics
- **Snowflake Database**: iMarket conversion journey data

### Components
- **Main Application**: `flaskIIS.py` - Flask app with HTTP Basic Auth
- **Data Modules**: Individual Python modules for each API endpoint
- **Credentials**: `Cred.py` (not in repo - see setup below)
- **IIS Config**: `web.config` - FastCGI configuration for Windows deployment

## 📋 API Endpoints

### MarketStorm Endpoints (StackAdapt Data)

All MarketStorm endpoints require:
- HTTP Basic Auth: `MarketStorm` user
- Header: `APIKey: Bearer <stackadapt_key>`

**1. Conversion Journey**
```
GET /conversionJourney?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&campaignIds=&trackerIds=
```
Returns conversion path tracking with attribution details, click/impression counts, campaign information.

**2. Advertiser Delivery Stats**
```
GET /advertiserDeliveryStats?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&granularity=DAILY
```
Returns advertiser-level delivery statistics by time granularity.

**3. Campaign Group Insights**
```
GET /campaignGroupInsights?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
```
Returns campaign group metrics including budget allocation, pacing, and performance.

**4. Campaign Insights**
```
GET /campaignInsights?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
```
Returns individual campaign-level metrics, status, audience targeting, and performance.

### iMarketSolutions Endpoint (Snowflake Data)

Requires HTTP Basic Auth with `iMarketSolutions` user (restricted access).

**5. iMarket Conversion Journey**
```
GET /iMarketSolutions/conversionJourney?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&AdvertiserID=
```
Returns conversion journey data from Snowflake filtered by Phone Call, Form Submit, and SchedulerStarted conversion types.

### Response Format

All endpoints return:
```json
{
  "#records": 150,
  "data": [
    { /* record 1 */ },
    { /* record 2 */ }
  ]
}
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Windows Server with IIS 10.0+
- Access to StackAdapt API
- Snowflake database access (for iMarket endpoint)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/netrics-analytics.git
cd netrics-analytics
```

2. **Create virtual environment**
```bash
python -m venv FlaskWebVenv
# Windows
FlaskWebVenv\Scripts\activate
# macOS/Linux
source FlaskWebVenv/bin/activate
```

3. **Install dependencies**
```bash
pip install flask flask-httpauth pandas requests snowflake-connector-python sqlalchemy
```

4. **Configure credentials**
```bash
cp Cred.py.example Cred.py
# Edit Cred.py with your actual credentials
```

5. **Run locally**
```bash
python flaskIIS.py
# Server runs at http://localhost:5000
```

### Testing with Postman

1. Import `MarketStorm_DataAPI.postman_collection.json` into Postman
2. Update environment variables with your credentials:
   - `marketstorm_password`
   - `imarket_password`
   - `stackadapt_api_key`
3. Send requests to test endpoints

## 🖥️ Production Deployment (Windows IIS)

### Server Configuration

**Production URL**: `http://data.netrics.ai`

**Server Details**:
- Platform: Windows Server on AWS EC2
- Web Server: IIS 10.0 with FastCGI
- Deployment Path: `C:\inetpub\wwwroot\dataapi\`

### Deployment Steps

1. **Copy files to server**
```powershell
# Copy to C:\inetpub\wwwroot\dataapi\
```

2. **Create virtual environment on server**
```powershell
cd C:\inetpub\wwwroot\dataapi
python -m venv FlaskWebVenv
FlaskWebVenv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure IIS**
- Ensure `web.config` points to correct Python executable
- FastCGI handler should be configured for `*.py` files
- Application pool identity needs read/write access

4. **Set permissions**
```powershell
icacls C:\inetpub\wwwroot\dataapi /grant "IIS_IUSRS:(OI)(CI)F" /T
```

5. **Restart IIS**
```powershell
iisreset /restart
```

### Troubleshooting

If the API returns 404 errors, run the diagnostic script:

```powershell
cd C:\inetpub\wwwroot\dataapi
.\Fix-DataAPI.ps1

# Or auto-fix common issues:
.\Fix-DataAPI.ps1 -AutoFix
```

The script checks:
- Python virtual environment
- Flask application imports
- IIS Application Pool status
- FastCGI configuration
- File permissions
- Event logs for errors
- API endpoint connectivity

## 🔧 Development

### Project Structure

```
dataapi/
├── flaskIIS.py                          # Main Flask application
├── Cred.py                              # Credentials (NOT in repo)
├── Cred.py.example                      # Credentials template
├── web.config                           # IIS/FastCGI configuration
├── MSConversionJourney.py              # StackAdapt conversion data
├── MSAdvertiserDeliveryStats.py        # Advertiser delivery stats
├── MSCampaignGroupInsights.py          # Campaign group metrics
├── MSCampaignInsights.py               # Campaign-level metrics
├── iMarketConversionJourney.py         # Snowflake conversion data
├── Fix-DataAPI.ps1                     # Diagnostic/fix script
├── MarketStorm_DataAPI.postman_collection.json  # API testing
├── INCIDENT_REPORT_2025-10-03.md       # Production issue analysis
└── CLAUDE.md                            # AI assistant instructions
```

### Data Module Pattern

All StackAdapt modules (`MS*.py`) follow this pattern:

```python
def fetch_graphql_data(APIKey, endpoint, query, variables=None):
    """Single GraphQL request with error handling"""

def fetch_all_data(APIKey, endpoint, query, variables=None, page_size=1000):
    """Pagination handler using cursor-based paging"""

def pullData(APIKey, startDate, endDate, **kwargs):
    """Public interface - formats dates and returns DataFrame dict"""
```

### Adding New Endpoints

1. Create new data module: `MyNewEndpoint.py`
2. Implement `pullData()` function following the pattern
3. Import in `flaskIIS.py`
4. Add route with `@auth.login_required` decorator
5. Call `restrict_access()` if user-specific
6. Format response with `#records` field

### Error Handling & Retry Logic

`MSCampaignGroupInsights.py` and `MSCampaignInsights.py` include sophisticated retry:
- Exponential backoff for transient failures
- Specific handling for missing 'records' responses
- Maximum retry limits (default: 10)

Other modules use simpler pagination without retry logic.

## 🔐 Security

### Credential Management

**NEVER commit `Cred.py` to version control!**

This file contains:
- StackAdapt API key
- HTTP Basic Auth passwords
- Snowflake database credentials

In production, consider using:
- Environment variables
- AWS Secrets Manager
- Azure Key Vault

### Authentication

- All endpoints use HTTP Basic Authentication
- Route-specific restrictions via `restrict_access()`
- `iMarketSolutions` user can only access `/iMarketSolutions/*` endpoints

## 📊 Monitoring

### Health Checks

Test API availability:
```bash
curl -u "username:password" "http://data.netrics.ai/iMarketSolutions/conversionJourney?startDate=2025-01-01&endDate=2025-01-02"
```

Expected: HTTP 200 with JSON response containing `#records` field

### Logs

**Windows Event Viewer**:
- Application Log → Filter by source: `FastCGI`, `IIS-W3SVC-WP`, `Python`

**IIS Logs**:
- `C:\inetpub\logs\LogFiles\`

## 🐛 Known Issues

### Direct IP Access Returns 404

- ✅ **`http://data.netrics.ai`** - Works correctly
- ❌ **`http://44.239.175.254`** - Returns 404 errors

**Root Cause**: Flask/FastCGI handler not configured for IP-based requests.

**Workaround**: Always use the domain name, not the direct IP.

## 📚 Additional Documentation

- `CLAUDE.md` - Detailed architecture and code modification guidelines
- `INCIDENT_REPORT_2025-10-03.md` - Production incident analysis example
- Postman Collection - Interactive API documentation

## 🤝 Contributing

1. Never commit `Cred.py` or files with actual credentials
2. Follow existing code patterns for data modules
3. Test endpoints with Postman collection before deploying
4. Update CLAUDE.md if making architectural changes

## 📞 Support

For production issues:
1. Check `http://data.netrics.ai` is accessible
2. Run `Fix-DataAPI.ps1` on the server
3. Review Windows Event Viewer for errors
4. Check Snowflake/StackAdapt API status

## 📝 License

Internal use only - MarketStorm proprietary.

---

**Production Status**: ✅ Operational at `http://data.netrics.ai`

**Last Updated**: October 3, 2025
