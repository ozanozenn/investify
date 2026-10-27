# ADR-006: Python sürümü

**Durum:** Kabul edildi · 2026-09-17 · sadeleştirildi 2026-10-12

## Bağlam
Docker imajı ile geliştiricinin makinesindeki Python sürümü farklı olabiliyor.

## Karar
- Docker (kayıt sürümü): Python **3.12** (`apps/api/Dockerfile`).
- Yerel geliştirme: **3.11** kabul edilir; hiçbir bağımlılık 3.12'ye özgü
  özellik kullanmıyor.
- `greenlet` doğrudan bağımlılık olarak yazılır (SQLAlchemy async ister,
  dolaylı gelmesine güvenilmez).
- Docker yoksa testler SQLite ile koşar; bağımlılık veya migration değiştiren
  işler en az bir kez `docker compose up -d --build` ile denenir.

## Alternatifler
- **Her yerde tam 3.12 zorunluluğu** — her makineye belirli sürüm kurdurmak,
  karşılığında bir şey kazandırmıyor.

## Sonuçlar
- Bir bağımlılık 3.12 gerektirirse bu ADR değişir.
