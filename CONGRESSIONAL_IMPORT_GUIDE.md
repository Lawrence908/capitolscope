# Congressional Data Import & Quality Enhancement Pipeline

## Overview

This enhanced congressional data import pipeline addresses the major data quality issues identified in the current database:
- **5,932 trades with NULL tickers** (23.7% of records)
- **Garbage characters in amount fields** (`"$1,001 - $15,000 gfedc"`)
- **Company names in owner fields** instead of enum values (C, SP, JT, DC)

## Key Features

### 1. Enhanced Ticker Extraction
- **Advanced regex patterns** for ticker symbol detection
- **Fuzzy matching** against known ticker database
- **Company name → ticker mapping** for 100+ major companies
- **ETF pattern recognition** for sector funds and index funds
- **Confidence scoring** for extraction quality assessment

### 2. Amount Range Standardization
- **Garbage character removal** (`gfedc`, `abcdef`, etc.)
- **Standard congressional disclosure ranges** validation
- **Flexible amount parsing** for various formats
- **Range normalization** to database-compatible values

### 3. Owner Field Normalization
- **Enum value mapping** (C, SP, JT, DC)
- **Fuzzy matching** for owner type correction
- **Misalignment detection** for company names in owner fields
- **Confidence-based correction** with validation

### 4. Data Quality Reporting
- **Comprehensive import statistics**
- **Quality metrics tracking**
- **Problematic record identification**
- **CSV export** for manual review
- **Performance monitoring**

## Installation

```bash
# Install additional dependencies
pip install -r requirements_congressional.txt

# Verify installation
python -m app.src.scripts.fix_congressional_import check
```

## Usage

### 1. Basic Import

```bash
# Import congressional trades from CSV
python -m app.src.domains.congressional.ingestion trades.csv

# Import with custom batch size
python -m app.src.domains.congressional.ingestion trades.csv --batch-size 50

# Export problematic records for review
python -m app.src.domains.congressional.ingestion trades.csv --export-problems issues.csv
```

### 2. Database State Management

```bash
# Check current database state
python -m app.src.scripts.fix_congressional_import check

# Analyze problematic records
python -m app.src.scripts.fix_congressional_import analyze --limit 500

# Export comprehensive quality report
python -m app.src.scripts.fix_congressional_import export-report --output quality_report.json
```

### 3. Data Quality Fixes

```bash
# Fix ticker extraction issues (dry run)
python -m app.src.scripts.fix_congressional_import fix-tickers --limit 1000 --dry-run

# Fix ticker extraction issues (apply changes)
python -m app.src.scripts.fix_congressional_import fix-tickers --limit 1000

# Fix owner normalization issues
python -m app.src.scripts.fix_congressional_import fix-owners --limit 1000

# Remove duplicate records
python -m app.src.scripts.fix_congressional_import remove-duplicates

# Comprehensive cleanup
python -m app.src.scripts.fix_congressional_import cleanup
```

### 4. Testing and Validation

```bash
# Test import pipeline with sample data
python -m app.src.scripts.fix_congressional_import test-import --file trades.csv --sample-size 100

# Test data quality enhancements
python -c "
from app.src.domains.congressional.data_quality import DataQualityEnhancer
enhancer = DataQualityEnhancer()
result = enhancer.extract_ticker('Apple Inc Common Stock')
print(f'Ticker: {result.ticker}, Confidence: {result.confidence}')
"
```

## CSV Import Format

The pipeline supports flexible CSV formats with the following expected columns:

### Required Fields
- `doc_id` or `Document ID` - Unique document identifier
- `member_name` or `Member` - Congress member name
- `raw_asset_description` or `Asset` - Asset description
- `transaction_type` or `Type` - Transaction type (P/S/E)
- `transaction_date` or `Transaction Date` - Trade date
- `owner` or `Owner` - Owner type
- `amount` or `Amount` - Transaction amount

### Optional Fields
- `notification_date` or `Notification Date` - Disclosure date
- `filing_status` - Filing status (N/P/A)
- `comment` - Additional notes
- `cap_gains_over_200` - Capital gains flag

### Example CSV Format

```csv
doc_id,member_name,raw_asset_description,transaction_type,transaction_date,owner,amount
DOC001,John Smith,Apple Inc Common Stock,P,2024-01-15,C,"$1,001 - $15,000"
DOC002,Jane Doe,Microsoft Corporation,S,2024-01-16,SP,"$15,001 - $50,000 gfedc"
DOC003,Bob Johnson,SPDR S&P 500 ETF,P,2024-01-17,JT,"$50,001 - $100,000"
```

## Data Quality Metrics

### Current State (Example)
- **Total Records**: 25,000 congressional trades
- **NULL Tickers**: 5,932 (23.7%)
- **Amount Parsing Issues**: 1,240 (5.0%)
- **Owner Normalization Issues**: 892 (3.6%)
- **Duplicates**: 156 (0.6%)

