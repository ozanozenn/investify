# Proje Durum Raporu

_Tarih: 2026-10-11 · Branch: `claude/vigilant-galileo-qlaxlf` (son commit `14d8e5b`) · Hazırlayan: kod tabanı denetimi (salt okunur)_

Bu rapor `docs/ROADMAP.md`, `docs/PHASE_1_SCOPE.md`, `docs/PHASE_2_PLAN.md`,
`docs/TECHNICAL_DEBT.md`, `docs/handoff/CURRENT.md` ve `MAIN_ROADMAP.md`'deki
iddiaların `apps/api/app` ve `apps/web` altındaki gerçek kodla
karşılaştırılmasıyla hazırlandı. Doküman ile kod çeliştiğinde kod esas alındı.

> **Doğrulama:** Rapor yazıldıktan sonra backend test paketi aynı oturumda
> çalıştırıldı: `pytest` **109 passed** (107 + arama düzeltmesinin 2 yeni
> regresyon testi), `ruff check .` temiz.

---

## 1. Faz durumu

**Şu an bulunulan faz:** Phase 4 (kısmen tamamlandı) — "Kalite ve
okunabilirlik turu" (feature freeze) kapanıyor; kullanıcı freeze'i
kaldırıp projeyi genişletmeye geçiyor.

