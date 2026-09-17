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
