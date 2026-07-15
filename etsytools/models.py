from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class EtsyListing(BaseModel):
    title: str = Field(description="SEO-optimized Etsy listing title, up to 140 characters.")
    description: str = Field(description="Formatted listing description.")
    tags: List[str] = Field(description="Exactly 13 Etsy tags, each 20 characters or fewer.")
    materials: List[str] = Field(description="Up to 5 listing materials.")


class TrendItem(BaseModel):
    id: int
    design: str
    style: str
    trend_score: int
    trend_direction: str


class TrendsResponse(BaseModel):
    trends: list[TrendItem]


class ElementPrompt(BaseModel):
    name: str
    prompt: str


class PromptsResponse(BaseModel):
    elements: list[ElementPrompt]

