# ADR-003: LLM sadece yorumlar, asla hesaplamaz

**Durum:** Kabul edildi · 2026-08-17 · güncellendi 2026-10-12 (sayı biçimlendirme, halüsinasyon kontrolü)

## Bağlam
Projenin en önemli kuralı: LLM finansal oran hesaplamaz, fiyat uydurmaz,
kaynaksız bilgi üretmez. LLM'in yazdığı her sayı kontrol edilebilir olmalı.

## Karar
1. LLM yalnızca `StructuredAnalysisContext` alır (`services/context_builder.py`).
   İçindeki her sayı deterministik motorlardan gelir. LLM'in veritabanı ve
   sağlayıcı erişimi yok (ADR-001).
2. Sayılar LLM'e **önceden Türkçe biçimlendirilmiş** gider (`%82,6`,
   `48,9 milyar TL`, `56,7x`) — `llm/number_format.py`,
   `llm/context_formatter.py`. Prompt, LLM'in bunları aynen kullanmasını,
   yeniden yuvarlamamasını ister.
3. Çıktı sabit bir şemaya uyar (`schemas/llm_analysis.py`) ve Pydantic ile
   doğrulanır. Uymazsa aşama `FAILED` olur; elle yamanmaz.
4. `llm/hallucination_guard.py` LLM metnindeki sayıları ayrıştırır ve
   context'te olmayanları `_meta.hallucination_flags`'e yazar. Şu an sadece
   **uyarı**; analizi engellemez, yeniden denemez.
5. Prompt sürümü dosya adıyla tutulur (`company-analysis-vN.md`); çıktının ne
   istediği değişince sürüm atlanır, eski silinmez. Şu an: v3.

## Alternatifler
- **LLM'e ham float vermek** — v1/v2 böyleydi; LLM metne `0.8259859533`
  yazıyordu. Biçimlendirme deterministik katmana alındı.
- **Halüsinasyonda otomatik yeniden deneme** — değerli ama henüz yapılmadı.

## Sonuçlar
- Her analiz, onu üreten context ile birlikte saklanır (ADR-005).
- LLM şemasında hâlâ bir `confidence` alanı var; LLM'in ürettiği bir sayı
  olduğu için arayüzde **gösterilmez**. Güvenilirlik deterministik hüküm
  kartından gelir (ADR-011). Alan bir sonraki prompt sürümünde kalkacak.
