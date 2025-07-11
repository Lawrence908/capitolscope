# Yahoo Finance Rate Limiting Issue and Solutions

## Problem Summary

The `seed_securities_database.py` script was experiencing widespread 429 "Too Many Requests" errors from Yahoo Finance's API. This is a known issue affecting many users, as documented in the [yahoofinance-api GitHub issue #211](https://github.com/sstrickx/yahoofinance-api/issues/211).

### Root Cause Analysis

1. **Widespread Issue**: Yahoo Finance has significantly tightened their rate limiting policies
2. **Authentication Level**: The 429 errors occur at the crumb authentication level, before actual data fetching
3. **Global Impact**: This affects all users of the Yahoo Finance API, not just our implementation

## Solutions Implemented

### 1. Enhanced Rate Limiting (Primary Script)

**File**: `app/src/domains/securities/ingestion.py`

**Improvements**:
- Increased delays from 0.1s to 3.0s between successful requests
- Added exponential backoff with 3x multiplier (was 2x)
- Added random delays (2-5 seconds) to avoid synchronized requests
- Implemented global rate limiting state with 5-minute cooldown
- Added longer delays between ticker processing (2s between each, 10s every 5 tickers)

**Usage**:
```bash
python app/src/scripts/seed_securities_database.py --rate-limit conservative
```

### 2. Conservative Rate Limiting Script

**File**: `app/src/scripts/seed_securities_database_conservative.py`

**Features**:
- Processes only S&P 500 tickers (limited subset)
- 10-second delays between tickers
- 30-second pauses every 3 tickers
- 5-minute cooldown after rate limiting detection
- Configurable max tickers (default: 50)

**Usage**:
```bash
python app/src/scripts/seed_securities_database_conservative.py --max-tickers 20
```

### 3. Alpha Vantage Only Script

**File**: `app/src/scripts/seed_securities_alpha_vantage.py`

**Features**:
- Completely bypasses Yahoo Finance API
- Uses only Alpha Vantage API for data fetching
- 2-second delays between requests
- Requires `ALPHA_VANTAGE_API_KEY` environment variable
- More reliable but requires API key

**Usage**:
```bash
# Set API key first
export ALPHA_VANTAGE_API_KEY=your_api_key_here

# Run the script
python app/src/scripts/seed_securities_alpha_vantage.py --max-tickers 100
```

## Recommended Approach

### For Immediate Use (No API Key Required)
```bash
# Try the conservative approach first
python app/src/scripts/seed_securities_database_conservative.py --max-tickers 20
```

### For Reliable Long-term Use (Requires Alpha Vantage API Key)
1. Get a free Alpha Vantage API key from [alphavantage.co](https://www.alphavantage.co/support/#api-key)
2. Set the environment variable:
   ```bash
   export ALPHA_VANTAGE_API_KEY=your_api_key_here
   ```
3. Run the Alpha Vantage script:
   ```bash
   python app/src/scripts/seed_securities_alpha_vantage.py --max-tickers 100
   ```

## Technical Details

### Rate Limiting Improvements

1. **Global State Management**:
   ```python
   yfinance_rate_limited = False
   rate_limit_detected_time = 0
   ```

2. **Enhanced Delays**:
   - Success delay: 3.0s (was 0.1s)
   - Rate limit delay: 10-30s (was 5-10s)
   - Between tickers: 2.0s (was 0.5s)
   - Every 5 tickers: 10.0s (was 5.0s)

3. **Fallback Strategy**:
   - When rate limiting is detected, switches to Alpha Vantage
   - 5-minute cooldown before retrying Yahoo Finance
   - Graceful degradation to alternative data sources

### Alpha Vantage Integration

The Alpha Vantage script provides:
- Complete bypass of Yahoo Finance
- Reliable data fetching with proper rate limiting
- Same data structure as Yahoo Finance output
- Better error handling and logging

## Testing

### Test Rate Limiting Improvements
```bash
python app/src/scripts/test_rate_limiting.py
```

### Test Alpha Vantage Integration
```bash
# With API key set
python app/src/scripts/seed_securities_alpha_vantage.py --max-tickers 5
```

## Monitoring and Debugging

### Check Rate Limiting State
The scripts provide detailed logging:
- Rate limiting events
- Success/failure counts
- Progress updates
- Error details

### Environment Variables
```bash
# For Alpha Vantage
export ALPHA_VANTAGE_API_KEY=your_key_here

# For debugging
export LOG_LEVEL=DEBUG
```

## Future Improvements

1. **Multiple Data Sources**: Implement additional fallback APIs
2. **Caching**: Cache successful responses to reduce API calls
3. **Batch Processing**: Process tickers in smaller batches
4. **Retry Logic**: Implement more sophisticated retry strategies
5. **Monitoring**: Add metrics and alerting for rate limiting events

## Troubleshooting

### Common Issues

1. **Still Getting 429 Errors**:
   - Use the Alpha Vantage script instead
   - Reduce the number of tickers processed
   - Increase delays further

2. **Alpha Vantage API Key Issues**:
   - Verify the API key is set correctly
   - Check Alpha Vantage account status
   - Ensure the key has sufficient quota

3. **Database Connection Issues**:
   - Check database connectivity
   - Verify environment variables
   - Check database schema

### Getting Help

If you continue to experience issues:
1. Check the logs for specific error messages
2. Try the Alpha Vantage script as a fallback
3. Reduce the number of tickers processed
4. Consider running during off-peak hours

## Conclusion

The Yahoo Finance rate limiting issue is widespread and affects many users. The implemented solutions provide multiple approaches:

1. **Enhanced rate limiting** for existing users
2. **Conservative processing** for limited datasets
3. **Alpha Vantage fallback** for reliable operation

Choose the approach that best fits your needs and API key availability. 