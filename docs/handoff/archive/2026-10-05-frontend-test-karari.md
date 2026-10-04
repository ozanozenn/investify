# Devir Notu
_Güncelleme: 2026-10-05 · Branch: development_

## Hedef
Kurulan agent sistemini doğrulamak, ADR'lerin doğruluğunu denetlemek ve
`/feature` akışını ilk kez gerçek bir işte denemek.

## Tamamlanan
- **ADR doğruluk denetimi**: 006-010'daki her somut iddia (dosya yolu,
  fonksiyon adı, config değeri) kodla karşılaştırıldı. **Bir gerçek hata
  bulundu ve düzeltildi**: `ADR-008` "iki sağlayıcı da SDK'nın parse
  kolaylığına güvenmez" diyordu — yanlış; `OpenAIProvider` `message.parsed`'a
  güveniyor, sadece `GeminiProvider` elle yeniden doğruluyor. Kalan tüm
  iddialar teyit edildi.
- **Agent sisteminin objektif değerlendirmesi**: belgeleme tarafı (AGENTS.md,
  ADR, handoff+hook) kendini kanıtladı; subagent'lar + `/feature` ucuz ama
  henüz kanıtlanmamış durumda.
- **`/feature` ilk denemesi** (frontend testi konusunda, 1-2. aşama):
  keşif aşaması gerçek değer üretti (aşağıdaki tuzaklar), plan aşaması
  kapsamı doğru şekilde kullanıcıya getirdi ve iş **bilinçli olarak
  durduruldu**. Akışın 3-7. aşamaları hâlâ hiç çalıştırılmadı.
- Frontend test keşfinin tüm tuzakları `ADR-010`'a kaydedildi, böylece o iş
  günün birinde yapılırsa analiz ikinci kez yapılmayacak.

## Devam eden / yarım kalan
- Yok. Ama **büyük bir iş bloğu commit edilmemiş durumda** (aşağıya bak).

## Sıradaki adımlar
1. **Commit**: `AGENTS.md`, `CLAUDE.md`, `.claude/` (agents/skills/hooks/
   settings), 5 yeni ADR, `ADR-002` değişikliği, `docs/ARCHITECTURE.md`,
   `docs/TECHNICAL_DEBT.md`, `docs/handoff/` — hepsi `6ea4aa1`'den beri
   commit edilmedi. Kullanıcı henüz commit talimatı vermedi.
2. `/feature` akışının 3-7. aşamalarını (uygulama → test-runner →
   code-reviewer → docs-keeper → handoff) ilk gerçek özellikte dene.
3. "Feature freeze / sadece doğrulama" modu hâlâ geçerli — yeni özellik
   başlatmadan önce onay al (kalıcı hafıza:
   `feedback_feature_freeze_verification_mode`).

## Alınan kararlar
- **Frontend test altyapısı şimdilik kurulmayacak** (2026-10-05). Gerekçe:
  bu projede bulunan her gerçek hata backend'deydi; frontend tasarım gereği
  hesap yapmayan bir gösterim katmanı; `typecheck`+`build`+tarayıcı
  doğrulaması mevcut risk profilini karşılıyor. **Tetikleyici**: frontend
  sayı *dönüştürmeye* başlarsa (şu an tek örnek: `dcf-panel`'deki `/100`)
  veya ikinci bir geliştirici katılırsa. Tam gerekçe `ADR-010`'da.
- `ADR-010` yeniden yazılmadı — "karar verildi, uygulanmadı" hâli zaten
  doğruydu; üstüne erteleme gerekçesi + tuzak listesi eklendi.

## Açık sorular / riskler
- **codebase-memory MCP bağlanamıyor** (CONNECTION_CLOSED). Bu, CLAUDE.md'nin
  "önce graph araçlarını kullan" talimatını fiilen işlevsiz bırakıyor;
  keşif agent'ı read/grep moduna düşerek çalıştı. Bağlantı kontrol edilmeli.

## Dikkat
Bu oturumda `/feature` ilk çağrıldığında "no matching commands" verdi —
neden: skill dosyası oturum **ortasında** oluşturulmuştu. Oturum yeniden
başlatılınca düzeldi. Yeni skill/agent ekledikten sonra oturumu yenile.
