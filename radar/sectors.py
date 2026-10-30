"""Regulatory category definitions (RBI + SEBI remit).

These drive the UI filters, the client-profile picker, and the category tags on
each regulatory item. Kept in one place so the taxonomy is consistent. The list
spans financial regulation broadly, not just fintech, since the radar pulls from
RBI and SEBI's full feeds.
"""
from __future__ import annotations

# Grouped loosely: banking/RBI first, then payments & fintech, then SEBI/markets.
SECTORS: dict[str, dict[str, str]] = {
    # ---- Banking & RBI prudential ----
    "banking": {
        "label": "Banking & Prudential",
        "regulator": "RBI",
        "blurb": "Banks, capital and prudential norms, licensing, governance.",
    },
    "nbfc": {
        "label": "NBFCs",
        "regulator": "RBI",
        "blurb": "Non-banking finance companies, scale-based regulation.",
    },
    "monetary_markets": {
        "label": "Monetary & Markets (RBI)",
        "regulator": "RBI",
        "blurb": "Monetary policy, liquidity, G-secs, money and forex markets.",
    },
    # ---- Payments & fintech ----
    "digital_lending": {
        "label": "Digital Lending",
        "regulator": "RBI",
        "blurb": "App-based and online lending, LSPs, loan service providers.",
    },
    "payment_aggregator": {
        "label": "Payment Aggregators / Gateways",
        "regulator": "RBI",
        "blurb": "PA/PG authorisation, escrow, merchant onboarding.",
    },
    "ppi_wallets": {
        "label": "Prepaid Instruments (Wallets)",
        "regulator": "RBI",
        "blurb": "PPI issuers, wallet KYC, interoperability.",
    },
    "upi": {
        "label": "UPI / Payments",
        "regulator": "NPCI / RBI",
        "blurb": "UPI apps, TPAPs, credit on UPI, volume caps.",
    },
    "account_aggregator": {
        "label": "Account Aggregator",
        "regulator": "RBI",
        "blurb": "AAs, financial information providers and users, consent.",
    },
    "p2p_lending": {
        "label": "P2P Lending",
        "regulator": "RBI",
        "blurb": "NBFC-P2P platforms and their lending conduct.",
    },
    "kyc_aml": {
        "label": "KYC / AML",
        "regulator": "RBI / FIU-IND",
        "blurb": "Customer due diligence, video KYC, PMLA obligations.",
    },
    "crypto_vda": {
        "label": "Crypto / Virtual Digital Assets",
        "regulator": "FIU-IND / RBI",
        "blurb": "VDA service providers, exchange AML, registration.",
    },
    "cross_border_fema": {
        "label": "Cross-border / FEMA",
        "regulator": "RBI",
        "blurb": "Cross-border payments, PA-CB, FEMA compliance.",
    },
    # ---- SEBI / capital markets ----
    "securities_markets": {
        "label": "Securities Markets (SEBI)",
        "regulator": "SEBI",
        "blurb": "General market regulation, trading, settlement, surveillance.",
    },
    "listed_companies": {
        "label": "Listed Companies / LODR",
        "regulator": "SEBI",
        "blurb": "Listing obligations, disclosures, takeovers, insider trading.",
    },
    "mutual_funds": {
        "label": "Mutual Funds",
        "regulator": "SEBI",
        "blurb": "AMCs, scheme rules, distribution, valuation.",
    },
    "market_intermediaries": {
        "label": "Market Intermediaries",
        "regulator": "SEBI",
        "blurb": "Brokers, RAs, investment advisers, custodians, RTAs.",
    },
    "fpi_foreign_investment": {
        "label": "FPIs / Foreign Investment",
        "regulator": "SEBI",
        "blurb": "Foreign portfolio investors, registration, KYC, limits.",
    },
    "reits_invits": {
        "label": "REITs / InvITs",
        "regulator": "SEBI",
        "blurb": "Real estate and infrastructure investment trusts.",
    },
    "wealthtech_sebi": {
        "label": "WealthTech / Advisers",
        "regulator": "SEBI",
        "blurb": "Investment platforms, advisers, finfluencer rules.",
    },
    # ---- Cross-cutting ----
    "data_protection": {
        "label": "Data Protection (DPDP)",
        "regulator": "MeitY",
        "blurb": "DPDP Act and Rules obligations for data fiduciaries.",
    },
    "enforcement": {
        "label": "Enforcement & Penalties",
        "regulator": "RBI / SEBI",
        "blurb": "Adjudication orders, penalties, directions against entities.",
    },
}

VALID_SECTORS = set(SECTORS.keys())


def label_for(sector: str) -> str:
    return SECTORS.get(sector, {}).get("label", sector.replace("_", " ").title())


def sectors_payload() -> list[dict[str, str]]:
    return [{"id": sid, **meta} for sid, meta in SECTORS.items()]
