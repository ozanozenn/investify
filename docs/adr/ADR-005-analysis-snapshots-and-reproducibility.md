# ADR-005: Analiz anlık görüntüleri değişmezdir

**Durum:** Kabul edildi · 2026-08-17 · gözden geçirildi 2026-10-12

## Bağlam
"Sistem 17 Ağustos'ta THYAO için ne demişti?" sorusu tek satır okumayla
cevaplanabilmeli. Sonradan yeniden hesaplamak güncellenmiş veriyle farklı
sonuç verir; geçmiş kaybolur.

## Karar
- Her başarılı refresh `analysis_snapshots` tablosuna tam bir satır yazar:
  motor sürümleri, prompt sürümü, LLM modeli, `context_json` (LLM'e giden
  context'in tamamı, hüküm dahil), `analysis_json` (LLM çıktısı),
  `data_quality_json`.
- Satır yazıldıktan sonra **güncellenmez**. Yeni refresh yeni satır demektir.
- `GET /analysis` son satırı, `GET /analysis/history` listeyi döner. Geçmiş
  karşılaştırma ve tez takibi (`services/snapshot_diff.py`) bu satırlardan
  hesaplanır; şema değişikliği gerekmedi.
- Sonradan eklenen alanlar (ör. `verdict`) şemada opsiyoneldir; eski
  satırlar okunmaya devam eder.

## Alternatifler
- **İstek anında yeniden hesaplamak** — ucuz ama geçmişi yeniden üretemez.
- **Sadece özet skorları saklamak** — "neden böyle dedi" sorusu cevapsız kalır.

## Sonuçlar
- Depolama refresh başına bir JSON satırı; tek kullanıcı için önemsiz.
- Peer karşılaştırması diğer şirketlerin son snapshot'ını kullandığı için
  sonuç, o şirketlerin ne zaman yenilendiğine bağlıdır.
