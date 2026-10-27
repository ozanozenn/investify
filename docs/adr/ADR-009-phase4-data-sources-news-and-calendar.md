# ADR-009: Haber ve takvim

**Durum:** Kabul edildi · 2026-09-28 · sadeleştirildi 2026-10-12 (kaynak tablosu ADR-002'ye taşındı)

## Bağlam
Phase 4'te haber akışı ve yaklaşan olaylar takvimi eklendi. Kaynak seçimleri
ADR-002'deki tabloda; bu ADR bu iki özelliğin nasıl davrandığını belirler.

## Karar
- **Haberler** (`GET /api/companies/{ticker}/news`, `GET /api/market/news`):
  Google News RSS; benzer başlıklar birleştirilir (benzerlik ≥ 0,75).
  Kaydedilmez, LLM'e verilmez, duygu analizi yok.
- **Takvim** (`GET /api/calendar`) iki güven seviyesini ayrı gösterir:
  - TCMB PPK tarihleri: resmi ve ileriye dönük, `config/tcmb_calendar.yaml`
    (TCMB yeni yılın takvimini yayınlayınca elle güncellenir).
  - Temettü / sermaye artırımı / halka arz: KAP piyasa akışından anahtar
    kelimeyle süzülür ve **duyuru tarihi** olarak etiketlenir.

## Alternatifler
- **KAP detay sayfalarından gerçek ödeme tarihlerini çekmek** — sayfa
  JSON vermiyor, şablon başına kırılgan kazıma gerekir. Takvim V2 adayı.
- **Haber kümeleme ve duygu skoru** — kullanıcı önce sade sürümü istedi.

## Sonuçlar
- Halka arz kapsamı KAP duyurusu ve anahtar kelime eşleşmesi kadar iyi.
- KAP kategorilendirme basit kelime eşleşmesi; yeni kalıplar buldukça liste
  genişletilir (`kap_provider.py:categorize`).
