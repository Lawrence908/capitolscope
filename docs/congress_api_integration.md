# Congress.gov API Integration

This document describes the integration of the Congress.gov API into CapitolScope for automatically fetching and updating U.S. Congress member profiles.

## Overview

The Congress.gov API integration allows CapitolScope to:
- Fetch detailed congressional member profiles
- Automatically update member information
- Sync member data with bioguide IDs
- Enrich existing member records with official data
- Track legislative activities and sponsored/cosponsored bills

## Setup

### 1. API Key Configuration

First, obtain an API key from the Library of Congress:
1. Visit: https://api.congress.gov/sign-up/
2. Request an API key
3. Add it to your environment variables:

```bash
export CONGRESS_GOV_API_KEY=your_api_key_here
```

Or add it to your `.env` file:
```
CONGRESS_GOV_API_KEY=your_api_key_here
```

### 2. Database Migration

The integration uses the existing `congress_gov_id` field to store the API member reference. No additional migration is needed for the basic integration.

### 3. Dependencies

All necessary dependencies are already included in the project's `pyproject.toml`. The integration uses:
- `aiohttp` for async HTTP requests
- `pydantic` for data validation
- Rate limiting and retry logic

## Usage

### Manual Sync Script

The main sync script is located at `app/src/scripts/sync_congress_members.py`. It supports several actions:

#### Test API Connection
```bash
python -m scripts.sync_congress_members --action test-api
```

#### Sync All Members (Current Congress)
```bash
python -m scripts.sync_congress_members --action sync-all
```

#### Sync Specific Member
```bash
python -m scripts.sync_congress_members --action sync-member --bioguide-id A000374
```

#### Sync Members by State
```bash
python -m scripts.sync_congress_members --action sync-state --state CA
```

#### Enrich Existing Members
```bash
python -m scripts.sync_congress_members --action enrich-existing
```

### Background Tasks

The integration includes Celery tasks for automated synchronization:

#### Sync All Members
```python
from background.tasks import sync_congressional_members
sync_congressional_members.delay("sync-all")
```

#### Sync Members by State
```python
sync_congressional_members.delay("sync-state", state="CA")
```

#### Sync Specific Member
```python
sync_congressional_members.delay("sync-member", bioguide_id="A000374")
```

### Programmatic Usage

#### Using the API Client Directly

```python
from domains.congressional.client import CongressAPIClient

async with CongressAPIClient() as client:
    # Get all members
    response = await client.get_member_list(limit=50)
    
    # Get specific member
    member = await client.get_member_by_bioguide_id("A000374")
    
    # Get members by state
    ca_members = await client.get_members_by_state("CA")
    
    # Get sponsored legislation
    legislation = await client.get_member_sponsored_legislation("A000374")
```

#### Using the Service Layer

```python
from domains.congressional.services import CongressAPIService
from domains.congressional.crud import CongressMemberRepository

# Initialize services
member_repo = CongressMemberRepository(session)
api_service = CongressAPIService(member_repo)

# Sync all members
results = await api_service.sync_all_members()

# Sync specific member
result = await api_service.sync_member_by_bioguide_id("A000374")

# Sync members by state
results = await api_service.sync_members_by_state("CA")
```

## API Endpoints Used

The integration uses the following Congress.gov API endpoints:

### Member Endpoints
- `GET /v3/member` - List all members
- `GET /v3/member/{bioguideId}` - Get member details
- `GET /v3/member/{stateCode}` - Get members by state
- `GET /v3/member/{stateCode}/{district}` - Get members by state and district
- `GET /v3/member/congress/{congress}` - Get members by Congress number

### Legislation Endpoints
- `GET /v3/member/{bioguideId}/sponsored-legislation` - Get sponsored legislation
- `GET /v3/member/{bioguideId}/cosponsored-legislation` - Get cosponsored legislation

## Data Mapping

The integration maps Congress.gov API data to CapitolScope's database schema:

| API Field | Database Field | Description |
|-----------|---------------|-------------|
| `bioguideId` | `bioguide_id` | Biographical Directory ID |
| `bioguideId` | `congress_gov_id` | Congress.gov API member ID (same as bioguide ID) |
| `name` | `first_name`, `last_name`, `full_name` | Parsed from "Last, First" format |
| `party` | `party` | Political party (R, D, I) |
| `state` | `state` | Two-letter state code |
| `district` | `district` | Congressional district |
| `terms[].startYear` | `term_start` | Term start date |
| `terms[].endYear` | `term_end` | Term end date |
| `terms[].congress` | `congress_number` | Congress number |

