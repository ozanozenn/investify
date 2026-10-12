# ADR-004: Finansal tablo normalizasyonu ve ölçek

**Durum:** Kabul edildi · 2026-08-17 · gözden geçirildi 2026-10-12 (kodla uyumlu hale getirildi)

## Bağlam
Aynı kalem farklı kaynaklarda farklı adlarla ("Total Revenue", "Hasılat")
ve farklı ölçeklerle (TL, bin TL) gelir. "1000 TL ile 1 TL'yi karıştırma"
hatasını yapısal olarak engellemek istiyoruz.

## Karar
- Sabit bir kanonik kalem listesi: `models/enums.py:CanonicalField`
  (REVENUE, EBITDA, NET_INCOME, EQUITY, TOTAL_DEBT, CASH, CAPEX, ...).
- Her sağlayıcı kendi alan adlarını bu listeye kendi eşleme dosyasında
  çevirir (`providers/financial/yfinance_mapping.py`). Aşağı katmanlar
  sağlayıcıya özgü ad görmez.
- `financial_values` tablosu her satırda `value`, `currency`, `scale` tutar.
  Hesaplamalar `FinancialValue.base_value` (= value × scale) üzerinden yapılır.
- Tüm şirketlerin TRY raporladığı varsayılır; `currency` sütunu bu varsayımı
  görünür kılmak için doldurulur. Çoklu para birimi desteklenmez.
- Hesaplamalarda `float` kullanılır, `Decimal` değil (muhasebe hassasiyetinde
  bir sistem değiliz).

## Alternatifler
- **Sağlayıcının ham alan adlarıyla çalışmak** — her yeni sağlayıcı motoru
  değiştirmeye zorlardı.
- **Farklı para birimi karışınca hata fırlatan koruma** — eski metinde
  `ScaleMismatchError` olarak anlatılıyordu ama **hiç yazılmadı**. USD
  raporlayan bir şirket eklenene kadar gerek yok.

## Sonuçlar
- Yeni sağlayıcı = yeni eşleme dosyası; motor değişmez.
- Ölçek hatası `base_value` disipliniyle önlenir; para birimi karışımına
  karşı kodda koruma yok.
