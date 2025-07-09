# Congressional Data Download Rate Limiting Guide

## Overview

The House Clerk's financial disclosure website (`disclosures-clerk.house.gov`) implements rate limiting to prevent abuse of their servers. This guide explains how to handle rate limiting when downloading congressional trading data.

## Rate Limiting Implementation

The enhanced `fetch_congress_data.py` includes several mechanisms to handle rate limiting:

### 1. **Request Delays**
- **Default**: 2 seconds between each request
- **Purpose**: Prevents overwhelming the server
- **Configurable**: Use `--delay` parameter

### 2. **Concurrent Request Limits** 
- **Default**: Maximum 3 concurrent downloads
- **Purpose**: Reduces server load
- **Configurable**: Use `--concurrent` parameter

### 3. **Retry Logic**
- **Default**: 3 retry attempts for failed downloads
- **Purpose**: Handles temporary rate limiting (HTTP 403 errors)
- **Configurable**: Use `--retries` parameter

### 4. **Batch Processing**
- **Default**: Process 10 documents per batch
- **Purpose**: Reduces memory usage and allows progress tracking
- **Built-in delay**: 5 seconds between batches

### 5. **Resume Capability**
- **Function**: Skips already downloaded PDFs
- **Purpose**: Allows resuming interrupted downloads
- **Automatic**: No configuration needed

## Usage Examples

### Basic Usage (Default Settings)
```bash
python fetch_congress_data.py 2024
```

### Conservative Settings (Slower but More Reliable)
```bash
python fetch_congress_data.py 2024 --delay 5.0 --concurrent 1 --retries 5 --retry-delay 10.0
```

### Aggressive Settings (Faster but May Hit Rate Limits)
```bash
python fetch_congress_data.py 2024 --delay 1.0 --concurrent 5 --retries 2 --retry-delay 3.0
```

### For Historical Data Processing
```bash
# Process multiple years with conservative settings
for year in 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023; do
    python fetch_congress_data.py $year --delay 3.0 --concurrent 2 --retries 5
    sleep 30  # Wait between years
done
```

## Troubleshooting Rate Limiting

### Symptoms of Rate Limiting
- Multiple `HTTP 403 Forbidden` errors
- Download failures clustering together
- Server rejecting requests after initial success

### Solutions

1. **Increase Delays**
   ```bash
   python fetch_congress_data.py 2024 --delay 5.0 --retry-delay 15.0
   ```

2. **Reduce Concurrency**
   ```bash
   python fetch_congress_data.py 2024 --concurrent 1
   ```

3. **Resume Interrupted Downloads**
   - Simply re-run the same command
   - Already downloaded PDFs will be skipped automatically

4. **Process in Smaller Batches**
   - The script automatically processes in batches of 10
   - Wait longer between running different years

## Best Practices

### For Regular Updates (Current Year)
- Use default settings
- Run during off-peak hours
- Monitor for 403 errors

### For Historical Data Backfill
- Use conservative settings (`--delay 3.0 --concurrent 2`)
- Process one year at a time
- Add delays between years
- Run overnight or during weekends

### For Development/Testing
- Use very conservative settings
- Test with small datasets first
- Monitor server responses

## Error Handling

The script handles several types of errors:

1. **HTTP 403 (Rate Limited)**: Automatically retried with exponential backoff
2. **HTTP 404 (Not Found)**: Logged and skipped
3. **Network Timeouts**: Retried up to maximum attempts
4. **Parsing Errors**: Logged but don't stop processing

## Monitoring Progress

The script provides detailed logging:
- Batch progress (e.g., "Processing batch 5/20")
- Individual download status
- Success/failure counts
- Rate limiting events

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--delay` | 2.0 | Seconds between requests |
| `--concurrent` | 3 | Max concurrent downloads |
| `--retries` | 3 | Max retry attempts |
| `--retry-delay` | 5.0 | Seconds between retries |
| `--log-level` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `--log-file` | None | Log file path (console only if not specified) |
| `--quiet` | False | Quiet mode - only warnings and errors |

## Logging Configuration

The enhanced script includes structured logging with multiple levels:

### **Logging Levels**

1. **DEBUG**: Detailed information for troubleshooting
   - Individual member processing
   - DocID validation details
   - Existing PDF detection
   - Rate limiting delays
   - Individual record parsing

2. **INFO**: General progress information (default)
   - Processing progress
   - Download summaries
   - Record counts
   - Configuration details

3. **WARNING**: Important issues that don't stop processing
   - Rate limiting events
   - Missing DocIDs
   - Failed individual downloads

4. **ERROR**: Serious problems that may affect results
   - Download failures
   - Parsing errors
   - System errors

### **Logging Examples**

```bash
# Standard INFO logging (default)
python fetch_congress_data.py 2024

# Debug logging with file output
python fetch_congress_data.py 2024 --log-level DEBUG --log-file debug.log

# Quiet mode for automation (warnings and errors only)
python fetch_congress_data.py 2024 --quiet

# Production logging with error file
python fetch_congress_data.py 2024 --quiet --log-file /var/log/congress_errors.log

# Detailed debugging with conservative rate limiting
python fetch_congress_data.py 2024 --delay 5.0 --concurrent 1 --log-level DEBUG
```

### **Service Integration**

For integration with larger service architectures:

```python
import logging
from fetch_congress_data import setup_logging, CongressTrades

# Configure logging to match your service
logger = setup_logging(
    level=logging.INFO,
    log_file="/var/log/your_service/congress_data.log"
)

# All congressional data operations now use consistent logging
trades = CongressTrades(year=2024)
```

### **Log Output Examples**

**INFO Level:**
```
2024-01-15 10:30:00 - congress_data - INFO - === Congressional Trading Data Processing ===
2024-01-15 10:30:01 - congress_data - INFO - Rate limiting configured: Request delay: 2.0s
2024-01-15 10:30:02 - congress_data - INFO - Processed 500 members: 250 valid, 250 invalid DocIDs
2024-01-15 10:30:03 - congress_data - INFO - Starting download of 150 new PDFs
2024-01-15 10:30:05 - congress_data - INFO - Processing batch 1/15 (10 documents)
```

**DEBUG Level:**
```
2024-01-15 10:30:02 - congress_data - DEBUG - Processing: Smith
2024-01-15 10:30:02 - congress_data - DEBUG - DocID download: 20024567
2024-01-15 10:30:03 - congress_data - DEBUG - PDF already exists for 20024568, skipping download
2024-01-15 10:30:03 - congress_data - DEBUG - Parsed existing PDF 20024568 with 3 records
```

**Quiet Mode:**
```
2024-01-15 10:30:15 - congress_data - WARNING - Rate limited (HTTP 403) for 20024570
2024-01-15 10:30:20 - congress_data - ERROR - All retry attempts failed for 20024571
```

## Technical Notes

- **No Official API Documentation**: The House Clerk website doesn't publish formal rate limiting policies
- **Empirical Testing**: Settings based on observed behavior and common web scraping practices
- **Respectful Downloading**: Always prioritize being respectful to government servers
- **Resume Capability**: Uses local file existence to determine what to skip

## Contact Information

If you encounter persistent rate limiting issues, consider:
- Contacting the House Clerk's technical support: `clerkweb@mail.house.gov`
- Using the Legislative Resource Center: `(202) 226-5200`
- Checking for official API announcements

Remember: Congressional financial disclosure data is public information, but servers have capacity limits. Always download responsibly. 