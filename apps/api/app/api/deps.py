from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.services.provider_bundle import ProviderBundle, get_provider_bundle


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def get_providers() -> ProviderBundle:
    return get_provider_bundle()
