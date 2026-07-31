"""
Curated historical / rename alias map for congressional-trade name resolution.

Universe validation and normalized-name matching (``universe.py`` +
``name_matching.py``) recover most tickers, but two cases they cannot handle on
their own:

  1. **Renames** where the *name itself* changed, so neither the old name nor the
     old ticker appears under the new listing (e.g. "Priceline Group" -> BKNG,
     "Dominion Resources" -> D, "Anthem" -> ELV).
  2. **Ticker reuse / mangled source text** where normalized matching would
     resolve to the wrong or no symbol (e.g. the "S&P" parsing loss that turns
     "SPDR S&P 500" into "spdr and 500").

Each entry maps a *normalized* company name (the output of
``name_matching.normalize_company_name``) to a ticker. For companies that
continue as a going concern under a new symbol we point at the **current**
ticker (price history is continuous); for companies that were fully acquired and
ceased trading we point at their own **delisted** ticker (its price history up to
the acquisition is what a trade-date return needs).

Targets are validated against the active+delisted universe at load time (see
``build_alias_index``); any alias whose ticker is not in the universe is dropped
with a warning so a typo here can never seed a bogus security.
"""

from __future__ import annotations

import logging
from typing import Dict, Set

from domains.securities.name_matching import normalize_company_name

logger = logging.getLogger(__name__)

