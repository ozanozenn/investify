# ADR-012: Skorlama ve değerleme yöntemi

**Durum:** Kabul edildi · 2026-08-17 (skor), 2026-09-17 (DCF) · ilk kez yazıldı 2026-10-12 · bankalar için değiştirildi: ADR-014

## Bağlam
Skor ve değerleme ürünün çekirdeği ama hangi kararla böyle kurulduğu hiçbir
ADR'de yoktu. Eşikleri kod değiştirmeden ayarlayabilmek istiyoruz.

## Karar
- **Skor** (`scoring_engine/engine.py`, `config/scoring.yaml`): 5 kategori
  (büyüme %25, kârlılık %20, bilanço %20, nakit akışı %15, değerleme %20).
  Her metrik, yaml'daki kırılma noktaları arasında doğrusal enterpolasyonla
  puana çevrilir. Eksik metrik 0 sayılmaz; kategori kalan metriklerle
  100'e yeniden ölçeklenir ve gerekçede belirtilir.
- **Göreli değerleme** (`valuation_engine/engine.py`): F/K, PD/DD, FD/FAVÖK ve
  bunların şirketin kendi 5 yıllık medyanına oranı.
- **DCF** (`valuation_engine/dcf.py`, `config/dcf.yaml`): 5 yıllık projeksiyon,
  ayı/baz/boğa senaryoları ve WACC × terminal büyüme duyarlılık tablosu.
  Varsayımlar şirketin geçmişinden türetilir; türetilemezse yaml'daki
  varsayılan kullanılır ve `missing_fields`'e yazılır. Kullanıcı varsayımları
  ayrı uçtan değiştirebilir.
- **Desteklenmeyen sektörler**: sigorta ve GYO (`Company.is_financial_industry`,
  banka olmayanlar) genel motora sokulmaz; yanlış skor yerine "desteklenmiyor"
  gösterilir (`financial_engine/industry_strategy.py`). Bankalar genel motora
  da sokulmaz; ayrı banka motoru ve `config/bank_scoring.yaml` ile analiz
  edilir, DCF uygulanmaz (ADR-014).
- Formül değişirse motor sürümü (`*_engine_version`) atlanır; sadece eşik
  değişirse atlanmaz.

## Alternatifler
- **Eşikleri koda gömmek** — her ayarda kod değişikliği ve test gerekir.
- **Bankaları da genel motorla skorlamak** — FAVÖK/borç gibi kavramlar
  bankada anlamsız; yanıltıcı skor üretir.

## Sonuçlar
- Tarihsel çarpanlar bugünkü hisse sayısıyla hesaplanıyor; dönem içinde
  sermaye değişikliği olan şirketlerde sapma olabilir (`missing_fields`'te
  işaretli).
- Ağır borçlu şirketlerde DCF ayı senaryosu negatif hisse değeri verebilir;
  bu bir hata değil, modelin sonucu.
- BIST piyasa değerinin büyük kısmı bankalar; banka motoru ADR-014 ile
  eklendi. Sigorta ve GYO motoru hâlâ eksik.
