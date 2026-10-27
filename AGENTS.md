# Investify — Agent Rehberi

> Bu dosya araçtan bağımsız ana kaynaktır (Claude Code, Codex vb. hepsi okur).
> Kısa tut: her satır her oturumda bağlama yüklenir. Detay → docs/

## Proje
Investify — Borsa İstanbul (BIST) şirketleri için kanıta dayalı, izlenebilir
yatırım araştırma platformu. Akış: gerçek piyasa/finansal/KAP/makro veri →
deterministik metrik/değerleme/skor → LLM yorumu (asla hesaplama yapmaz) →
versiyonlu, değişmez analiz anlık görüntüsü (`AnalysisSnapshot`). Tek
kullanıcılı. AL/TUT/SAT sinyali **yalnızca demo** olarak, deterministik hüküm
motorundan gelir ve tek ayarla kapanır (ADR-011); LLM asla sinyal vermez.

## Stack
FastAPI + SQLAlchemy 2.0 (async) + Alembic + PostgreSQL (`apps/api`) ·
Next.js 15 (App Router) + React 19 + TypeScript + Tailwind (`apps/web`) ·
Docker Compose orkestrasyon · Redis (güncel fiyat önbelleği; erişilemezse önbelleksiz çalışır).

## Komutlar
| Amaç        | Komut              |
|-------------|--------------------|
| Kurulum (api) | `cd apps/api && python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"` |
| Kurulum (web) | `cd apps/web && npm install` |
| Geliştirme (tam) | `docker compose up -d --build` |
| Geliştirme (api) | `cd apps/api && .venv/bin/uvicorn app.main:app --reload` |
| Geliştirme (web) | `cd apps/web && npm run dev` |
| Test (api)  | `cd apps/api && .venv/bin/pytest tests/ -q` |
| Tek test (api) | `cd apps/api && .venv/bin/pytest tests/unit/test_x.py::test_adı -v` |
| Test (web)  | yok — bkz. `docs/adr/ADR-010-test-strategy-and-repo-structure.md` |
| Lint+tip (api) | `cd apps/api && .venv/bin/ruff check .` |
| Lint+tip (web) | `cd apps/web && npm run lint && npm run typecheck` |
| Build (web) | `cd apps/web && npm run build` |

## Mimari haritası
<!-- Klasör → sorumluluk. Sadece üst seviye; detay docs/ARCHITECTURE.md -->
- `apps/api/app/` — backend; import yönü `routers → services → {providers,
  financial_engine, scoring_engine, valuation_engine, verdict_engine, llm} → models`
  (ADR-001). Motorlar (`*_engine/`) saf fonksiyonlardır, I/O yapmaz.
- `apps/web/app/`, `apps/web/components/` — Next.js App Router sayfaları ve
  bileşenler; frontend asla finansal hesaplama yapmaz, API yanıtını olduğu
  gibi gösterir.
- `apps/api/config/*.yaml` — skorlama ağırlıkları, DCF varsayımları, TCMB
  takvimi gibi versiyon kontrollü, secret olmayan ayarlar.
- `docs/adr/` — mimari kararlar (`ADR-NNN-*.md`, bkz. Dokümantasyon haritası).

## Konvansiyonlar
<!-- Sadece Claude'un tahmin edemeyeceği, projeye özgü kurallar -->
- **Tüm kullanıcıya dönük çıktı Türkçe** — UI metinleri, LLM analiz çıktısı,
  hata mesajları. Yeni özellikler ilk taslaktan itibaren Türkçe yazılır,
  sonradan çevrilmez. ADR'ler de Türkçe ve kısa (şablon: `/adr` skill'i).
- **LLM asla hesaplama yapmaz** (ADR-003) — her sayı deterministik
  motorlardan gelir; context'e girmeden önce insan-okunur Türkçe formatlanır
  (`llm/number_format.py`, `llm/context_formatter.py`); LLM bu biçimi aynen
  korur, kendi başına yeniden yuvarlamaz.
- **"Asla tahmin etme" disiplini** — eksik veri `missing_fields` ile
  işaretlenir, makul görünen bir değerle doldurulmaz. Sağlayıcı hataları
  `ProviderUnavailableError` ile yakalanıp aşamalı bozulmaya çevrilir.
- **`AnalysisSnapshot` değişmezdir** (ADR-005) — kaydedildikten sonra
  güncellenmez; yeni refresh yeni bir snapshot oluşturur.
- **Finansal hesaplamalarda native `float` kullanılır**, `Decimal` değil —
  bilinçli bir basitlik tercihi (muhasebe-hassasiyetinde bir sistem değiliz).
- **Prompt versiyonlama dosya adıyla yapılır** (`company-analysis-vN.md`) —
  çıktının *ne istediği* değişince versiyon atlanır, eskisi silinmez.
- **Commit'leri mantıksal olarak ayır** — birden fazla konuyu tek commit'te
  birleştirme.
- **Yeni bir sağlayıcı/entegrasyon eklerken** mock'a değil, gerçek API'ye
  karşı en az bir kez canlı doğrulama yap (curl/script) — sadece mock
  testlere güvenme.

## Çalışma akışı
1. **Anla** — Değişiklikten önce ilgili kodu keşfet (graph araçları > grep).
2. **Planla** — 3+ dosyaya dokunan işlerde önce plan yaz, onay al.
3. **Uygula** — Küçük, test edilebilir adımlar.
4. **Doğrula** — Test + lint geçmeden "bitti" deme.
5. **Belgele** — Mimari karar alındıysa ADR yaz (`docs/adr/`, `/adr` skill).
6. **Devret** — Oturum sonunda `docs/handoff/CURRENT.md` güncelle (`/handoff`).

## Korkuluklar
- `.env*` dosyalarını okuma/yazma; secret'ları koda gömme.
- Migration'ları geri alınabilir yaz (`downgrade()` dolu olsun); gerçek bir
  prod ortamı kurulduğunda prod veriye dokunan komut asla otomatik çalışmaz.
- Test silmek/atlamak yerine düzelt; zorunluysa nedenini yaz.
- Frontend state yönetimi sadece React Query — ayrı bir global store
  (Redux/Zustand vb.) ekleme; gerekirse önce neden yetersiz kaldığını yaz.
- Bu agent kurulumunun parçalarını (`AGENTS.md`, `CLAUDE.md`, `.claude/*`,
  ADR'ler, devir notu) **kullanıcı onayı olmadan kaldırma/geri alma** —
  gereksiz veya maliyetli bulursan öner ve onay bekle. Tarifler:
  `docs/AGENT_SETUP.md`.

## Dokümantasyon haritası
- `docs/ARCHITECTURE.md` — sistem mimarisi
- `docs/adr/README.md` — mimari karar kayıtları dizini (3 haneli numara,
  asla yeniden numaralama — kod bu numaralara atıf yapıyor)
- `docs/ROADMAP.md` — faz durumu · `docs/TECHNICAL_DEBT.md` — bilinen açıklar
- `docs/handoff/CURRENT.md` — güncel durum / devir notu
- `docs/AGENT_SETUP.md` — bu kurulumun kapsamı, maliyeti ve geri alma tarifi