# Raw curated aliases: human-readable company name -> ticker.
# Keys are normalized on load, so write them naturally (case/suffix don't matter).
_RAW_ALIASES: Dict[str, str] = {
    # -- Renames: company continues under a new ticker (point at current symbol) --
    "Dominion Resources": "D",
    "Raytheon Technologies": "RTX",
    "Priceline Group": "BKNG",
    "Coach": "TPR",                      # -> Tapestry (2017)
    "Anthem": "ELV",                     # -> Elevance Health (2022)
    "WellPoint": "ELV",
    "Blackstone Group": "BX",
    "Facebook": "META",
    "Google": "GOOGL",
    "Kraft Foods Group": "KHC",
    "Kraft Heinz": "KHC",
    "L Brands": "BBWI",                  # -> Bath & Body Works (2021)
    "Under Armour": "UAA",
    "Andeavor": "MPC",                   # merged into Marathon Petroleum (2018)
    "DowDuPont": "DD",
    "Fiat Chrysler Automobiles": "STLA", # -> Stellantis (2021)
    "Peloton": "PTON",
    "Square": "XYZ",                     # Square/Block -> ticker changed SQ->XYZ (2025)
    "Block": "XYZ",

    # -- Acquisitions / full delistings: point at the company's own dead ticker --
    "Twitter": "TWTR",
    "Celgene": "CELG",
    "United Technologies": "UTX",        # merged with Raytheon -> RTX (2020)
    "Express Scripts Holding": "ESRX",
    "Express Scripts": "ESRX",
    "Pioneer Natural Resources": "PXD",
    "Red Hat": "RHT",
    "Allergan": "AGN",
    "Activision Blizzard": "ATVI",
    "SanDisk": "SNDK",
    "Tyco International": "TYC",
    "China Mobile": "CHL",               # delisted from NYSE (2021)
    "Frontier Communications": "FTR",
    "WestRock": "WRK",                   # merged -> Smurfit WestRock (2024)
    "Splunk": "SPLK",                    # acquired by Cisco (2024)
    "Vivint Solar": "VSLR",
    "Cabot Oil & Gas": "COG",            # -> Coterra (CTRA, 2021)
    "Xilinx": "XLNX",                    # acquired by AMD (2022)
    "Maxim Integrated Products": "MXIM",
    "Alexion Pharmaceuticals": "ALXN",   # acquired by AstraZeneca (2021)
    "Cypress Semiconductor": "CY",
    "Time Warner": "TWX",
    "DuPont E I De Nemours": "DD",
    "Rowan": "RDC",
    "Andeavor Logistics": "ANDX",

    # -- SPAC -> operating company (pre-merger name -> successor ticker) --
    "Diamond Eagle Acquisition": "DKNG",

    # -- Parsing artifacts (upstream "S&P" -> "S" dropped => "and") --
    "SPDR and 500": "SPY",
    "ProShares Short and P500": "SH",
    "iShares and 500 Value": "IVE",
    "Vanguard and 500": "VOO",

    # -- Renames where the listing name no longer shares a token with the old
    #    name (so name/containment matching can't bridge them) --
    "Schlumberger": "SLB",               # listing is now "SLB Limited"
    "GlaxoSmithKline": "GSK",            # listing is now "GSK plc"
    "Northwest Natural Gas": "NWN",      # -> Northwest Natural Holding
    "E I du Pont de Nemours": "DD",
    "British American Tobacco Industries": "BTI",
    "British American Tobacco": "BTI",

    # -- More renames -> current active ticker (company continues) --
    "Sempra Energy": "SRE",              # listing is now just "Sempra"
    "Acuity Brands": "AYI",              # -> Acuity Inc.
    "AmerisourceBergen": "COR",          # -> Cencora
    "National Oilwell Varco": "NOV",     # -> NOV Inc.
    "KLA Tencor": "KLAC",                # -> KLA Corporation
    "ViacomCBS": "PARA",                 # common -> Paramount Global
    "Alliance Data Systems": "BFH",      # -> Bread Financial

    # -- Acquisitions -> own delisted ticker (verified not reused by an active co) --
    "Catamaran": "CTRX",                 # acquired by UnitedHealth (2015)

    # -- Foreign ADRs whose terse OTC listing name ("ROCHE HLDG AG S/ADR") blocks
    #    an automatic name match. Targets validated against the OTC universe. --
    "Roche Holdings": "RHHBY",
    "Roche Holding": "RHHBY",
    "Bayer": "BAYRY",
    "Bayer Aktiengesellschaft": "BAYRY",
    "Tencent Holdings": "TCEHY",
    "LVMH Moet Hennessy Louis Vuitton": "LVMUY",
    "LVMH Moet Hennessy Louis": "LVMUY",
    "Murata Manufacturing": "MRAAY",
    "Fanuc": "FANUY",
    "Chugai Pharmaceutical": "CHGCY",
    "Royal DSM": "RDSMY",
    "Mitsubishi Estate": "MITEY",
    "Societe Generale": "SCGLY",
    "Nestle": "NSRGY",
    "Roche Holdings Basel": "RHHBY",

    # -- Long-tail US renames / delisted (verified against the universe) --
    "Trimble Navigation": "TRMB",
    "Towers Watson": "WTW",
    "Willis Towers Watson": "WTW",
    "Newell Rubbermaid": "NWL",
    "International Flavors and Fragrances": "IFF",
    "Internationa Flavors and Fragrances": "IFF",   # source typo
    "Molson Coors Brewing": "TAP",
    "F5 Networks": "FFIV",
    "Polaris Industries": "PII",
    "Boston Properties": "BXP",
    "Charter Communications": "CHTR",
    "Vistra Energy": "VST",
    "Wisconsin Energy": "WEC",
    "NortonLifeLock": "GEN",
    "DaVita Healthcare Partners": "DVA",
    "BancorpSouth": "BXS",
    "BancorpSouth Bank": "BXS",
    "Blackstone Group": "BX",
    "Celanese US Holdings": "CE",
    "Sunoco": "SUN",
    "Energy Transfer Partners": "ET",
    "MarkWest Energy": "MWE",
    "MarkWest Energy Partners": "MWE",
    "Plains Group Holdings": "PAGP",
    "Plains GP Holdings": "PAGP",
    "KapStone Paper and Packaging": "KS",
    "Zayo Group": "ZAYO",
    "Zayo Group Holdings": "ZAYO",
    "Regal Beloit": "RRX",
    "Canadian Pacific Railway": "CP",
    "Shire": "SHPG",
    "Wright Medical Group": "WMGI",
    "PetSmart": "PETM",
    "Fresh Market": "TFM",
    "Level 3 Communications": "LVLT",
    "New York Community Bancorp": "NYCB",
    "Regal Beloit Corporation": "RRX",
    "Bank Nova Scotia Halifax": "BNS",
    "Bank of Nova Scotia": "BNS",

    # -- More foreign ADRs (OTC/listed), each verified name==company --
    "Ambev": "ABEV",
    "SoftBank": "SFTBY",
    "SoftBank Group": "SFTBY",
    "Astellas Pharma": "ALPMY",
    "Komatsu": "KMTUY",
    "Shionogi": "SGIOY",
    "Itau Unibanco": "ITUB",
    "Itau Unibanco Banco Holding": "ITUB",
    "Mazda Motor": "MZDAY",
    "Shiseido": "SSDOY",
    "Atlas Copco": "ATLCY",
    "Atlas Copco AB": "ATLCY",
    "Kering": "PPRUY",
    "Denso": "DNZOY",
    "DBS Group Holdings": "DBSDY",
    "Seven and I Holdings": "SVNDY",
    "Suntory Beverage and Food": "STBFY",
    "Seiko Epson": "SEKEY",
    "Seiko Epson Suwa": "SEKEY",
    "Temenos Group": "TMSNY",
    "Epiroc": "EPOAY",
    "Epiroc Aktiebolag": "EPOAY",
    "Total": "TTE",
    "TotalEnergies": "TTE",
    "Royal Dutch Shell": "SHEL",
    "Royal Dutch Shell Royal Dutch": "SHEL",

    # -- Name variants that miss an exact normalized match --
    "Fidelity National Information": "FIS",  # source drops "Services"
    "Fidelity National Information Services": "FIS",
}


def build_alias_index(universe: Set[str]) -> Dict[str, str]:
    """Normalize keys and drop any alias whose target is not in the universe.

    Returns {normalized_name: ticker}. Dropped aliases are logged so a stale
    entry surfaces instead of silently seeding a wrong security.
    """
    index: Dict[str, str] = {}
    dropped = []
    for raw_name, ticker in _RAW_ALIASES.items():
        key = normalize_company_name(raw_name)
        symbol = ticker.strip().upper()
        if not key:
            continue
        if symbol not in universe:
            dropped.append((raw_name, symbol))
            continue
        index[key] = symbol
    if dropped:
        logger.warning(
            "historical_aliases: %d alias target(s) not in universe, dropped: %s",
            len(dropped), dropped,
        )
    logger.info("historical_aliases: %d active aliases", len(index))
    return index


def resolve_ticker_by_alias(normalized_name: str, alias_index: Dict[str, str]) -> str | None:
    """Return the aliased ticker for a pre-normalized company name, or None."""
    if not normalized_name:
        return None
    return alias_index.get(normalized_name)
