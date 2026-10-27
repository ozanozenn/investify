# ADR-015: Finansal veri kaynakları v2 — İş Yatırım, çapraz kontrol, tam BIST listesi

**Durum:** Kabul edildi (İş Yatırım canlı doğrulanana kadar varsayılan kapalı) · 2026-10-27

## Bağlam
Finansal tablolar yalnızca yfinance'ten geliyor; birçok BIST şirketinde eksik
veya geç. Arama ~60 kodluk elle yazılmış dizine dayanıyor, BIST'te 500+
şirket var. Yeni sağlayıcılar kod yazıldığı ortamdan canlı doğrulanamadı
(isyatirim.com.tr ve kap.org.tr erişilemiyordu).

## Karar
- **İş Yatırım MaliTablo** (`providers/financial/isyatirim_provider.py`):
  `GET …/Common/Data.aspx/MaliTablo?companyCode&exchange=TRY&financialGroup=XI_29&year1..4&period1..4`.
  Yıl başına bir istek (zorunlu 4 dönem: 3/6/9/12). Yalnız XI_29 (sanayi)
  şablonu; banka/sigorta boş döner → yedek kaynak.
- Eşleme `isyatirim_mapping.py`'de (ADR-004 deseni): 3C hasılat, 3D brüt kâr,
  3DF esas faaliyet kârı, 3Z (yoksa 3L) net kâr, 1AA nakit, 1BL toplam
  varlık, 2O (yoksa 2N) özkaynak, 2AA+2BA finansal borç, 3H+4B FAVÖK,
  4C işletme nakit akışı, 4CAI yatırım harcaması. Kodlar birden çok açık
  kaynak istemcinin kayıtlı yanıtlarıyla çapraz kontrol edildi. 4CB (FCF)
  tanımı farklı olduğu için eşlenmedi.
- 3*/4* kalemleri yıl başından kümülatif: çeyrekler önceki dönemle fark
  alınarak tek çeyreğe çevrilir; önceki dönem yoksa alan boş kalır.
- **Birincil + yedek** (`providers/financial/composite_provider.py`):
  birincil hata/boş → yedek. Çapraz kontrol açıksa ikisi birlikte
  sorgulanır; aynı dönem/alan toleransı aşarsa birincilin değeri kullanılır
  ve Türkçe veri kalitesi uyarısı eklenir (`services/financial_sources.py`).
- Ayarlar: `FINANCIAL_PROVIDER_PRIMARY` (yfinance), `FINANCIAL_PROVIDER_FALLBACK`
  (none), `FINANCIAL_CROSS_CHECK` (false) — varsayılan = eski davranış.
  Tolerans/alanlar `config/financial_sources.yaml`.
- Doğrulama: `scripts/verify_isyatirim.py` (THYAO/ASELS/FROTO yan yana,
  `--dump-codes` canlı kalem etiketleri). Geçerse önerilen ayar:
  PRIMARY=isyatirim, FALLBACK=yfinance, CROSS_CHECK=true.
- **Tam BIST listesi**: `scripts/import_bist_companies.py` KAP şirket
  listesi (`/tr/api/company/generic/excel/IGS/A`) + Sektörler sayfasından
  `providers/company/bist_companies.json` üretir (kaynak/tarih metadata'da);
  `ticker_index` dosya varsa statik dizinle birleştirir, yoksa statiğe düşer.

## Alternatifler
- **KAP XBRL** — doğru kaynak ama taksonomi işi haftalar sürer.
- **borsapy/isyatirimhisse'yi bağımlılık olarak eklemek** — ağır bağımlılık
  ağacı, kümülatif/mükerrer satır sorunları; uç nokta basit, doğrudan çağrı yeterli.
- **Açık kaynak bir BIST listesini commit etmek** — güncelliği ve kaynağı
  doğrulanabilen bir liste bulunamadı; kod uydurmamak için betik tercih edildi.

## Sonuçlar
- İş Yatırım ve KAP uç noktaları resmî değil; biçim değişirse sağlayıcı
  bozulur, birleşik sağlayıcı yfinance'e düşer.
- **Lisans:** borsapy/isyatirimhisse "yalnızca kişisel ve eğitim amaçlı"
  diyor; tek kullanıcılı kişisel araç için kabul edilebilir. Ürün ticari
  olursa İş Yatırım / Borsa İstanbul'dan lisans gerekir.
- TMS 29 (enflasyon muhasebesi) yeniden düzenlemeleri kaynaklar arası
  farkın olağan nedeni; tolerans canlı karşılaştırmadan sonra ayarlanmalı.
- Açık işler: sahibi doğrulama betiğini çalıştırıp varsayılanı değiştirmeli
  ve `import_bist_companies.py` çıktısını commit etmeli; banka (UFRS)
  şablonu eşlemesi yok.
