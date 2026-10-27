# ADR-007: Tek kullanıcılı kimlik doğrulama

**Durum:** Kabul edildi · 2026-08-17 · güncellendi 2026-10-27 (bypass varsayılanı kapalı, giriş ekranı)

## Bağlam
Uygulamayı tek kişi kullanıyor. Kullanıcı yönetimi kurmak gereksiz yük.

## Karar
- Tek kimlik, ayarlardan: `APP_USER_EMAIL` / `APP_USER_PASSWORD`. `users`
  tablosu yok, kayıt yok.
- `POST /api/auth/login` doğru bilgiyle JWT (HS256, 7 gün) verir. Korunan her
  router `core/security.py:require_user` kullanır.
- Frontend'de `/giris` sayfası var. Token tarayıcıda (`localStorage`)
  saklanır, her isteğe `Authorization` başlığı olarak eklenir; 401 gelirse
  giriş sayfasına yönlendirilir (`apps/web/lib/auth.ts`).
- `auth_dev_bypass` **varsayılan kapalı**. Yerelde istenirse `.env`'de
  `AUTH_DEV_BYPASS=true` yapılır; yalnız `APP_ENV=development` iken işler
  ve açılışta uyarı loglanır.
- Geliştirme dışında (`APP_ENV` ≠ `development`) varsayılan `JWT_SECRET`
  veya `APP_USER_PASSWORD` ile uygulama **açılmaz**
  (`core/security.py:assert_secure_settings`, lifespan'de çağrılır).

## Alternatifler
- **Gerçek kullanıcı sistemi** — ikinci bir kullanıcı olana kadar gereksiz.
- **Hiç kimlik doğrulama yok** — uygulama yanlışlıkla ağa açılırsa veriler
  ortada kalır.

## Sonuçlar
- Ayarsız bir kurulum artık sessizce herkese açık kalmaz: ya giriş ister
  ya da (geliştirme dışında) hiç açılmaz.
- Geliştirmede varsayılan parola `changeme` hâlâ kabul edilir; gerçek
  parola `.env`'den gelmeli.
- Token `localStorage`'da: XSS'e karşı httpOnly çerez kadar güçlü değil.
  Tek kullanıcılı yerel araç için kabul; ağa açılırsa çereze geçilmeli.
- İkinci kullanıcı gelirse bu küçük bir yama değil: her tabloya sahiplik
  sütunu ve gerçek kayıt akışı gerekir.
