# ADR-008: LLM sağlayıcı sırası (OpenAI → Gemini → Mock)

**Durum:** Kabul edildi · 2026-09-17 · gözden geçirildi 2026-10-12

## Bağlam
ADR-003 LLM'in rolünü belirler; bu ADR çalışma anında hangi modelin o rolü
üstleneceğini belirler. Ücretli API'ye bağımlı kalmak istemiyoruz.

## Karar
- Tek arayüz: `llm/base.py:LLMProvider`. Pipeline hangi sağlayıcının aktif
  olduğuna göre dallanmaz.
- Seçim, tanımlı anahtara göre otomatik (`services/provider_bundle.py`):
  1. `OPENAI_API_KEY` → OpenAI (varsayılan model `gpt-4.1-mini`)
  2. yoksa `GEMINI_API_KEY` → Gemini (ücretsiz katman, varsayılan
     `gemini-3.6-flash`)
  3. yoksa → `MockLLMProvider` (her metin `[MOCK LLM ...]` ile başlar)
- OpenAI çıktısı SDK'nın şema doğrulamasına (`message.parsed`) güvenir;
  Gemini'nin ham metni her zaman Pydantic ile yeniden doğrulanır.
- İkisi de geçici hatalarda 3 kez üstel bekleme ile yeniden dener.

## Alternatifler
- **Tek sağlayıcı** — ya maliyet ya da tek tedarikçiye bağımlılık.
- **Yerel model (Ollama vb.)** — Türkçe kalite ve yapılandırılmış çıktı
  güvenilirliği denenmedi.

## Sonuçlar
- Sağlayıcı değiştirmek `.env` değişikliği, kod değişikliği değil.
- İki SDK paralel bakılır. Prompt ortak; sağlayıcı başına kopyalanmaz.
- Model adları emekliye ayrılabiliyor (gemini-2.0-flash'ta yaşandı);
  varsayılanlar ayarlardan değiştirilir.
