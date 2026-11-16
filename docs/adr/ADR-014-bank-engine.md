# ADR-014: Banka analiz motoru

**Durum:** Kabul edildi · 2026-10-27 · ADR-012'nin "desteklenmeyen sektörler" maddesini bankalar için değiştirir

## Bağlam
Bankalar `Company.is_financial_industry` nedeniyle "desteklenmiyor"
gösteriliyordu (ADR-012), oysa BIST piyasa değerinin büyük kısmı bankalar.
Genel motorun FAVÖK, net borç ve serbest nakit akışı kavramları bankada
anlamsız. Veri kaynağı yfinance; geliştirme ortamından Yahoo'ya erişim yok.

## Karar
- **Tespit:** `industry_strategy.is_bank_industry` — finansal bayrak + endüstri
  "Bankacılık" (ya da ham "Banks - Regional/Diversified"). Sigorta ve GYO
  desteklenmeyen yolda kalır.
- **Veri:** yeni `CanonicalField` üyeleri (NET_INTEREST_INCOME, INTEREST_INCOME,
  INTEREST_EXPENSE, OPERATING_EXPENSE, CREDIT_LOSS_PROVISION, LOANS, DEPOSITS);
  yfinance satır adları kurulu yfinance 0.2.66 `const.py:fundamentals_keys`
  listesine göre eşlendi (`yfinance_mapping.py`, `BANK_*`). Mevduat o listede
  yok → DEPOSITS eşlenmedi.
- **Motor:** `financial_engine/bank_engine.py` (saf): ROE, ROA, yaklaşık net faiz
  marjı (NFG / ortalama **toplam** aktif), NFG/net kâr/özkaynak büyümesi,
  özkaynak/aktif, karşılık/NFG, varsa kredi/mevduat ve yaklaşık gider/gelir.
- **Değerleme:** `compute_valuation` yeniden kullanılır (F/K, PD/DD, kendi
  medyanı); FD/FAVÖK boşaltılır, DCF yok (`services/bank_analysis.py`, DCF ucu 422).
- **Skor:** `scoring_engine/bank_scoring.py` + `config/bank_scoring.yaml`
  (`bank-v1`), aynı `ScoreResult` anahtarlarıyla: büyüme %25, kârlılık %30,
  bilanço ve risk %25, değerleme %20, nakit akışı %0 (değer üretilmez,
  gerekçe yazılır). Gider/gelir skora girmez.
- **Hüküm:** yalnızca tarihsel ve sektör yöntemleri oy verir; DCF yöntemi
  "Bankalar için DCF uygulanmaz…" gerekçesiyle `not_applicable` listelenir.
  Banka yalnızca bankalarla kıyaslanır (sektöre geri düşüş yok).
- **Context/arayüz:** opsiyonel `bank_metrics` alanı (eski snapshot'lar
  okunur), banka veri kalitesi (`compute_bank_data_quality`); LLM'e yalnızca
  bankada, yaklaşıklık notuyla girer; sayfada `bank-metrics-card.tsx` genel
  finansal kartın ve DCF panelinin yerini alır.

## Alternatifler
- **Bankayı genel motorla skorlamak** — FAVÖK/net borç bankada anlamsız.
- **Ayrı `BankScoreResult` şeması** — şema, arayüz ve karşılaştırma uçları
  çatallanırdı; aynı anahtarlar + ağırlık 0 daha küçük yüzey.
- **Faiz dışı geliri ve mevduatı başka kalemlerden türetmek** — Yahoo'nun
  banka tanımları doğrulanmadı; tahmin olurdu.

## Sonuçlar
- Bankalar skor, değerleme ve hüküm alır; sigorta/GYO hâlâ desteklenmiyor.
- **Canlı doğrulanmadı:** Türk bankalarında hangi yfinance kalemlerinin dolu
  geldiği bilinmiyor; internetli makinede `apps/api/scripts/verify_bank_fields.py`
  çalıştırılıp eşleme gerekirse düzeltilmeli.
- Kredi/mevduat yfinance ile hep eksik; gider/gelir yaklaşık ve skor dışı;
  NIM gerçeğinden düşük. Eşikler nominal TL. Snapshot'ın
  `financial_engine_version` sütunu bankada da ayar değeridir (motor sürümü
  `bank_metrics.engine_version`'da). Eski banka snapshot'ları değişmez.
