# Congressional Data Migration Strategy

## 🎯 **Recommended Approach: Enhance Existing Data**

### **Why NOT Delete Existing Records:**
- **Preserve Historical Data**: 25,000 records represent valuable historical information
- **Minimize Risk**: Keep original data as backup during enhancement
- **Gradual Improvement**: Can incrementally improve quality
- **Audit Trail**: Maintain record of changes for compliance

## 📋 **Migration Strategy: 3-Phase Approach**

### **Phase 1: Backup & Analysis (Risk-Free)**
```bash
# 1. Create backup of current state
pg_dump -t congressional_trades your_db > congressional_trades_backup.sql

# 2. Analyze current data quality
python -m app.src.scripts.fix_congressional_import check
python -m app.src.scripts.fix_congressional_import analyze --limit 1000
python -m app.src.scripts.fix_congressional_import export-report
```

### **Phase 2: Enhance Existing Data (Reversible)**
```bash
# 1. Fix ticker extraction issues (dry run first)
python -m app.src.scripts.fix_congressional_import fix-tickers --limit 1000 --dry-run
python -m app.src.scripts.fix_congressional_import fix-tickers --limit 1000

# 2. Fix owner normalization issues  
python -m app.src.scripts.fix_congressional_import fix-owners --limit 1000 --dry-run
python -m app.src.scripts.fix_congressional_import fix-owners --limit 1000

# 3. Remove duplicates
python -m app.src.scripts.fix_congressional_import remove-duplicates --dry-run
python -m app.src.scripts.fix_congressional_import remove-duplicates

# 4. Verify improvements
python -m app.src.scripts.fix_congressional_import check
```

### **Phase 3: New Import Pipeline (Production)**
```bash
# Use enhanced pipeline for new data imports
python -m app.src.domains.congressional.ingestion new_trades.csv
```

## 🔄 **Alternative: Clean Slate Approach (If Needed)**

**Only use if existing data quality is irreparable:**

```bash
# 1. Export current data for analysis
python -m app.src.scripts.fix_congressional_import export-report

# 2. Backup everything
pg_dump your_db > full_backup.sql

# 3. Create cleanup script (DANGEROUS - use with caution)
python -c "
from app.src.core.database import db_manager
from app.src.domains.congressional.models import CongressionalTrade

with db_manager.session_scope() as session:
    count = session.query(CongressionalTrade).count()
    print(f'Found {count} records to delete')
    
    # Uncomment next line only if you're sure
    # session.query(CongressionalTrade).delete()
    # session.commit()
    # print('All congressional trades deleted')
"

# 4. Re-import with enhanced pipeline
python -m app.src.domains.congressional.ingestion all_trades.csv
```

## ✅ **Recommended Decision Tree**

```
Current Data Quality Check:
├── NULL Tickers < 10% → Enhance existing data (Phase 1-2)
├── NULL Tickers 10-30% → Enhance existing + Re-import critical missing data  
├── NULL Tickers > 30% → Consider clean slate approach
└── Data Corruption/Alignment Issues → Clean slate approach
```

## 🎯 **Success Metrics Tracking**

Track these before/after metrics:
- **Ticker Extraction Rate**: Current vs Enhanced
- **Amount Parsing Rate**: Current vs Enhanced  
- **Owner Normalization Rate**: Current vs Enhanced
- **Data Completeness**: Overall improvement percentage
- **Processing Performance**: Speed and reliability

## 🔧 **Rollback Plan**

Always have a rollback strategy:
```bash
# If enhancement goes wrong, restore from backup
psql your_db < congressional_trades_backup.sql
```