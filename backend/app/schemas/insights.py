from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.market import MarketAssetRead


class InsightScore(BaseModel):
    score: int | None = Field(default=None, ge=-10, le=10)
    status: Literal["ready", "not_configured", "unavailable", "error"] = "unavailable"
    summary: str = ""
    model: str | None = None


class OverallInsightScore(BaseModel):
    score: float | None = Field(default=None, ge=-1, le=1)
    status: Literal["ready", "not_configured", "unavailable", "error"] = "unavailable"
    summary: str = ""
    model: str | None = None


class InsightFactor(BaseModel):
    key: str
    label: str
    category: Literal["quant", "financial", "macro", "flow", "earnings"]
    value: float | str | None = None
    unit: str = ""
    observed_at: str | None = None
    period: str | None = None
    source: str = ""
    note: str = ""
    ai: InsightScore = Field(default_factory=InsightScore)


class SentimentInsight(BaseModel):
    title: str = "市场情绪"
    source: str = ""
    available: bool = False
    indicators: list[InsightFactor] = Field(default_factory=list)
    ai: InsightScore = Field(default_factory=InsightScore)


class InsightNews(BaseModel):
    title: str
    subtype: str = ""
    source: str = ""
    publish_time: str = ""
    url: str = ""
    related_securities: list[str] = Field(default_factory=list)


class NewsInsight(BaseModel):
    title: str = "资产相关新闻"
    source: str = "Futu get_search_news"
    available: bool = False
    items: list[InsightNews] = Field(default_factory=list)
    ai: InsightScore = Field(default_factory=InsightScore)


class FactorInsightsRead(BaseModel):
    asset: MarketAssetRead
    start_date: date
    end_date: date
    generated_at: datetime
    factors: list[InsightFactor] = Field(default_factory=list)
    market_sentiment: SentimentInsight = Field(default_factory=SentimentInsight)
    asset_news: NewsInsight = Field(default_factory=NewsInsight)
    overall: OverallInsightScore = Field(default_factory=OverallInsightScore)
    ai_configured: bool = False
    warnings: list[str] = Field(default_factory=list)
