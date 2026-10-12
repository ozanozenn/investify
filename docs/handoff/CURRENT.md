# Devir Notu
_Güncelleme: 2026-10-12 · Branch: claude/vigilant-galileo-qlaxlf (bulut oturumu, push edildi)_

## Hedef
Kullanıcı sayfaya girince ilk saniyede "ucuz mu pahalı mı, şirket iyi mi"
görsün; ADR'ler Türkçe, kısa ve koda uygun olsun.

## Tamamlanan
- **Hüküm motoru** (`apps/api/app/verdict_engine/`, `config/verdict.yaml`,
  ADR-011): üç değerleme yöntemi (kendi geçmişi, sektör medyanı, DCF baz)
  çoğunluk oyuyla Ucuz/Makul/Pahalı; skor → Güçlü/Orta/Zayıf; güvenilirlik;
  **demo AL/TUT/SAT** (`signal.enabled`, güven düşükse verilmez). Refresh'te
  hesaplanıp snapshot'a yazılır, API'de `verdict` alanı.
- **Hüküm kartı** sayfanın en üstünde; sayfa Hüküm → Neden? → Detaylar →
  Bağlam katmanlarına ayrıldı. LLM'in "Güven %X" puanı kaldırıldı.
- Code review'da bulunan oy mantığı hatası (ortalama → azınlık kazanıyordu)
  düzeltildi. pytest 127 passed, ruff temiz, web typecheck + build geçti,
  sahte sağlayıcılı demo API ile tarayıcıda (masaüstü + mobil) doğrulandı.
- **ADR'ler baştan yazıldı**: Türkçe, Bağlam/Karar/Alternatifler/Sonuçlar,
  her iddia kodla doğrulandı (ADR-004'teki var olmayan `ScaleMismatchError`
  gibi yanlışlar düzeltildi). Yeni: ADR-011 (hüküm), ADR-012 (skor/değerleme
  yöntemi), `docs/adr/README.md` dizini. `/adr` skill'i yeni şablonda.

## Devam eden / yarım kalan
- Hüküm gerçek yfinance verisiyle henüz denenmedi (bulut ortamında Yahoo ve
  KAP engelli). Yerelde birkaç gerçek hisseyle (THYAO, ASELS, FROTO) refresh
  edip hükümlerin makul olduğunu kontrol et; eşikler `config/verdict.yaml`.
- Sektör yöntemi ancak aynı sektörden ≥ 2 şirket yenilenince oy veriyor.

## Sıradaki adımlar
1. LLM prompt **v4**: hükmü context'e ekle, LLM hükmü açıklasın; `confidence`
   alanını ve tekrar eden alanları (3 vade + bull/bear + riskler) sadeleştir.
2. Temizlik turu: `auth_dev_bypass` varsayılanı, Redis kararı, CI.
3. Tam BIST listesi (KAP erişimi gerekiyor).

## Alınan kararlar
- AL/TUT/SAT **demo** olarak açık (kullanıcı, 2026-10-12); kalıcı olursa
  `MAIN_ROADMAP.md` madde 1 güncellenmeli. LLM sinyal vermez.
- ADR numaraları ve dosya adları korundu (kod 27 dosyada atıf yapıyor).

## Dikkat
- Bulut oturumu `claude/*` branch'ine commit atar; yerel `development` onu
  görmez, PR/merge gerekir.
