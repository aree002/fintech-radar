"""Illustrative sample dataset for the offline engine.

These items are representative of real Indian fintech regulatory themes, written
so the dashboard is fully populated without any API key or network access. They
are labelled as sample data in the UI. A live scan replaces these with current
items found by real-time web search.
"""
from __future__ import annotations

from .schemas import LLMRadarItem

SAMPLE_ITEMS: list[LLMRadarItem] = [
    LLMRadarItem(
        title="Consolidated Digital Lending Directions",
        regulator="RBI",
        date="2026-05-08",
        status="notified",
        sectors=["digital_lending"],
        summary=(
            "RBI consolidated its digital lending norms into a single set of "
            "directions covering regulated entities and the lending service "
            "providers they work with. It restates the Key Fact Statement (KFS) "
            "requirement, the all-inclusive APR disclosure, the cooling-off "
            "period, and limits on data collection by lending apps."
        ),
        impact_level="high",
        affected_entities=["Banks", "NBFC lenders", "Lending Service Providers", "Digital lending apps"],
        action_items=[
            "Issue a KFS to every borrower before disbursal, with the all-in APR.",
            "Provide a cooling-off / look-up period to exit without penalty.",
            "Limit app data collection to what is needed; no access to contacts, media or location logs.",
            "Name a grievance redressal officer and publish the escalation path.",
        ],
        source_url="https://www.rbi.org.in",
        source_title="Reserve Bank of India",
    ),
    LLMRadarItem(
        title="Default Loss Guarantee (DLG / FLDG) capped at 5%",
        regulator="RBI",
        date="2026-04-22",
        status="notified",
        sectors=["digital_lending", "p2p_lending"],
        summary=(
            "RBI reaffirmed that default loss guarantee arrangements between a "
            "regulated lender and a lending service provider cannot exceed 5% of "
            "the underlying loan portfolio, and must be backed by permitted forms "
            "of security and clear documentation."
        ),
        impact_level="high",
        affected_entities=["NBFC lenders", "Lending Service Providers offering DLG"],
        action_items=[
            "Cap any DLG arrangement at 5% of the covered portfolio.",
            "Document the arrangement and the form of security used.",
            "Avoid using DLG to mask evergreening or to bypass provisioning norms.",
        ],
        source_url="https://www.rbi.org.in",
        source_title="Reserve Bank of India",
    ),
    LLMRadarItem(
        title="Payment Aggregator framework extended to offline PAs",
        regulator="RBI",
        date="2026-03-14",
        status="notified",
        sectors=["payment_aggregator"],
        summary=(
            "RBI extended the payment aggregator framework to physical, "
            "point-of-sale aggregators and tightened merchant onboarding and KYC "
            "expectations. Authorisation, net worth and escrow requirements apply "
            "to offline PAs on the same footing as online ones."
        ),
        impact_level="high",
        affected_entities=["Payment Aggregators", "Payment Gateways", "Offline PAs"],
        action_items=[
            "Confirm authorisation status and the applicable net-worth timeline.",
            "Route funds through the prescribed escrow mechanism.",
            "Run merchant due diligence and KYC per the updated expectations.",
        ],
        source_url="https://www.rbi.org.in",
        source_title="Reserve Bank of India",
    ),
    LLMRadarItem(
        title="DPDP Rules notified",
        regulator="MeitY",
        date="2026-02-20",
        status="notified",
        sectors=["data_protection"],
        summary=(
            "The rules under the Digital Personal Data Protection Act were "
            "notified, operationalising consent notices, the rights of data "
            "principals, security safeguards, breach reporting timelines and "
            "additional obligations for significant data fiduciaries."
        ),
        impact_level="high",
        affected_entities=["All data fiduciaries", "Fintech apps handling personal data"],
        action_items=[
            "Publish a clear, itemised consent notice and capture consent properly.",
            "Build a process for data-principal rights (access, correction, erasure).",
            "Set up breach detection and reporting within the prescribed timeline.",
            "Assess whether you are a significant data fiduciary and appoint a DPO if so.",
        ],
        source_url="https://www.meity.gov.in",
        source_title="Ministry of Electronics and IT",
    ),
    LLMRadarItem(
        title="PPI interoperability and full-KYC wallet norms updated",
        regulator="RBI",
        date="2026-01-30",
        status="notified",
        sectors=["ppi_wallets", "upi"],
        summary=(
            "RBI updated the prepaid payment instrument directions to push "
            "interoperability through UPI for full-KYC wallets and to clarify "
            "loading and cash-out limits."
        ),
        impact_level="medium",
        affected_entities=["PPI issuers", "Wallet providers"],
        action_items=[
            "Enable UPI interoperability for full-KYC wallets.",
            "Review loading and cash-out limits against the updated thresholds.",
        ],
        source_url="https://www.rbi.org.in",
        source_title="Reserve Bank of India",
    ),
    LLMRadarItem(
        title="Credit line on UPI onboarding guidance",
        regulator="NPCI",
        date="2026-06-11",
        status="notified",
        sectors=["upi", "digital_lending"],
        summary=(
            "NPCI issued onboarding guidance for offering pre-sanctioned credit "
            "lines through UPI, covering consent, disclosure of terms at the point "
            "of transaction, and settlement responsibilities between the bank and "
            "the app."
        ),
        impact_level="medium",
        affected_entities=["UPI apps (TPAPs)", "Banks offering credit on UPI"],
        action_items=[
            "Disclose credit-line terms clearly at the point of transaction.",
            "Capture explicit consent before enabling a credit line.",
        ],
        source_url="https://www.npci.org.in",
        source_title="National Payments Corporation of India",
    ),
    LLMRadarItem(
        title="Finfluencer association restrictions for registered intermediaries",
        regulator="SEBI",
        date="2026-07-02",
        status="notified",
        sectors=["wealthtech_sebi"],
        summary=(
            "SEBI restricted registered intermediaries and their agents from "
            "associating with unregistered finfluencers who give securities "
            "advice or make performance claims, with limited carve-outs for "
            "investor-education content."
        ),
        impact_level="medium",
        affected_entities=["Investment platforms", "Registered Investment Advisers", "Brokers"],
        action_items=[
            "Review marketing tie-ups with finfluencers for prohibited association.",
            "Separate genuine investor-education content from advice or return claims.",
        ],
        source_url="https://www.sebi.gov.in",
        source_title="Securities and Exchange Board of India",
    ),
    LLMRadarItem(
        title="VDA service providers reminded of FIU-IND registration and AML duties",
        regulator="FIU-IND",
        date="2026-08-19",
        status="enforcement",
        sectors=["crypto_vda", "kyc_aml"],
        summary=(
            "FIU-IND reiterated that virtual digital asset service providers "
            "operating in India must register as reporting entities and maintain "
            "an AML/CFT programme, following action against non-compliant offshore "
            "platforms."
        ),
        impact_level="medium",
        affected_entities=["Crypto exchanges", "VDA service providers"],
        action_items=[
            "Register with FIU-IND as a reporting entity if serving Indian users.",
            "Run a full AML/CFT programme, including suspicious transaction reporting.",
        ],
        source_url="https://fiuindia.gov.in",
        source_title="Financial Intelligence Unit - India",
    ),
    LLMRadarItem(
        title="Account Aggregator consent framework refinements",
        regulator="RBI",
        date="2026-05-27",
        status="notified",
        sectors=["account_aggregator"],
        summary=(
            "RBI refined the account aggregator consent architecture, tightening "
            "purpose specification, consent validity and the handling of financial "
            "information by information users."
        ),
        impact_level="low",
        affected_entities=["Account Aggregators", "Financial Information Users"],
        action_items=[
            "Specify purpose precisely in each consent request.",
            "Honour consent validity and data-use limits.",
        ],
        source_url="https://www.rbi.org.in",
        source_title="Reserve Bank of India",
    ),
]
