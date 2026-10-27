# ADR-011: Hüküm kartı ve demo AL/TUT/SAT sinyali

**Durum:** Kabul edildi · 2026-10-12 · sinyal kısmı **demo**, kapatılabilir

## Bağlam
Kullanıcı sayfaya girdiğinde ilk saniyede "ucuz mu pahalı mı, şirket iyi mi"
sorusunun cevabını görmeli, sonra aşağı indikçe detaya inmeli. Bu cevap
dağınıktı (değerleme 6. bölümdeydi), üstelik "güven" olarak LLM'in kendi
uydurduğu bir sayı gösteriliyordu (ADR-003 ihlali). Kullanıcı ayrıca
AL/TUT/SAT sinyalini deneme amaçlı görmek istedi.

## Karar
- Yeni saf motor `app/verdict_engine/engine.py`, eşikler `config/verdict.yaml`.
- **Fiyat** (Ucuz / Makul / Pahalı): üç yöntem ayrı oy verir; oy verenlerin
  **yarısından fazlası** aynı şeyi demezse fiyat hükmü yoktur (ortalama alınmaz).
  - Kendi geçmişi: güncel F/K, FD/FAVÖK, PD/DD ÷ 5 yıllık medyan (< 0,85 ucuz, > 1,15 pahalı)
  - Sektör: aynı çarpanlar ÷ benzer şirket medyanı (her çarpan için en az 2
    şirket; benzerlerin son snapshot'ı kullanılır, tazelik filtresi yok)
  - DCF: baz senaryo içsel değerin fiyata göre farkı (> +%20 ucuz, < −%20 pahalı)
  - Negatif çarpanlar (zarar eden şirketin F/K'sı) hesaba katılmaz.
- **Kalite** (Güçlü / Orta / Zayıf): genel skora göre (≥ 65 / ≥ 45).
- **Güvenilirlik** (Yüksek / Orta / Düşük): kaç yöntem veri verdi, ne kadar
  uzlaşıyor, veri kalitesi ne.
- **Sinyal (demo):** fiyat × kalite tablosundan türetilir. Ucuz ama zayıf
  şirkete AL verilmez (değer tuzağı) → TUT. Güvenilirlik düşükse sinyal
  verilmez. `signal.enabled: false` ile
  kapanır; kapalıyken arayüz sinyal hücresini hiç göstermez.
- Veri olmayan yöntem oy vermez, `missing_fields`'e yazılır; tahmin edilmez.
- Hüküm refresh sırasında hesaplanır ve snapshot'a yazılır (ADR-005).
  Banka/GYO gibi desteklenmeyen sektörlerde hüküm üretilmez.
- Şirket sayfası katmanlı: Hüküm → Neden? (skor, değerleme, DCF,
  karşılaştırma) → Detaylar → Bağlam (KAP, haber, makro).
- LLM'in `confidence` alanı arayüzde gösterilmez.

## Alternatifler
- **Hükmü LLM'e yazdırmak** — ADR-003'e aykırı ve tekrarlanamaz.
- **Tek yöntem (sadece DCF)** — DCF varsayımlara çok duyarlı; tek başına
  yanıltıcı olur.
- **Oyların ortalaması** — ilk sürüm böyleydi; "1 ucuz + 2 makul" ortalaması
  "ucuz" ve AL çıkarıyordu (azınlık kazanıyordu). Çoğunluk kuralına geçildi.
- **Sinyal hiç olmasın** (`MAIN_ROADMAP.md` madde 1) — kullanıcı demo olarak
  görmek istedi; "yatırım tavsiyesi değildir" notuyla ve tek ayarla
  kapatılabilir şekilde eklendi.

## Sonuçlar
- Sinyal açıkken proje "AL/SAT/TUT vermez" kuralının bilinçli bir
  istisnasında. Kalıcı olursa `MAIN_ROADMAP.md` madde 1 güncellenmeli.
- Sektör yöntemi, aynı sektörden başka şirketler yenilendikçe güçlenir;
  ilk aşamada çoğu şirkette "veri yok" görünür.
- Hüküm prompt v4'ten beri LLM context'inde; LLM onu yalnızca açıklar,
  demo sinyali tekrar etmez (ADR-003).
