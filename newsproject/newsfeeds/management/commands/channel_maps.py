from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Channel definitions
# ──────────────────────────────────────────────

@dataclass
class Channel:
    channel_id:       str
    channel_name:     str
    macro_indicators: List[str]
    cis_dimensions:   List[str]
    description:      str

    def to_dict(self) -> dict:
        return {
            "id":               self.channel_id,
            "name":             self.channel_name,
            "macro_indicators": self.macro_indicators,
            "cis_dimensions":   self.cis_dimensions,
            "description":      self.description,
        }


# Complete channel catalogue — 14 channels covering India macro
CHANNELS: Dict[str, Channel] = {

    "trade_competitiveness": Channel(
        channel_id="trade_competitiveness",
        channel_name="Trade competitiveness",
        macro_indicators=["export_growth_pct", "goods_exports_usd",
                          "export_market_share", "trade_weighted_rer"],
        cis_dimensions=["D1", "D2"],
        description="Changes in Indian export price competitiveness vs peers",
    ),

    "current_account": Channel(
        channel_id="current_account",
        channel_name="Current account balance",
        macro_indicators=["cad_gdp_ratio", "trade_deficit_usd",
                          "services_exports", "remittances"],
        cis_dimensions=["D1", "D2"],
        description="Impact on India's external balance and CAD",
    ),

    "inr_exchange_rate": Channel(
        channel_id="inr_exchange_rate",
        channel_name="INR exchange rate",
        macro_indicators=["inr_usd_rate", "reer_index",
                          "forex_reserves", "nifty_defence"],
        cis_dimensions=["D1", "D5"],
        description="Pressure on rupee via flows, sentiment or trade",
    ),

    "imported_inflation": Channel(
        channel_id="imported_inflation",
        channel_name="Imported inflation",
        macro_indicators=["cpi_inflation", "wpi_inflation",
                          "core_cpi", "fuel_inflation"],
        cis_dimensions=["D1", "D3"],
        description="Inflation pass-through from import costs and INR",
    ),

    "food_inflation": Channel(
        channel_id="food_inflation",
        channel_name="Food inflation",
        macro_indicators=["cpi_food", "cereals_inflation",
                          "pulses_inflation", "vegetables_inflation"],
        cis_dimensions=["D1", "D3", "D4"],
        description="Price shocks in domestic food basket",
    ),

    "fiscal_balance": Channel(
        channel_id="fiscal_balance",
        channel_name="Fiscal balance",
        macro_indicators=["fiscal_deficit_gdp", "revenue_deficit",
                          "govt_borrowing", "subsidy_bill"],
        cis_dimensions=["D1", "D5"],
        description="Impact on government revenue, spending and deficit",
    ),

    "monetary_policy": Channel(
        channel_id="monetary_policy",
        channel_name="Monetary policy",
        macro_indicators=["repo_rate", "crr_slr",
                          "liquidity_lafa", "gsec_10yr_yield"],
        cis_dimensions=["D3", "D5"],
        description="RBI response via rates, liquidity, reserve requirements",
    ),

    "capital_flows": Channel(
        channel_id="capital_flows",
        channel_name="Capital flows (FII / FPI)",
        macro_indicators=["fii_equity_flow", "fpi_debt_flow",
                          "fdi_inflow", "ecb_flows"],
        cis_dimensions=["D1", "D2", "D6"],
        description="Portfolio and FDI flows in and out of India",
    ),

    "equity_market": Channel(
        channel_id="equity_market",
        channel_name="Equity market",
        macro_indicators=["sensex", "nifty50",
                          "nifty_bank", "market_cap_gdp"],
        cis_dimensions=["D1", "D6"],
        description="Domestic equity indices and sectoral impact",
    ),

    "bond_market": Channel(
        channel_id="bond_market",
        channel_name="Bond market",
        macro_indicators=["gsec_10yr_yield", "aaa_corporate_spread",
                          "term_structure", "gsec_5yr_yield"],
        cis_dimensions=["D1", "D3"],
        description="Sovereign and corporate bond yields and spreads",
    ),

    "employment_sector": Channel(
        channel_id="employment_sector",
        channel_name="Sectoral employment",
        macro_indicators=["plfs_unemployment", "naukri_jobspeak",
                          "epfo_net_add", "sectoral_employment"],
        cis_dimensions=["D2", "D6"],
        description="Employment impact in affected sectors via orders / output",
    ),

    "commodity_price": Channel(
        channel_id="commodity_price",
        channel_name="Commodity prices",
        macro_indicators=["brent_crude_usd", "gold_price",
                          "industrial_metals_index", "agri_commodity_index"],
        cis_dimensions=["D1", "D2", "D4"],
        description="Direct pass-through from global commodity markets",
    ),

    "supply_chain": Channel(
        channel_id="supply_chain",
        channel_name="Supply chain / logistics",
        macro_indicators=["port_throughput", "freight_index",
                          "inventory_days", "pmi_suppliers"],
        cis_dimensions=["D1", "D4", "D6"],
        description="Logistics disruption, shipping routes, input availability",
    ),

    "sovereign_risk": Channel(
        channel_id="sovereign_risk",
        channel_name="Sovereign risk perception",
        macro_indicators=["cds_5yr_spread", "ems_risk_premium",
                          "india_sovereign_rating", "sdr_spread"],
        cis_dimensions=["D1", "D5", "D6"],
        description="Perceived creditworthiness of India / EM risk premium",
    ),
}


