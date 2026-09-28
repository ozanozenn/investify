from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class RateDecisionEvent(BaseModel):
    date: dt.date


class CompanyEvent(BaseModel):
    ticker: str | None
    company_name: str
    category: str
    title: str
    announced_at: dt.datetime
    source_url: str


class CalendarResult(BaseModel):
    rate_decisions: list[RateDecisionEvent]
    company_events: list[CompanyEvent]
