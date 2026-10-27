# ADR-010: Test stratejisi

**Durum:** Kabul edildi · 2026-10-05 · sadeleştirildi 2026-10-12 (repo yapısı kısmı ADR-001'de)

## Bağlam
Bu projede bulunan tüm gerçek hatalar backend'deydi (FCF işaret hatası,
halüsinasyon regex'i, KAP kategorileri, EVDS geçişi, Gemini model emekliliği).
Frontend tasarım gereği hesap yapmayan bir gösterim katmanı.

## Karar
- **Backend:** `pytest` + `pytest-asyncio`. `tests/unit/` saf motorlar ve
  sağlayıcı ayrıştırma (HTTP `respx` ile taklit), `tests/integration/` API
  uçları (SQLite bellek içi DB, sahte sağlayıcılar). Lint: `ruff`.
- **Frontend:** şimdilik otomatik test yok. `typecheck` + `build` + değişiklik
  başına tarayıcıda kontrol yeterli.
- Kurulduğunda: **Vitest + React Testing Library**.

## Alternatifler
- **Jest** — Next 15 / React 19 / ESM ile daha fazla ayar ister.
- **Frontend testlerini şimdi kurmak** — değişen bir arayüzde bakım maliyeti
  yüksek, yakalayacağı hata az.

## Sonuçlar
- Frontend sayı *dönüştürmeye* başlarsa veya ikinci geliştirici katılırsa
  test kurulur. Bugün tek örnek `dcf-panel.tsx`'teki yüzde → oran (`/100`)
  dönüşümü.
- Kurulum yapılırken bilinen tuzaklar: `global.fetch` taklit edilmeli
  (`lib/api*.ts` modülleri değil); `theme-provider` jsdom'da `matchMedia`
  ister; her testte `retry: false` ile yeni `QueryClient`; `tr-TR` `Intl`
  çıktısı ICU sürümüne göre değişir.
- Bulut ortamında `npm run lint` ESLint ayarı olmadığı için çalışmıyor;
  ayrı bir iş.