# ──────────────────────────────────────────────
# Lookup table — (event_class, subtype) → channel IDs
# ──────────────────────────────────────────────

# Clean event_class names matching normalized classifications (lowercase, snake_case)
# And clean subtype names matching normalized classifications
CHANNEL_MAP: Dict[Tuple[str, str], List[str]] = {

    # ── trade_policy subtypes ─────────────────
    ("trade_policy", "bilateral_tariff_change"):
        ["trade_competitiveness", "current_account",
         "employment_sector", "inr_exchange_rate"],
    ("trade_policy", "multilateral_tariff_change"):
        ["trade_competitiveness", "current_account",
         "employment_sector"],
    ("trade_policy", "non_tariff_barrier"):
        ["trade_competitiveness", "current_account",
         "supply_chain"],
    ("trade_policy", "export_restriction"):
        ["food_inflation", "imported_inflation",
         "current_account", "trade_competitiveness"],
    ("trade_policy", "trade_agreement"):
        ["trade_competitiveness", "current_account",
         "capital_flows", "employment_sector"],
    ("trade_policy", "anti_dumping_duty"):
        ["trade_competitiveness", "employment_sector",
         "imported_inflation"],
    ("trade_policy", "import_quota_change"):
        ["current_account", "imported_inflation",
         "supply_chain"],
    ("trade_policy", "safeguard_duty"):
        ["trade_competitiveness", "employment_sector",
         "imported_inflation"],
    ("trade_policy", "countervailing_duty"):
        ["trade_competitiveness", "employment_sector"],
    ("trade_policy", "rules_of_origin_change"):
        ["trade_competitiveness", "supply_chain"],

    # ── geopolitical subtypes ─────────────────
    ("geopolitical", "sanctions_imposed"):
        ["commodity_price", "supply_chain",
         "sovereign_risk", "inr_exchange_rate"],
    ("geopolitical", "armed_conflict"):
        ["commodity_price", "capital_flows",
         "sovereign_risk", "inr_exchange_rate"],
    ("geopolitical", "diplomatic_rupture"):
        ["trade_competitiveness", "capital_flows",
         "sovereign_risk"],
    ("geopolitical", "alliance_shift"):
        ["capital_flows", "trade_competitiveness",
         "sovereign_risk"],
    ("geopolitical", "border_dispute"):
        ["sovereign_risk", "fiscal_balance",
         "capital_flows"],
    ("geopolitical", "terrorism_event"):
        ["sovereign_risk", "capital_flows",
         "equity_market"],
    ("geopolitical", "naval_military_exercise"):
        ["sovereign_risk", "commodity_price"],
    ("geopolitical", "diplomatic_expulsion"):
        ["sovereign_risk", "capital_flows"],
    ("geopolitical", "coup_political_instability"):
        ["commodity_price", "sovereign_risk",
         "capital_flows"],
    ("geopolitical", "shipping_lane_disruption"):
        ["supply_chain", "commodity_price",
         "imported_inflation", "current_account"],

    # ── commodity subtypes ────────────────────
    ("commodity", "crude_oil_price_change"):
        ["commodity_price", "imported_inflation",
         "current_account", "fiscal_balance", "inr_exchange_rate"],
    ("commodity", "natural_gas_price_change"):
        ["commodity_price", "imported_inflation",
         "current_account", "fiscal_balance"],
    ("commodity", "food_commodity_surge"):
        ["food_inflation", "commodity_price",
         "current_account", "fiscal_balance"],
    ("commodity", "metal_price_change"):
        ["commodity_price", "employment_sector",
         "current_account"],
    ("commodity", "fertiliser_price_change"):
        ["food_inflation", "fiscal_balance",
         "imported_inflation", "current_account"],
    ("commodity", "critical_mineral_restriction"):
        ["supply_chain", "employment_sector",
         "commodity_price"],
    ("commodity", "supply_cut_opec"):
        ["commodity_price", "imported_inflation",
         "current_account", "inr_exchange_rate"],
    ("commodity", "supply_disruption_weather"):
        ["commodity_price", "food_inflation",
         "supply_chain"],
    ("commodity", "demand_shift_china"):
        ["commodity_price", "trade_competitiveness",
         "capital_flows"],
    ("commodity", "strategic_reserve_action"):
        ["commodity_price", "fiscal_balance",
         "current_account"],

    # ── financial_market subtypes ─────────────
    ("financial_market", "fed_rate_change"):
        ["capital_flows", "inr_exchange_rate",
         "bond_market", "equity_market"],
    ("financial_market", "dollar_movement"):
        ["inr_exchange_rate", "imported_inflation",
         "capital_flows"],
    ("financial_market", "em_capital_flow"):
        ["capital_flows", "inr_exchange_rate",
         "equity_market", "bond_market"],
    ("financial_market", "sovereign_rating_change"):
        ["sovereign_risk", "capital_flows",
         "bond_market", "inr_exchange_rate"],
    ("financial_market", "global_risk_off"):
        ["capital_flows", "inr_exchange_rate",
         "equity_market", "sovereign_risk"],
    ("financial_market", "banking_sector_stress"):
        ["bond_market", "sovereign_risk",
         "capital_flows", "equity_market"],
    ("financial_market", "bond_yield_movement"):
        ["bond_market", "monetary_policy",
         "capital_flows"],
    ("financial_market", "currency_intervention"):
        ["inr_exchange_rate", "monetary_policy",
         "capital_flows"],
    ("financial_market", "equity_market_crash"):
        ["equity_market", "capital_flows",
         "sovereign_risk"],
    ("financial_market", "crypto_market_shock"):
        ["capital_flows", "sovereign_risk"],

    # ── climate_natural subtypes ──────────────
    ("climate_natural", "monsoon_deficit"):
        ["food_inflation", "fiscal_balance",
         "employment_sector"],
    ("climate_natural", "flood_cyclone"):
        ["supply_chain", "fiscal_balance",
         "food_inflation", "employment_sector"],
    ("climate_natural", "el_nino_la_nina"):
        ["food_inflation", "commodity_price",
         "fiscal_balance"],
    ("climate_natural", "global_food_crisis"):
        ["food_inflation", "commodity_price",
         "current_account"],
    ("climate_natural", "drought"):
        ["food_inflation", "fiscal_balance",
         "employment_sector"],
    ("climate_natural", "heat_wave"):
        ["food_inflation", "employment_sector"],
    ("climate_natural", "earthquake"):
        ["supply_chain", "fiscal_balance",
         "employment_sector"],
    ("climate_natural", "crop_damage"):
        ["food_inflation", "fiscal_balance",
         "employment_sector"],
    ("climate_natural", "water_scarcity"):
        ["food_inflation", "fiscal_balance",
         "employment_sector"],
    ("climate_natural", "air_quality_crisis"):
        ["supply_chain", "employment_sector",
         "fiscal_balance"],

    # ── domestic_policy subtypes ──────────────
    ("domestic_policy", "fiscal_stimulus"):
        ["fiscal_balance", "bond_market",
         "employment_sector", "inr_exchange_rate"],
    ("domestic_policy", "rbi_rate_change"):
        ["monetary_policy", "bond_market",
         "inr_exchange_rate", "equity_market"],
    ("domestic_policy", "gst_revision"):
        ["fiscal_balance", "imported_inflation",
         "employment_sector"],
    ("domestic_policy", "pli_industrial_policy"):
        ["employment_sector", "trade_competitiveness",
         "capital_flows", "fiscal_balance"],
    ("domestic_policy", "infrastructure_push"):
        ["fiscal_balance", "employment_sector",
         "bond_market"],
    ("domestic_policy", "regulatory_reform"):
        ["capital_flows", "employment_sector",
         "equity_market"],
    ("domestic_policy", "disinvestment"):
        ["fiscal_balance", "capital_flows",
         "equity_market"],
    ("domestic_policy", "agricultural_policy"):
        ["food_inflation", "fiscal_balance",
         "employment_sector"],
    ("domestic_policy", "trade_promotion_scheme"):
        ["trade_competitiveness", "current_account",
         "employment_sector"],
    ("domestic_policy", "financial_sector_regulation"):
        ["bond_market", "monetary_policy",
         "capital_flows", "equity_market"],
}


