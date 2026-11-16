# ADR-003: LLM sadece yorumlar, asla hesaplamaz

**Durum:** Kabul edildi · 2026-08-17 · güncellendi 2026-10-12 (sayı biçimlendirme, halüsinasyon kontrolü) · 2026-10-27 (prompt v4: hüküm context'te, sade şema, tek düzeltme denemesi)

## Bağlam
Projenin en önemli kuralı: LLM finansal oran hesaplamaz, fiyat uydurmaz,
kaynaksız bilgi üretmez. LLM'in yazdığı her sayı kontrol edilebilir olmalı.
Hüküm kartı (ADR-011) geldikten sonra LLM'in işi de netleşti: hükmü
vermek değil, deterministik hükmü sade Türkçeyle **açıklamak** — daha az,
daha odaklı çıktıyla (daha ucuz).

## Karar
1. LLM yalnızca `StructuredAnalysisContext` alır (`services/context_builder.py`).
   İçindeki her sayı deterministik motorlardan gelir. LLM'in veritabanı ve
   sağlayıcı erişimi yok (ADR-001).
2. Sayılar LLM'e **önceden Türkçe biçimlendirilmiş** gider (`%82,6`,
   `48,9 milyar TL`, `56,7x`) — `llm/number_format.py`,
   `llm/context_formatter.py`. Prompt, LLM'in bunları aynen kullanmasını,
   yeniden yuvarlamamasını ister.
3. **Hüküm context'te** (`llm/verdict_formatter.py`): başlık, Türkçe
   fiyat/kalite/güvenilirlik etiketleri, her bakış açısının etiketi +
   hükmü + motorun yazdığı gerekçe. Ham oranlar gönderilmez. Demo sinyal
   yalnızca "demo, tavsiye değil, tekrar etme" notuyla gider. LLM hükmü
   açıklar; onunla çelişmez, yeniden hesaplamaz, kendi AL/SAT/TUT'unu ya da
   hedef fiyatını vermez.
4. Çıktı sabit, sade bir şemaya uyar (`schemas/llm_analysis.py`, v4):
   `executive_summary` (2-4 cümle), `what_matters_now` (≤5, önemliden
   önemsize), ufuk başına `{outlook, rationale}`, kısa listeler (≤3/≤4).
   LLM'in kendi `confidence` sayısı **kaldırıldı** — güvenilirlik hüküm
   kartından gelir. Şemaya uymayan yanıt `FAILED` olur; yalnızca fazla
   uzun listeler baştan kesilir.
5. `llm/hallucination_guard.py` LLM metnindeki sayıları ayrıştırır ve
   context'te olmayanları `_meta.hallucination_flags`'e yazar. Bayrak varsa
   LLM **bir kez** daha çağrılır, prompt'un sonuna desteksiz sayıları
   listeleyen kısa bir düzeltme notu eklenir; daha az bayraklı yanıt
   tutulur (`services/llm_analysis.py`). Kontrol hâlâ **uyarıdır**:
   analiz her durumda kaydedilir, kalan bayraklar arayüzde Türkçe uyarı
   olarak gösterilir.
6. Prompt sürümü dosya adıyla tutulur (`company-analysis-vN.md`); çıktının ne
   istediği değişince sürüm atlanır, eski silinmez. Şu an: **v4**. v1-v3
   eski snapshot'ların denetim kaydı için durur; v4 şemasıyla uyumlu değildir.

## Alternatifler
- **LLM'e ham float vermek** — v1/v2 böyleydi; LLM metne `0.8259859533`
  yazıyordu. Biçimlendirme deterministik katmana alındı.
- **Halüsinasyonda analizi engellemek** — kullanıcıyı özetsiz bırakır;
  sezgisel bir kontrol için fazla sert. Tek deneme + görünür uyarı seçildi.
- **Sınırsız yeniden deneme** — maliyet sınırsız olur; bir deneme yeterli.
- **Madde sınırlarını JSON Schema `maxItems` ile zorlamak** — OpenAI ve
  Gemini desteği sürüme göre değişiyor; sınır prompt + alan açıklamasında,
  fazlası sunucuda kesiliyor.

## Sonuçlar
- Her analiz, onu üreten context ile birlikte saklanır (ADR-005); eski
  (v1-v3) `analysis_json` şekli olduğu gibi kalır, arayüz iki şekli de çizer.
- Bayraklı bir refresh en fazla iki LLM çağrısı yapar.
- `_meta`: `hallucination_flags` (son), `hallucination_retry`,
  `hallucination_flags_first_attempt`, düzeltme çağrısı hata verirse
  `hallucination_retry_error`.
