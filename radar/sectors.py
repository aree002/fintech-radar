"""Fintech sub-sector definitions.

These drive the UI filters, the client-profile picker, and the sector tags on
each regulatory item. Kept in one place so the taxonomy is consistent.
"""
from __future__ import annotations

# ordered: most active areas first
SECTORS: dict[str, dict[str, str]] = {
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
    "insurtech": {
        "label": "InsurTech",
        "regulator": "IRDAI",
        "blurb": "Digital insurance distribution and web aggregators.",
    },
    "wealthtech_sebi": {
        "label": "WealthTech / Securities",
        "regulator": "SEBI",
        "blurb": "Investment platforms, advisers, finfluencer rules.",
    },
    "cross_border_fema": {
        "label": "Cross-border / FEMA",
        "regulator": "RBI",
        "blurb": "Cross-border payments, PA-CB, FEMA compliance.",
    },
    "data_protection": {
        "label": "Data Protection (DPDP)",
        "regulator": "MeitY",
        "blurb": "DPDP Act and Rules obligations for data fiduciaries.",
    },
}

VALID_SECTORS = set(SECTORS.keys())


def label_for(sector: str) -> str:
    return SECTORS.get(sector, {}).get("label", sector.replace("_", " ").title())


def sectors_payload() -> list[dict[str, str]]:
    return [{"id": sid, **meta} for sid, meta in SECTORS.items()]
