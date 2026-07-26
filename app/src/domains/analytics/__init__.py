"""
Analytics domain package for CapitolScope.

Signals, backfills, and analytical engines built on top of the congressional,
securities, and market_data domains. Submodules are imported directly (e.g.
``from domains.analytics.backfill_securities import ...``); this package
intentionally does not eagerly import submodules so partially-built pieces
never break unrelated imports.
"""
