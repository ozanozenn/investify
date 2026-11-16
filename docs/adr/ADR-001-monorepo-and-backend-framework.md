# ADR-001: Tek repo, modüler monolit backend

**Durum:** Kabul edildi · 2026-08-17 · gözden geçirildi 2026-10-27

## Bağlam
Tek kullanıcı, tek geliştirici. Yol haritası motorları (finansal, skor,
değerleme) ayrı paketler olarak öneriyor ama ayrı paketlerin bakım yükü bu
ölçekte hiçbir şey kazandırmıyor.

## Karar
- Tek repo, iki uygulama: `apps/api` (FastAPI) ve `apps/web` (Next.js).
- Backend tek Python paketi, içi katmanlı. İçe aktarma yönü tek yönlü:
  `api/routers → services → {providers, *_engine, llm} → models/schemas`.
- `*_engine/` modülleri (financial, scoring, valuation, verdict) **saf
  fonksiyon**: I/O yok, `providers` veya `llm` içe aktarmaz.
- `llm/` veritabanına erişmez; yalnızca `schemas` alır.
- Refresh, HTTP isteğinin içinde senkron çalışır; kuyruk (Celery vb.) yok.
- Stack: FastAPI + Pydantic v2 + SQLAlchemy 2 (async) + Alembic + PostgreSQL.

## Alternatifler
- **Motorlar ayrı paket (`packages/*`)** — tek tüketici varken sadece
  sürümleme yükü getirir. Kural zaten "yukarı import yok" olduğu için
  ileride ayırmak dosya taşımaktan ibaret.
- **Arka plan kuyruğu** — tek kullanıcı, refresh birkaç saniye. Zamanlanmış
  refresh veya izleme listesi gelince gerekecek.

## Sonuçlar
- Motorlar kolay test edilir ve gerekirse paket olarak ayrılabilir.
- Katman kuralı araçla değil review ile korunuyor.
- Redis yalnızca hafif önbellek: sayfa açılışındaki güncel fiyat
  (`GET /api/companies/{ticker}/quote`) `services/cache.py` ile
  önbelleklenir (TTL `QUOTE_CACHE_TTL_SECONDS`, varsayılan 60 sn). Redis'e
  ulaşılamazsa bir kez uyarı loglanır, önbelleksiz devam edilir — hiçbir
  istek önbellek yüzünden başarısız olmaz.
