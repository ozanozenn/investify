# ADR-016: Kalite bayrakları ve reel (enflasyondan arındırılmış) büyüme

**Durum:** Kabul edildi · 2026-10-27

## Bağlam
Skor kartı bir şirketin "ne kadar iyi" göründüğünü özetliyor ama "gelir
artıyor, nakit akışı bozuluyor" gibi tutarsızlıkları ayrıca söylemiyordu
(`MAIN_ROADMAP.md` §72). Türkiye'de yüksek enflasyon nominal büyümeyi
şişirdiği için %40 gelir artışı %45 enflasyonda aslında küçülmedir (§66).
İkisi de LLM'e bırakılamaz (ADR-003): deterministik üretilmeli.

## Karar
- Saf motor `financial_engine/quality_flags.py`, eşikler
  `config/quality_flags.yaml` (`version` alanıyla). Son iki yıllık dönemden
  9 kontrol: gelir–faaliyet nakit akışı, kâr–nakit (tahakkuk), FAVÖK ve net
  marj eğilimi, borç–FAVÖK, art arda negatif SNA, özkaynak, ticari
  alacak–gelir, stok–gelir.
- Önem: `UYARI` / `DIKKAT` / `OLUMLU` (yalnızca marj genişlemesi olumlu).
  Başlık/açıklama sade Türkçe ve **rakamsız**; ham sayılar `values`'ta
  (birimi `ratio`/`currency`), biçimlendirme arayüzde ve
  `llm/context_formatter.py`'de yapılır.
- İki büyüme **göreli farkla** kıyaslanır: `(1+a)/(1+b) − 1`. Enflasyon iki
  tarafta olduğu için birbirini götürür; yüzde puan farkı yüksek
  enflasyonda yanıltırdı.
- Girdi eksikse ya da taban sıfır/negatifse kontrol "değerlendirilemedi"
  (`not_evaluated` + `missing_fields`) olur — tahmin edilmez.
- Yeni kanonik alanlar `RECEIVABLES`, `INVENTORY` (yfinance etiketleri
  kurulu paketin `const.py` listesinden doğrulandı; kolon String, migration yok).
- Reel büyüme `financial_engine/real_growth.py` + `formulas.real_growth`:
  `(1+nominal)/(1+TÜFE)−1`, gelir ve net kâr için. Mock TÜFE ile asla
  (`cpi_yoy_mock`); TÜFE gözlemi mali yıl sonundan 12 aydan uzaksa
  hesaplanmaz (`cpi_period_mismatch`).
- `services/quality_analysis.py` config'i okur, pipeline `build_context`
  sonrası `context.quality_flags` / `context.real_growth`'u doldurur.
  Alanlar opsiyonel (ADR-005). Banka/GYO'da `unsupported_industry`.
- Arayüz: Skor Kartı altında "Kalite Bayrakları" kartı; "Finansal
  Göstergeler"de iki reel büyüme kutusu ve yaklaşıklık ipucu.

## Alternatifler
- **Bayrakları LLM'e çıkarttırmak** — ADR-003'e aykırı, tekrarlanamaz.
- **Bayrakları skora katmak** — skor yöntemini (ADR-012) değiştirir ve eski
  snapshot'larla kıyası bozar; şimdilik ayrı bilgi katmanı.
- **Mali yıl ortalama TÜFE'si** — doğru arındırıcı bu, ama EVDS'ten yalnızca
  son yıllık değişimi çekiyoruz; tarihsel seri ayrı iş.

## Sonuçlar
- Kullanıcı ve LLM tutarsızlıkları sayılarıyla görür; eksik veri görünür kalır.
- Reel büyüme yaklaşıktır (son TÜFE ≠ mali yıl enflasyonu); kod, LLM
  context notu ve arayüz ipucu bunu açıkça söyler.
- `EVDS_API_KEY` yoksa TÜFE mock'tur, reel büyüme hiç görünmez.
- Açık işler: mali yıl TÜFE serisiyle tam arındırma; hisse sulandırma ve
  tek seferlik kalemler (§72'nin diğer maddeleri) veri olmadığı için yok;
  prompt'un bayrakları açıkça yorumlaması bir sonraki prompt sürümünün işi.
