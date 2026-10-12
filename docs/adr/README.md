# Mimari Karar Kayıtları (ADR)

Her ADR tek bir kararı kısa anlatır: **Bağlam → Karar → Alternatifler →
Sonuçlar**. Numaralar asla değişmez (kod bu numaralara atıf yapıyor).
Yeni ADR için `/adr` komutunu kullan.

| No | Konu | Durum |
|---|---|---|
| [001](ADR-001-monorepo-and-backend-framework.md) | Tek repo, modüler monolit backend | Kabul |
| [002](ADR-002-data-provider-selection.md) | Veri kaynakları | Kabul |
| [003](ADR-003-llm-separation.md) | LLM sadece yorumlar, asla hesaplamaz | Kabul |
| [004](ADR-004-financial-normalization-and-currency.md) | Finansal tablo normalizasyonu ve ölçek | Kabul |
| [005](ADR-005-analysis-snapshots-and-reproducibility.md) | Analiz anlık görüntüleri değişmezdir | Kabul |
| [006](ADR-006-python-version-and-local-dev-environment.md) | Python sürümü | Kabul |
| [007](ADR-007-single-user-auth-model.md) | Tek kullanıcılı kimlik doğrulama | Kabul (⚠️ açık varsayılanlar) |
| [008](ADR-008-llm-provider-chain.md) | LLM sağlayıcı sırası | Kabul |
| [009](ADR-009-phase4-data-sources-news-and-calendar.md) | Haber ve takvim | Kabul |
| [010](ADR-010-test-strategy-and-repo-structure.md) | Test stratejisi | Kabul |
| [011](ADR-011-verdict-card-and-demo-signal.md) | Hüküm kartı ve demo AL/TUT/SAT | Kabul (sinyal demo) |
| [012](ADR-012-scoring-and-valuation-methodology.md) | Skorlama ve değerleme yöntemi | Kabul |