| Faz | Tamamlanma | Gerekçe (kodla doğrulandı) |
|-----|-----------:|-----------------------------|
| **Phase 1** — MVP dikey dilim | **%93** | Tüm zorunlu modüller var (`providers/*`, `financial_engine/`, `valuation_engine/engine.py`, `scoring_engine/`, `services/refresh_pipeline.py`, `services/data_quality.py`, `llm/*`, `company/[ticker]/page.tsx`). Eksik: frontend testleri (ADR-010 ile bilinçli ertelendi), Redis önbelleği dokümante edilmiş ama hiç kullanılmıyor, arama ~61 sembollük statik indeksle sınırlı. |
| **Phase 2** — Değerleme ve geçmiş | **%95** | `valuation_engine/dcf.py`, `services/peer_comparison.py`, `services/snapshot_diff.py`, `providers/company/taxonomy.py`, `config/dcf.yaml`, `config/thesis.yaml` ve üç frontend paneli (`dcf-panel.tsx`, `peer-comparison-panel.tsx`, `historical-comparison-panel.tsx`) mevcut, router'lar `main.py`'de kayıtlı. Kalan: taksonomi tablosu kapsamı, dokümanların "commit edilmedi" gibi bayat ifadeleri. |
| **Phase 3** — Sektöre özel motorlar | **%3** | Kullanıcı kararıyla ertelendi (2026-09-17). Yalnızca `financial_engine/industry_strategy.py` banka/sigorta/GYO/holdingi "desteklenmiyor" durumuyla reddediyor; NIM/NPL/SYR, NAV, SOTP motorları yok. |
| **Phase 4** — Haber, takvim, izleme listesi, alarm, sohbet | **%45** | Var: `providers/news/google_news_provider.py`, `routers/news.py`, `routers/market.py`, `routers/calendar.py`, `config/tcmb_calendar.yaml`, `/haberler`, `/takvim`, `nav-bar.tsx`. Yok: watchlist, alarm motoru, şirket AI sohbeti, haber kümeleme/sentiment, takvim V2 (kesin hak kullanım tarihleri). |
| **Kalite ve okunabilirlik turu** | **%85** | `llm/number_format.py`, `llm/context_formatter.py`, `company-analysis-v3.md` (varsayılan, `core/config.py:54`), yeniden yazılmış `hallucination_guard.py` mevcut. Açık: `hallucination_flags` hâlâ yalnızca loglanıyor ve UI'da gösterilmiyor (`lib/types.ts:155`'te tip var, hiçbir bileşen render etmiyor); LLM'in kendi "Güven %" değeri UI'da gösteriliyor (bkz. Fix #3). |
| **Phase 5+** — İleri seviye | **%3** | Konsensüs, guidance takibi, sermaye tahsisi, muhasebe anomalisi, makro dashboard, teknik analiz, sonuç takibi — hiçbiri yok. Tek kısmi öğe: DCF `upside_vs_current_price` (MAIN_ROADMAP §14). |

**Paralel olarak devam eden işler:**
- "Finansal Performans" kartındaki TradingView Lightweight Charts mini bar
  grafiklerinin (`components/charts/mini-bar-chart.tsx`, `page.tsx:197-218`)
  kaldırılıp "TradingView'da Aç" butonuyla değiştirilmesi — **tamamlandı (2026-10-11)**.
- Şirket arama fallback hatası (`routers/companies.py` `search_companies`,
  DB yalnızca statik indeks 0 sonuç döndürdüğünde sorgulanıyor) — **tamamlandı (2026-10-11)**.
- KAP'tan tam BIST şirket listesi içe aktarımı — **planlandı, bloklu**
  (bulut ortamının ağ politikası `www.kap.org.tr`'yi reddediyor).

---

## 2. Eklenecek özellikler

Boyut: **S** ≈ ≤1 gün · **M** ≈ 2-5 gün · **L** ≈ 1+ hafta.

### Phase 1 tamamlayıcıları
1. **Tam BIST şirket evreni içe aktarımı** — ~500 şirketi `tickers`/`companies`
   tablolarına tek seferlik iş ile yükleme; autocomplete tüm BIST'i kapsar. **M**.
   Bloker: `kap.org.tr` erişimi (bulut ağ politikası) veya yerel makinede
   çalıştırma. Ref: TECHNICAL_DEBT "Search", MAIN_ROADMAP §34.
2. **Redis önbellek katmanı** — piyasa/makro sağlayıcı yanıtları için hafif TTL
   önbellek (bağımlılık ve compose servisi zaten var, kod yok). **S**. Ref: §52.
3. **Dönem bazlı `shares_outstanding`** — tarihsel çarpanların sabit hisse
   sayısı yaklaşımını kaldırır. **M**. Bloker: yfinance'ta dönem bazlı veri
   kapsamı belirsiz; yoksa `missing_fields` korunur. Ref: §9, TECHNICAL_DEBT "Valuation".

### Phase 3 — sektöre özel motorlar (ertelendi, yeniden değerlendirilmeli)
4. **Banka motoru** — NIM, kredi/mevduat büyümesi, NPL, SYR, maliyet/gelir;
   BIST piyasa değerinin büyük kısmı bankalar olduğu için en yüksek değerli kalem. **L**.
   Bloker: yfinance banka tabloları yetersiz; BDDK/KAP finansal tablo kaynağı gerekir. Ref: §61.
5. **GYO/REIT motoru** — NAV, NAV iskontosu, doluluk. **M**. Bloker: değerleme
   raporları KAP PDF'lerinde; ayrıştırma gerekir. Ref: §62.
6. **Holding motoru** — SOTP, holding iskontosu. **L**. Bağımlılık: iştirak
   piyasa değerleri (mevcut market provider yeterli) + iştirak payları (KAP). Ref: §63.
7. **Sigorta motoru** — Ref: MAIN_ROADMAP Phase 1 addendum §4. **M**.

### Phase 4 — kalan kapsam
8. **İzleme listesi (watchlist)** — tek kullanıcılı, DB tablosu + Ana Sayfa
   bölümü. **S-M**. Yeni migration gerekir. Ref: §27.
9. **Alarm motoru** — skor değişimi, yeni önemli KAP, değerleme eşiği;
   uygulama içi bildirim önce, e-posta/Telegram sonra. **M-L**. Bağımlılık:
   #8 ve #12 (zamanlanmış refresh). Ref: §28.
10. **Bağlama dayalı şirket AI sohbeti** — yalnızca son `AnalysisSnapshot`
    context'inden cevap, internetten bilgi yok, kaynak atıflı. **M**. Ref: §83, §84.
11. **KAP Intelligence** — her bildirim için tür/önem/etki/zaman ufku/özet
    (LLM sınıflandırma, kurallar öncelikli; LLM sayı üretmez). **M**. Ref: §20.
12. **Zamanlanmış/arka plan refresh** — refresh'i HTTP isteğinden çıkarma
    (Celery/RQ veya APScheduler). **M**. Ref: §36, §53, TECHNICAL_DEBT "Refresh execution model".
13. **Haber kümeleme + şirket ilişkisi + sentiment** — sentiment asla tek başına
    karar girdisi değil. **M**. Ref: §21.
14. **Takvim V2** — KAP detay sayfalarından kesin temettü/bedelsiz/genel kurul
    tarihleri. **L**. Bloker: KAP detay sayfası JSON API'siz SPA (headless
    tarayıcı gerekir) + ağ erişimi. Ref: ROADMAP Phase 4.
15. **Ana Dashboard** — Piyasa/Makro özeti, watchlist, önemli KAP, tez
    değişimleri, yaklaşan olaylar. **M**. Bağımlılık: #8. Ref: §30.

### Kalite turu takipleri
16. **Halüsinasyon bayraklarının UI'da gösterilmesi + bir kez otomatik retry** — **S**. Ref: §41.
17. **Deterministik "Şu An Önemli Olanlar"** — şu an frontend
    `key_catalysts`'tan 3 + `key_risks`'ten 2 madde kesiyor (`page.tsx:120`);
    §81 sıralı, kural tabanlı en fazla 5 konu istiyor. **S-M**. Ref: §81.

### Phase 5+ — MAIN_ROADMAP'te olup ROADMAP.md'nin izlemediği kalemler
18. **Kalite bayrakları (Quality Flags)** — "gelir artıyor ama nakit akışı
    bozuluyor", "alacaklar gelirden hızlı büyüyor", seyrelme, marj daralması. **M**.
    Mevcut finansal tablolarla yapılabilir, yeni kaynak gerekmez. Ref: §72.
19. **Kural tabanlı muhasebe anomali motoru** — **M**. Ref: §73.
20. **Reel (enflasyondan arındırılmış) büyüme** — nominal/reel ayrımı; TÜFE
    zaten EVDS'den geliyor. **S**. Ref: §66.
21. **Temettü analizi** — verim, dağıtım oranı, temettü CAGR, istikrar, geçmiş. **M**.
    yfinance temettü geçmişi kullanılabilir. Ref: §70.
22. **Şirket-makro duyarlılık modeli (`CompanyMacroExposure`)** — sektöre göre
    USD/EUR/faiz/petrol hassasiyeti, config tabanlı. **M**. Ref: §19.
23. **Kur riski verileri** — gelir/borç döviz payı, ihracat payı. **L**. Bloker:
    faaliyet raporu/dipnot verisi (KAP PDF). Ref: §67.
24. **Teknik bağlam göstergeleri** — SMA 20/50/200, RSI, MACD, ATR, 52 hafta,
    volatilite; yalnızca kısa vade context'i, sinyal değil. **M**. OHLCV mevcut. Ref: §29.
25. **Sermaye tahsisi takibi** — temettü/geri alım/CAPEX/borç ödemesi/sermaye artırımı. **M**. Ref: §71.
26. **Tek seferlik kalemler / normalize kazanç veri modeli** — **M**. Ref: §74.
27. **Yönetim guidance takibi (gerçekleşen vs. beklenti)** — **L**. Bloker:
    yatırımcı sunumu/KAP metin ayrıştırma. Ref: §68.
28. **Analiz sonuç takibi (Analysis Outcome Tracking)** — 3/6/12 ay sonra
    tezin gerçekleşmeyle karşılaştırılması; backtest değil. **M**.
    Bağımlılık: snapshot geçmişi (var). Ref: §44.
29. **Tam Türkiye makro paneli** — **M**. Ref: §18.
30. **Konsensüs analist verisi** — **L**. Bloker: yasal kullanılabilir kaynak
    yok; bulunmadan başlanmamalı. Ref: §69.
31. **Formül kayıt defteri (Formula Registry) / açıklanabilirlik ekranı** —
    her metriğin formülü, girdileri, kaynağı. **S-M**. Ref: §60, §76.
32. **CI hattı** — `.github/` yok; pytest + ruff + typecheck + build. **S**. Ref: §49.

**Toplam: 32 özellik kalemi.**

---

## 3. Düzeltilmesi gereken fix'ler / teknik borç

### Koddan doğan
1. **Arama fallback hatası** — `apps/api/app/api/routers/companies.py`
   `search_companies`: DB yalnızca statik indeks boşsa sorgulanıyor; indekste
   kısmi eşleşme varsa DB'deki şirketler hiç görünmüyor. **Yüksek** — _tamamlandı (2026-10-11)_.
2. **Redis bağımlılığı ölü** — `apps/api/pyproject.toml` (`redis>=5.0`),
   `docker-compose.yml` redis servisi, `core/config.py:30` `redis_url`; uygulama
   kodunda hiçbir kullanım yok. `docs/ARCHITECTURE.md:12` ve `AGENTS.md`
   "Redis önbellek olarak kullanılıyor" diyor — yanlış. **Orta**.
3. **LLM'in kendi güven skoru kullanıcıya gösteriliyor** —
   `apps/api/app/schemas/llm_analysis.py:8` `HorizonOutlook.confidence`,
   `apps/web/components/outlook-card.tsx:18` "Güven %X". MAIN_ROADMAP §75
   ("Confidence LLM'in keyfi özgüveni olmamalı") ve `services/data_quality.py`
   docstring'iyle çelişiyor. Deterministik güvenle değiştirilmeli veya kaldırılmalı. **Yüksek**.
4. **Frontend'de türetilmiş sayılar** — `app/company/[ticker]/page.tsx:506`
   `(ratio - 1) * 100` ve sabit renk eşikleri `1.15/0.9`; `page.tsx:327`
   makro `m.value / 100`; `page.tsx:452` veri kalitesi `* 100`. ADR-010 tek
   örnek olarak `dcf-panel`'i sayıyor — bu, ADR'deki "frontend testi
   tetikleyicisi"nin zaten gerçekleşmiş olabileceği anlamına gelir. **Orta**.
5. **"Şu An Önemli Olanlar" frontend'de birleştiriliyor** — `page.tsx:120`
   (bkz. Özellik #17). **Düşük**.
6. **`auth_dev_bypass` varsayılanı `True`** — `apps/api/app/core/config.py:34`.
   Yerel araç için kabul edilebilir, ama ağa açılırsa kimlik doğrulama
   fiilen kapalı. Varsayılan `False` olmalı ya da açıkça uyarılmalı. **Orta**.
7. **Hiç CI yok** — repo kökünde `.github/` yok; "test + lint geçmeden bitti
   deme" kuralı yalnızca insan disiplinine bağlı. **Orta**.
8. **Mini bar grafikleri kaldırılıyor** — `components/charts/mini-bar-chart.tsx`,
   `package.json` `lightweight-charts`. Kaldırıldıktan sonra bağımlılık da
   silinmeli. **Düşük** — _tamamlandı (2026-10-11)_.

### `docs/TECHNICAL_DEBT.md`'den hâlâ açık olanlar
9. **Tarihsel çarpanlar güncel hisse sayısıyla hesaplanıyor** —
   `apps/api/app/valuation_engine/engine.py`. **Orta**.
10. **Statik ~61 sembollük arama indeksi** —
    `apps/api/app/providers/company/ticker_index.py`. **Yüksek** (tam liste
    içe aktarımı ağ politikası nedeniyle bloklu).
11. **KAP kategorilendirmesi anahtar kelime tabanlı** —
    `apps/api/app/providers/disclosure/kap_provider.py:categorize()`; çoğu
    bildirim `OTHER`. **Orta**.
12. **Refresh HTTP isteği içinde senkron** —
    `apps/api/app/services/refresh_pipeline.py`. Watchlist/alarm için blokaj. **Orta**.
13. **Entegrasyon testleri SQLite'ta, Postgres'te değil** —
    `apps/api/tests/integration/conftest.py`. **Düşük**.
14. **Frontend bileşen testleri yok** — ADR-010 ile ertelendi; Fix #4
    tetikleyiciyi zorluyor. **Düşük-Orta**.
15. **Tek kullanıcı auth `hmac.compare_digest` ile env'e karşı** —
    `apps/api/app/core/security.py`. Tek kullanıcı kaldıkça kabul. **Düşük**.
16. **Taksonomi çeviri tablosu eksik** —
    `apps/api/app/providers/company/taxonomy.py` `_INDUSTRY_TRANSLATIONS`;
    tam BIST içe aktarımıyla birçok yeni sektör eşleşmeyecek. **Orta**.
17. **`hallucination_flags` yalnızca tavsiye niteliğinde** —
    `apps/api/app/services/refresh_pipeline.py:327`; engellemiyor, retry yok, UI'da yok. **Orta**.
18. **Sayı ayrıştırıcı tek-grup belirsizliği** (`5.678`) —
    `apps/api/app/llm/hallucination_guard.py`. Pratikte tetiklenmedi. **Düşük**.

### Bayat / kodla çelişen dokümanlar
19. **`docs/handoff/CURRENT.md`** — "büyük bir iş bloğu commit edilmemiş"
    ve "Sıradaki adım 1: Commit" diyor; bu iş `6054b28..14d8e5b` commit'lerinde
    zaten commit edildi. Feature freeze notu da artık geçersiz. **Orta**.
20. **`docs/PHASE_2_PLAN.md`** — Wave 1 tablosunda DCF ve snapshot diff hâlâ
    "dispatched", Wave 3 "dispatched", son paragraf "Nothing has been committed
    yet" (Phase 2 `d3bdb27`'de commit edildi). Test sayıları (52) eski; şu an 107. **Düşük**.
21. **`docs/TECHNICAL_DEBT.md`** — DCF negatif bear değeri "ürün kararı
    verilmeli" olarak açık duruyor, ama karar 2026-09-16'da verildi (olduğu gibi
    göster + not). "Geliştirme makinesinde Python/Docker yok" notu ortama özgü
    ve bayat. Başlık hâlâ "Phase 1 shortcuts" diyor. **Düşük**.
22. **`README.md`** — "this delivery implements Phase 1 only", `docs/ROADMAP.md`
    için "Phase 1 status + proposed Phase 2+" diyor; LLM olarak yalnız OpenAI
    anılıyor (Gemini zinciri yok). **Orta** (ilk okunan dosya).
23. **`docs/ARCHITECTURE.md`** — "Frontend information architecture" bölümü
    "Single Company Detail screen" diyor; `/haberler` ve `/takvim` yok sayılıyor.
    Redis iddiası ve var olmayan "ROADMAP CACHE section" referansı (bkz. #2). **Düşük**.
24. **`docs/DATA_SOURCES.md`** — tabloda Google News RSS satırı yok; "Deferred
    sources" altında "general news APIs" hâlâ ertelenmiş görünüyor (ADR-009 ile çelişir). **Düşük**.
25. **`CLAUDE.md` agent tablosu** — `codebase-memory-scout/-auditor` vb. agent'lar
    `~/.claude/agents/`'ta olduğu söyleniyor; bu ortamda o dizin yok, repo'da
    yalnızca `code-reviewer`, `docs-keeper`, `test-runner` var. Handoff'taki
    "codebase-memory MCP bağlanamıyor" sorunu da hâlâ açık. **Düşük**
    (değiştirmek kullanıcı onayı gerektirir — AGENTS.md korkulukları).

**Toplam: 25 fix / borç kalemi** (Yüksek: 3 · Orta: 11 · Düşük: 11; #14 Düşük-Orta, Düşük sayıldı).

---

## 4. Önerilen sıralama — projeyi bambaşka bir boyuta taşımak

Tüm adımlar katı kurallara uyar: AL/SAT/TUT sinyali yok, LLM hesap yapmaz,
tek kullanıcı, eksik veri `missing_fields` ile işaretlenir.

1. **Temizlik turu (1-2 gün)** — Fix #1, #3, #19-#24: arama hatası, LLM
   güven skorunun deterministik güvenle değiştirilmesi, bayat dokümanlar,
   ölü Redis'e karar (ya kullan ya kaldır). CI (#32) aynı turda eklenmeli —
   genişlemeye başlamadan güvenlik ağı.
2. **Tam BIST evreni (#1) + taksonomi genişletmesi (#16)** — platformu 8-60
   şirketten ~500'e çıkarır; peer karşılaştırması ancak o zaman gerçek anlam
   kazanır. KAP ağ blokajı için yerel makinede tek seferlik script veya
   bulut ağ politikasına `www.kap.org.tr` istisnası.
3. **Arka plan refresh + zamanlayıcı (#12)** — watchlist, alarm ve dashboard'un
   ön koşulu; 500 şirkette senkron refresh sürdürülemez.
4. **Kalite bayrakları + anomali motoru (#18, #19, #20)** — yeni veri kaynağı
   gerektirmeyen, deterministik, en yüksek "kanıt" değeri; LLM bunları yalnızca
   yorumlar. Reel büyüme Türkiye bağlamında zorunlu bir netlik katmanı.
5. **Watchlist + Dashboard + uygulama içi alarmlar (#8, #15, #9)** — ürünü
   "tek şirket sorgula" aracından "her sabah açılan araştırma masası"na çevirir.
6. **Bağlama dayalı AI sohbet (#10) + KAP Intelligence (#11)** — yalnızca
   snapshot context'i ve atıflı kaynaklar; halüsinasyon koruması sohbete de
   uygulanır (#16 ile birlikte).
7. **Banka motoru (#4)** — Phase 3'ün yeniden açılması; BIST piyasa değerinin
   büyük bölümünü kapsayan "desteklenmiyor" boşluğunu kapatır. Veri kaynağı
   araştırması (BDDK/KAP XBRL) önce yapılmalı, ADR yazılmalı.
8. **Analiz sonuç takibi (#28)** — geçmiş snapshot'ların sonradan gerçekleşmeyle
   karşılaştırılması; sistemin kendi isabetini şeffafça ölçmesi (backtest değil).