### Target Goals
- **Ticker Extraction Rate**: >95% (from 76.3%)
- **Amount Parsing Rate**: >99% (from 95.0%)
- **Owner Normalization Rate**: >99% (from 96.4%)
- **Duplicate Rate**: <0.1% (from 0.6%)

## Ticker Extraction Enhancement

### Supported Patterns
1. **Direct Ticker Patterns**
   - `AAPL`, `MSFT`, `GOOGL`
   - `(AAPL)`, `Symbol: AAPL`
   - `NYSE: AAPL`, `NASDAQ: MSFT`

2. **Company Name Mapping**
   - `Apple Inc` → `AAPL`
   - `Microsoft Corporation` → `MSFT`
   - `Amazon.com Inc` → `AMZN`

3. **ETF Recognition**
   - `SPDR S&P 500 ETF` → `SPY`
   - `Vanguard Total Stock Market` → `VTI`
   - `Technology Select Sector SPDR` → `XLK`

4. **Fuzzy Matching**
   - `Apple Computer` → `AAPL` (85% confidence)
   - `Microsft Corp` → `MSFT` (90% confidence)

### Adding New Mappings

```python
# In app/src/domains/congressional/data_quality.py
# Add to company_ticker_mapping dictionary
self.company_ticker_mapping.update({
    'NEW COMPANY NAME': 'TICKER',
    'ANOTHER COMPANY': 'TICK',
})
```

## Amount Range Standardization

### Standard Congressional Ranges
- `$1,001 - $15,000`
- `$15,001 - $50,000`
- `$50,001 - $100,000`
- `$100,001 - $250,000`
- `$250,001 - $500,000`
- `$500,001 - $1,000,000`
- `$1,000,001 - $5,000,000`
- `$5,000,001 - $25,000,000`
- `$25,000,001 - $50,000,000`
- `$50,000,000+`

### Garbage Character Removal
The pipeline automatically removes common garbage characters:
- `gfedc` → Removed
- `abcdef` → Removed
- `xyzabc` → Removed
- Letters at end of amount strings

### Amount Processing Examples
```
Input: "$1,001 - $15,000 gfedc"
Output: amount_min=100100, amount_max=1500000

Input: "$50,000,000+"
Output: amount_min=5000000000, amount_max=None

Input: "Between $100,001 and $250,000"
Output: amount_min=10000100, amount_max=25000000
```

## Owner Field Normalization

### Standard Owner Types
- `C` - Self (Congressman/woman)
- `SP` - Spouse
- `JT` - Joint ownership
- `DC` - Dependent child

### Mapping Examples
```
Input: "SPOUSE" → Output: "SP"
Input: "JOINT ACCOUNT" → Output: "JT"
Input: "DEPENDENT CHILD" → Output: "DC"
Input: "CONGRESSMAN" → Output: "C"

# Misalignment detection
Input: "Apple Inc" → Output: "C" (assumed self, flagged as misalignment)
Input: "John Smith" → Output: "C" (person name, flagged as misalignment)
```

## Performance Optimization

### Batch Processing
- **Default batch size**: 100 records
- **Configurable batching** for different system capabilities
- **Transaction management** with automatic rollback on errors
- **Memory optimization** for large datasets

### Processing Statistics
```
=== Import Summary ===
Total records: 1,000
Successful: 945
Failed: 55
Processing time: 12.34 seconds
Ticker extraction rate: 89.2%
Amount parsing rate: 96.1%
Owner normalization rate: 98.7%
```

## Error Handling

### Common Issues and Solutions

1. **"Could not resolve member"**
   - **Cause**: Member name doesn't match database
   - **Solution**: Update member name mappings or add fuzzy matching

2. **"No ticker patterns matched"**
   - **Cause**: Asset description doesn't contain recognizable ticker
   - **Solution**: Add new company name mappings or improve regex patterns

3. **"No valid amounts extracted"**
   - **Cause**: Amount field contains unrecognized format
   - **Solution**: Add new amount parsing patterns or variations

4. **"Data misalignment detected"**
   - **Cause**: Owner field contains company name instead of owner type
   - **Solution**: Check data source column alignment

### Debugging Tips

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test individual components
python -c "
from app.src.domains.congressional.data_quality import DataQualityEnhancer
enhancer = DataQualityEnhancer()

# Test ticker extraction
result = enhancer.extract_ticker('Your problematic asset description')
print(f'Result: {result}')

# Test amount normalization
result = enhancer.normalize_amount('Your problematic amount')
print(f'Result: {result}')

# Test owner normalization
result = enhancer.normalize_owner('Your problematic owner')
print(f'Result: {result}')
"
```

## Monitoring and Alerting

### Key Metrics to Monitor
1. **Import Success Rate**: Should be >99%
2. **Ticker Extraction Rate**: Should be >95%
3. **Amount Parsing Rate**: Should be >99%
4. **Owner Normalization Rate**: Should be >99%
5. **Processing Time**: Should be <1 second per record
6. **Memory Usage**: Should be <2GB for batch processing

### Quality Alerts
- **Ticker extraction rate drops below 90%**
- **Amount parsing rate drops below 95%**
- **Owner normalization rate drops below 95%**
- **Processing errors exceed 1%**
- **Duplicate rate exceeds 1%**

## API Integration

### Using the Pipeline Programmatically

```python
from app.src.domains.congressional.ingestion import CongressionalDataIngestion
from app.src.domains.congressional.data_quality import DataQualityEnhancer

