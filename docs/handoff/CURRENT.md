# Devir Notu
_Güncelleme: 2026-11-10 · Branch: `claude/vigilant-galileo-qlaxlf` (push edildi, `development`'a henüz birleştirilmedi)_

## Hedef
V1: yol haritasındaki 1-15. maddeleri tamamlamak (kullanıcı, 2026-10-27).

## Tamamlanan (V1 kod olarak bitti)
Altı paralel agent + entegrasyon; hepsi bu dalda:
- **LLM prompt v4** (ADR-003): LLM deterministik hükmü açıklar, sade çıktı
  şeması (LLM `confidence` yok), halüsinasyonda tek düzeltme denemesi,
  uyarı arayüzde.
- **Taze fiyat + Redis önbellek** (`/api/companies/{t}/quote`, 60 sn) ve
  değerleme etiketlerinin hüküm eşikleriyle birleşmesi.
- **Kalite bayrakları + reel büyüme** (ADR-016).
- **İzleme listesi + zamanlanmış yenileme + ana sayfa paneli** (ADR-013,
  yeni migration `7b6f462d1089`).
- **Banka motoru** (ADR-014): bankalar artık analiz ediliyor; sigorta/GYO
  hâlâ "desteklenmiyor".
- **İş Yatırım finansal kaynak + çapraz kontrol + BIST listesi içe aktarımı**
  (ADR-015) — **varsayılan kapalı**, canlı doğrulama bekliyor.
- **Güvenlik**: `auth_dev_bypass` varsayılan kapalı, `/giris` sayfası,
  geliştirme dışında varsayılan sırlarla açılış reddedilir (ADR-007).
- **CI** (`.github/workflows/ci.yml`) + ESLint ayarı.
- Entegre kod incelemesi bulguları düzeltildi (halüsinasyon kontrolünde
  küçük yüzde yanlış alarmı ve zaman damgası deliği — kararsız testin kök
  nedeni; yöntem değişince sahte "tez güçlendi"; açık yönlendirme; banka
  kalite bayrağı gerekçesi; 401 testleri).
- Doğrulama: pytest 424 passed, ruff/lint/typecheck/build temiz; sahte
  sağlayıcılı demo ile tarayıcıda giriş → ana sayfa → genel şirket → banka
  → sigorta (masaüstü + mobil) kontrol edildi.

## Devam eden / yarım kalan
- **Gerçek veriyle hiç denenmedi** (bulut ortamında KAP/Yahoo/İş Yatırım/
  Google News/EVDS/OpenAI kapalı). Adım adım: `docs/V1_DOGRULAMA.md`.
- `.env.example`'da `AUTH_DEV_BYPASS=true` olabilir (`.env*` okunmadı,
  kural); varsa sahibi `false` yapmalı.
- Dal `development`'a birleştirilmedi (kullanıcı kararı bekleniyor).

## Sıradaki adımlar
1. Kullanıcının yönlendirmesi: proje CV'ye profesyonel şekilde eklenecek.
2. `docs/V1_DOGRULAMA.md` adımları (yerel makinede).
3. Dalı `development`'a birleştirme + V1 etiketi.

## Alınan kararlar
- AL/TUT/SAT **demo** (ADR-011); LLM sinyal vermez.
- İş Yatırım entegrasyonu canlı doğrulanana kadar kapalı (AGENTS.md kuralı).

## Dikkat
- Bulut ortamı yenilenince push edilmemiş commit'ler kaybolur (2026-11-10
  bir doküman commit'i böyle kayboldu, yeniden yazıldı) — her commit'ten
  sonra push.
- Demo sunucusunu kapatırken süreç adı `.venv/bin/python …demo_server2.py`;
  yanlış kalıpla kapatılmazsa veritabanı silinince 500'ler görünür (gerçek
  hata değil, 2026-11-10'da doğrulandı).