# ──────────────────────────────────────────────
# Propagation lag by event class
# ──────────────────────────────────────────────

# How quickly events in each class transmit to Indian macro
PROPAGATION_LAG: Dict[str, str] = {
    "financial_market":  "immediate",    # hours to days
    "commodity":         "short_term",   # days to weeks
    "geopolitical":      "short_term",   # days to weeks
    "trade_policy":      "medium_term",  # weeks to months
    "domestic_policy":   "medium_term",  # weeks to months
    "climate_natural":   "medium_term",  # weeks to months (season-dependent)
}


# ──────────────────────────────────────────────
# Result dataclass
# ──────────────────────────────────────────────

@dataclass
class ChannelMappingResult:
    channels:         List[Dict]
    macro_indicators: List[str]
    cis_dimensions:   List[str]
    propagation_lag:  str
    unmapped_subtypes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "channels":          self.channels,
            "macro_indicators":  self.macro_indicators,
            "cis_dimensions":    self.cis_dimensions,
            "propagation_lag":   self.propagation_lag,
            "unmapped_subtypes": self.unmapped_subtypes,
        }


# ──────────────────────────────────────────────
# Channel mapper class
# ──────────────────────────────────────────────

class ChannelMapper:
    """
    Maps (event_class, subtypes) to transmission channels.
    Pure rule-based — no ML, no training, no external data.
    """

    def __init__(self):
        # Validate that all channel IDs referenced in CHANNEL_MAP exist
        self._validate_map()

    def _validate_map(self) -> None:
        """Check integrity at init time."""
        all_referenced: Set[str] = set()
        for ch_list in CHANNEL_MAP.values():
            all_referenced.update(ch_list)

        missing = all_referenced - set(CHANNELS.keys())
        if missing:
            logger.error("Missing channel definitions: %s", missing)

    # ── Main method ───────────────────────────

    def map(
        self,
        event_class: str,
        subtypes:    List[str],
    ) -> ChannelMappingResult:
        """
        Map an event to its transmission channels.

        Args:
            event_class: e.g. "trade_policy"
            subtypes:    list of subtype strings
                        e.g. ["bilateral_tariff_change"]

        Returns:
            ChannelMappingResult with aggregated channels,
            macro indicators, CIS dimensions, and propagation lag.
        """
        channel_ids: Set[str]        = set()
        unmapped:    List[str]       = []

        # Collect channels from all subtype matches
        for subtype in subtypes:
            key = (event_class, subtype)
            if key in CHANNEL_MAP:
                channel_ids.update(CHANNEL_MAP[key])
            else:
                unmapped.append(subtype)
                logger.warning(
                    "No channel mapping for (%s, %s)",
                    event_class, subtype
                )

        # Build channel objects
        channels: List[Dict]          = []
        macro_indicators: Set[str]    = set()
        cis_dimensions:   Set[str]    = set()

        for ch_id in sorted(channel_ids):
            if ch_id in CHANNELS:
                channel = CHANNELS[ch_id]
                channels.append(channel.to_dict())
                macro_indicators.update(channel.macro_indicators)
                cis_dimensions.update(channel.cis_dimensions)

        return ChannelMappingResult(
            channels=channels,
            macro_indicators=sorted(macro_indicators),
            cis_dimensions=sorted(cis_dimensions),
            propagation_lag=PROPAGATION_LAG.get(event_class, "unknown"),
            unmapped_subtypes=unmapped,
        )

    def map_batch(
        self,
        events: List[Tuple[str, List[str]]],
    ) -> List[ChannelMappingResult]:
        """Batch mapping — input is list of (event_class, subtypes) tuples."""
        return [self.map(ec, st) for ec, st in events]

    # ── Helpers ───────────────────────────────

    def list_channels(self) -> List[str]:
        return list(CHANNELS.keys())

    def list_class_subtype_pairs(self) -> List[Tuple[str, str]]:
        return list(CHANNEL_MAP.keys())

    def coverage_report(self) -> Dict[str, int]:
        """Returns count of mapped (class, subtype) pairs per class."""
        from collections import Counter
        counts = Counter()
        for (cls, _) in CHANNEL_MAP:
            counts[cls] += 1
        return dict(counts)


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(description="Channel mapper CLI")
    sub    = parser.add_subparsers(dest="command")

    mp = sub.add_parser("map", help="Map one event to channels")
    mp.add_argument("event_class", type=str)
    mp.add_argument("subtypes",    type=str,
                    help="Comma-separated subtype list")

    sub.add_parser("list", help="List all defined channels")
    sub.add_parser("coverage", help="Show mapping coverage report")
    sub.add_parser("test", help="Run built-in test cases")

    args   = parser.parse_args()
    mapper = ChannelMapper()

    if args.command == "map":
        subtype_list = [s.strip() for s in args.subtypes.split(",")]
        result       = mapper.map(args.event_class, subtype_list)
        print(json.dumps(result.to_dict(), indent=2))

    elif args.command == "list":
        print(f"\nDefined channels ({len(CHANNELS)}):\n")
        for cid, ch in CHANNELS.items():
            print(f"  {cid:<28} — {ch.channel_name}")

    elif args.command == "coverage":
        report = mapper.coverage_report()
        print("\nMapping coverage per event class:\n")
        for cls, count in sorted(report.items()):
            print(f"  {cls:<20}  {count} subtypes mapped")
        print(f"\nTotal (class, subtype) pairs mapped: {len(CHANNEL_MAP)}")

    elif args.command == "test":
        TEST_CASES = [
            ("trade_policy",     ["bilateral_tariff_change"]),
            ("commodity",        ["crude_oil_price_change", "supply_cut_opec"]),
            ("financial_market", ["fed_rate_change"]),
            ("climate_natural",  ["flood_cyclone", "crop_damage"]),
            ("geopolitical",     ["sanctions_imposed"]),
            ("domestic_policy",  ["rbi_rate_change"]),
        ]

        print("\n" + "=" * 80)
        print("  CHANNEL MAPPER — TEST RESULTS")
        print("=" * 80)

        for i, (ec, st) in enumerate(TEST_CASES, 1):
            result = mapper.map(ec, st)
            print(f"\n[{i}] {ec} / {st}")
            print(f"    Lag        : {result.propagation_lag}")
            print(f"    Channels   : {[c['id'] for c in result.channels]}")
            print(f"    CIS dims   : {result.cis_dimensions}")
            print(f"    Indicators : {result.macro_indicators[:5]}"
                  f"{'...' if len(result.macro_indicators) > 5 else ''}")

        print("\n" + "=" * 80 + "\n")

    else:
        parser.print_help()
