from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: dt.datetime


class NewsResult(BaseModel):
    ticker: str
    items: list[NewsItem]


class MarketNewsResult(BaseModel):
    items: list[NewsItem]


class MarketDisclosureItem(BaseModel):
    ticker: str | None
    company_name: str
    title: str
    subject: str | None
    category: str
    published_at: dt.datetime
    source_url: str


class MarketDisclosureResult(BaseModel):
    items: list[MarketDisclosureItem]
