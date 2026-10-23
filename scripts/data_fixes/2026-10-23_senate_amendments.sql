-- Senate amended PTRs were imported as new filings dated the day of the
-- amendment, so on-time trades looked years late (e.g. Tuberville INTC
-- "820 days") and unchanged trades were stored twice.
--
-- Map: 2026-10-23_senate_amendments.csv (doc_id, original filing date),
-- built from data/congress/raw/senate/search_*.json.
-- Backup of the 207 affected rows (taken before any change):
--   /mnt/hermes/backups/capitolscope/amend_rows_backup_2026-10-23.csv
--
-- Run (dry run by default; edit the last line to COMMIT to apply):
--   docker cp scripts/data_fixes/2026-10-23_senate_amendments.csv capitolscope-postgres:/tmp/amend_map.csv
--   docker exec -i capitolscope-postgres psql -U capitolscope -d capitolscope -v ON_ERROR_STOP=1 \
--     < scripts/data_fixes/2026-10-23_senate_amendments.sql

begin;
create temp table am(doc_id text, orig date);
\copy am from '/tmp/amend_map.csv' csv

-- 1) Amendment rows that only repeat a trade already stored from another
--    filing (expected: 47, none referenced by notifications/discussions).
create temp table dup as
select t.id from congressional_trades t join am using (doc_id)
where exists (
  select 1 from congressional_trades o
  where o.member_id = t.member_id and o.doc_id <> t.doc_id
    and o.transaction_date = t.transaction_date
    and o.transaction_type = t.transaction_type
    and o.amount_min is not distinct from t.amount_min
    and (case when coalesce(t.ticker, '') <> '' then o.ticker = t.ticker
              else o.raw_asset_description = t.raw_asset_description end)
);
select count(*) as duplicates_to_delete from dup;
delete from congressional_trades where id in (select id from dup);

-- 2) Remaining amendment rows: mark as amendments and use the original
--    filing date as the disclosure date (expected: 160 rows).
update congressional_trades t
set filing_status = 'A', notification_date = am.orig, updated_at = now()
from am where am.doc_id = t.doc_id;

select count(*) as amendment_rows_kept,
       count(*) filter (where notification_date - transaction_date > 45) as still_late
from congressional_trades t join am using (doc_id);

rollback;  -- change to COMMIT to apply