## Rate Limiting

The integration implements rate limiting to comply with the Congress.gov API limits:
- Maximum 5,000 requests per hour
- Built-in retry logic with exponential backoff
- Automatic rate limit detection and waiting

## Error Handling

The integration includes comprehensive error handling:
- API authentication errors
- Rate limit exceeded errors
- Network timeout errors
- Data parsing errors
- Database connection errors

## Monitoring and Logging

All operations are logged with appropriate levels:
- `INFO` for successful operations
- `WARNING` for non-critical issues
- `ERROR` for failures
- `DEBUG` for detailed debugging information

## Scheduling

### Cron Job Example
```bash
# Daily sync at 2 AM
0 2 * * * /path/to/python -m scripts.sync_congress_members --action sync-all

# Weekly enrichment on Sundays at 3 AM
0 3 * * 0 /path/to/python -m scripts.sync_congress_members --action enrich-existing
```

### Celery Beat Schedule
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'sync-congress-members-daily': {
        'task': 'background.tasks.sync_congressional_members',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'args': ('sync-all',)
    },
    'enrich-existing-members-weekly': {
        'task': 'background.tasks.sync_congressional_members',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday at 3 AM
        'args': ('enrich-existing',)
    }
}
```

## API Response Examples

### Member List Response
```json
{
  "members": [
    {
      "bioguideId": "A000374",
      "district": "05",
      "name": "Abraham, Ralph Lee",
      "party": "R",
      "state": "LA",
      "terms": [
        {
          "congress": 118,
          "startYear": "2023",
          "endYear": "2025"
        }
      ],
      "updateDate": "2023-01-03T18:13:36Z",
      "url": "https://api.congress.gov/v3/member/A000374"
    }
  ],
  "pagination": {
    "count": 1,
    "next": null
  }
}
```

### Member Detail Response
```json
{
  "member": {
    "bioguideId": "A000374",
    "birthYear": "1954",
    "currentMember": true,
    "directOrderName": "Abraham, Ralph Lee",
    "district": "05",
    "firstName": "Ralph",
    "lastName": "Abraham",
    "middleName": "Lee",
    "name": "Abraham, Ralph Lee",
    "officialWebsiteUrl": "https://abraham.house.gov",
    "party": "R",
    "state": "LA",
    "terms": [...],
    "updateDate": "2023-01-03T18:13:36Z",
    "url": "https://api.congress.gov/v3/member/A000374"
  }
}
```

## Troubleshooting

### Common Issues

#### API Key Not Working
- Verify the API key is correctly set in environment variables
- Check if the API key has proper permissions
- Ensure the key hasn't expired

#### Rate Limit Exceeded
- The integration automatically handles rate limits
- If persistent issues occur, consider reducing batch sizes
- Check if multiple processes are using the same API key

#### Database Connection Issues
- Ensure the database is running and accessible
- Check database credentials and connection string
- Verify database migrations are up to date

#### Data Sync Issues
- Check if members have valid bioguide IDs
- Review logs for specific error messages
- Ensure the Congress.gov API is accessible

### Debug Mode
Enable debug logging to get detailed information:

```python
import logging
logging.getLogger('domains.congressional').setLevel(logging.DEBUG)
```

### Health Check
Run the API connection test to verify everything is working:

```bash
python -m scripts.sync_congress_members --action test-api
```

## Security Considerations

1. **API Key Security**: Store API keys securely and never commit them to version control
2. **Rate Limiting**: Respect API rate limits to avoid being blocked
3. **Data Validation**: All incoming data is validated before database insertion
4. **Error Handling**: Sensitive information is not exposed in error messages

## Future Enhancements

Potential improvements for the integration:
- Support for historical Congress data
- Integration with additional Congress.gov endpoints
- Real-time webhook support (if available)
- Enhanced data validation and enrichment
- Performance optimizations for large datasets

## Support

For issues related to the Congress.gov API integration:
1. Check the troubleshooting section above
2. Review the application logs for error details
3. Verify API key and permissions
4. Contact the development team with specific error messages and logs