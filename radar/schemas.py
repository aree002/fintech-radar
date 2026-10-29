"""Pydantic models for the radar engine and the API."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Regulator(str, Enum):
    rbi = "RBI"
    sebi = "SEBI"
    meity = "MeitY"
    npci = "NPCI"
    irdai = "IRDAI"
    fiu = "FIU-IND"
    cert_in = "CERT-In"
    other = "Other"


class Impact(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Status(str, Enum):
    notified = "notified"          # in force / issued
    draft = "draft"               # draft rules/directions
    consultation = "consultation"  # consultation / discussion paper
    enforcement = "enforcement"    # penalty / enforcement action


class Source(BaseModel):
    url: str
    title: str | None = None


# ---- What the model returns for one item (structured output) ----
class LLMRadarItem(BaseModel):
    title: str
    regulator: Regulator
    date: str = Field(description="Date of the development, e.g. '2026-09-15' or 'September 2026'")
    status: Status
    sectors: list[str] = Field(description="Sub-sector ids this affects")
    summary: str = Field(description="2-4 plain-language sentences on what changed")
    impact_level: Impact
    affected_entities: list[str] = Field(description="Who must act, e.g. 'NBFC lenders', 'PA/PG'")
    action_items: list[str] = Field(description="Short, concrete steps the affected entity should take")
    source_url: str | None = None
    source_title: str | None = None


class LLMRadar(BaseModel):
    items: list[LLMRadarItem]


# ---- Final, enriched item returned by the API ----
class RadarItem(LLMRadarItem):
    id: str
    client_relevance: str | None = None   # filled when a client profile is supplied
    relevance_score: int = 0              # 0-100 overlap with the client profile


class ClientProfile(BaseModel):
    name: str | None = None
    business_types: list[str] = Field(default_factory=list)  # sector ids
    notes: str | None = None


class ScanRequest(BaseModel):
    sectors: list[str] = Field(default_factory=list)   # empty = all
    lookback_days: int | None = None
    query: str | None = None
    client: ClientProfile | None = None
    web_search: bool | None = None


class RadarResult(BaseModel):
    generated_at: str
    engine: str
    web_search_used: bool
    lookback_days: int
    sectors: list[str]
    query: str | None = None
    items: list[RadarItem]
    sources: list[Source] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
