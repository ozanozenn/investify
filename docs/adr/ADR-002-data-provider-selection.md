# ADR-002: Veri kaynakları

**Durum:** Kabul edildi · 2026-08-17 · güncellendi 2026-10-12 (EVDS3, Gemini, haber/takvim birleştirildi) · güncellendi 2026-10-27 (ADR-015: İş Yatırım finansal tablo, KAP şirket listesi)

## Bağlam
Gerçek veri şart, bütçe yok. Öncelik sırası: resmi API → ücretsiz güvenilir
kaynak → yasal kullanılabilir kamu kaynağı → açıkça etiketli mock.

## Karar
| Veri | Kaynak | Anahtar | Kod |
|---|---|---|---|
| Fiyat, tarihsel fiyat, finansal tablolar, şirket profili | Yahoo Finance (`yfinance`, `<KOD>.IS`) | yok | `providers/market`, `providers/financial`, `providers/company` |
| Finansal tablolar (birincil adayı, varsayılan kapalı) | İş Yatırım `MaliTablo` JSON'u (KAP tabanlı, XI_29 şablonu) — ADR-015 | yok | `providers/financial/isyatirim_provider.py` |
| BIST şirket listesi (arama) | KAP şirket listesi Excel'i + Sektörler sayfası, betikle üretilen dosya — ADR-015 | yok | `scripts/import_bist_companies.py`, `providers/company/ticker_index.py` |
| USD/TRY, EUR/TRY | Yahoo Finance (`USDTRY=X`) | yok | `providers/macro` |
| Politika faizi, TÜFE | TCMB EVDS3 (`evds3.tcmb.gov.tr/igmevdsms-dis/`) | `EVDS_API_KEY` (HTTP başlığında) | `providers/macro/evds_client.py` |
| KAP açıklamaları (şirket ve piyasa geneli) | KAP'ın kimlik doğrulamasız JSON API'si | yok | `providers/disclosure/kap_provider.py` |
| Haberler | Google News RSS araması | yok | `providers/news/google_news_provider.py` |
| TCMB PPK toplantı tarihleri | Elle tutulan, kaynak notlu dosya | — | `config/tcmb_calendar.yaml` |

- Her sağlayıcı hata durumunda `ProviderUnavailableError` fırlatır; pipeline
  o aşamayı `FAILED` işaretler ve devam eder, çökmez.
- EVDS anahtarı yoksa makro seriler `is_mock=True` etiketli sabit değere
  düşer; arayüz bunu "(mock)" olarak gösterir.
- KAP'a istekler arasında 0,5 sn beklenir.
- Takvimde KAP duyurularının **duyuru tarihi** gösterilir; ödeme/hak
  kullanım tarihi uydurulmaz (KAP detay sayfası JSON vermiyor).

## Alternatifler
- **Borsa İstanbul Data Store** — resmi ama ücretli lisans.
- **KAP XBRL'den finansal tablo** — doğru kaynak ama taksonomiyi çözmek
  haftalar sürer. Yahoo kapsamı yetersiz kaldığında önce KAP tabanlı İş
  Yatırım JSON'u seçildi (ADR-015); XBRL hâlâ uzun vadeli aday.
- **Ücretli haber API'leri** — gerek görülmedi.

## Sonuçlar
- Anahtarsız çalışır; sadece EVDS ve LLM anahtarı isteğe bağlı.
- Yahoo ve KAP resmi olmayan uç noktalar: biçim değişirse sağlayıcı
  bozulur (EVDS2→EVDS3 geçişinde yaşandı). Her yeni/değişen sağlayıcı
  canlı istekle doğrulanır.
- Yahoo'da BIST finansal tablo derinliği şirkete göre değişiyor; eksik alan
  `missing_fields` ile işaretlenir. İş Yatırım birincil/yedek ve çapraz
  kontrol olarak ADR-015'te; canlı doğrulanana kadar kapalı.