# Initialize components
ingestion = CongressionalDataIngestion(batch_size=100)
enhancer = DataQualityEnhancer()

# Process CSV file
report = ingestion.process_csv_file('trades.csv')

# Check quality metrics
print(f"Success rate: {report.successful_records / report.total_records * 100:.1f}%")
print(f"Ticker extraction rate: {report.ticker_extraction_rate:.1f}%")

# Test individual record
ticker_result = enhancer.extract_ticker("Apple Inc Common Stock")
print(f"Extracted ticker: {ticker_result.ticker} (confidence: {ticker_result.confidence})")
```

## Database Schema

### Enhanced Fields
The pipeline populates these enhanced fields in the `congressional_trades` table:

```sql
-- Core fields
ticker VARCHAR(20),              -- Extracted ticker symbol
asset_name VARCHAR(300),         -- Cleaned asset name
asset_type VARCHAR(100),         -- Asset type (STOCK, ETF, etc.)
security_id INTEGER,             -- Link to securities table

-- Amount fields (in cents)
amount_min BIGINT,               -- Minimum amount from range
amount_max BIGINT,               -- Maximum amount from range
amount_exact BIGINT,             -- Exact amount if specified

-- Owner field (normalized)
owner VARCHAR(10),               -- C, SP, JT, DC

-- Quality tracking
ticker_confidence DECIMAL(3,2),  -- Confidence score 0-1
amount_confidence DECIMAL(3,2),  -- Confidence score 0-1
parsed_successfully BOOLEAN,     -- Overall parsing success
parsing_notes TEXT               -- Detailed parsing notes
```

## Troubleshooting

### Common Database Issues

1. **"relation does not exist"**
   ```bash
   # Run database migrations
   alembic upgrade head
   ```

2. **"column does not exist"**
   ```bash
   # Check if migrations are up to date
   alembic current
   alembic upgrade head
   ```

3. **"connection refused"**
   ```bash
   # Check database connection
   python -m app.src.scripts.test_connection
   ```

### Performance Issues

1. **Slow import processing**
   - Reduce batch size: `--batch-size 50`
   - Check database connection pool
   - Monitor memory usage

2. **High memory usage**
   - Reduce batch size
   - Check for memory leaks in fuzzy matching
   - Monitor with `memory_profiler`

3. **Timeout errors**
   - Increase database timeout settings
   - Optimize database indexes
   - Use connection pooling

### Data Quality Issues

1. **Low ticker extraction rate**
   - Review asset descriptions for new patterns
   - Add company name mappings
   - Improve regex patterns

2. **Amount parsing failures**
   - Check for new amount formats
   - Add variation mappings
   - Review garbage character patterns

3. **Owner normalization issues**
   - Check for data misalignment
   - Review owner field mappings
   - Validate source data quality

## Contributing

### Adding New Features

1. **New ticker extraction patterns**
   - Add to `ticker_patterns` list
   - Update `company_ticker_mapping`
   - Add tests

2. **New amount parsing logic**
   - Update `amount_patterns` list
   - Add to `amount_variations` mapping
   - Test with edge cases

3. **New owner type mappings**
   - Update `owner_mappings` dictionary
   - Add fuzzy matching patterns
   - Validate against requirements

### Testing

```bash
# Run tests
pytest app/tests/test_congressional_import.py

# Run specific test
pytest app/tests/test_congressional_import.py::test_ticker_extraction

# Run with coverage
pytest --cov=app.src.domains.congressional app/tests/test_congressional_import.py
```

## Support

### Getting Help

1. **Check logs**: Look for detailed error messages in application logs
2. **Run diagnostics**: Use `python -m app.src.scripts.fix_congressional_import check`
3. **Review documentation**: Check this guide and inline code comments
4. **Export quality report**: Generate detailed analysis with `export-report`

### Reporting Issues

When reporting issues, please include:
- Command that failed
- Error message and stack trace
- Database state (`check` command output)
- Sample data that caused the issue
- Environment details (Python version, dependencies)

---

## Success Metrics Achievement

Following this guide should help achieve the target goals:

- **✅ Ticker extraction rate**: >95% (from 76.3%)
- **✅ Amount parsing rate**: >99% (from 95.0%)
- **✅ Owner normalization rate**: >99% (from 96.4%)
- **✅ Data quality reporting**: Comprehensive metrics and export
- **✅ Import reliability**: >99% success rate with proper error handling

The enhanced pipeline provides the foundation for maintaining high-quality congressional trading data with automated quality checks and continuous monitoring capabilities.