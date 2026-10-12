# ADR-007: Tek kullanıcılı kimlik doğrulama

**Durum:** Kabul edildi · 2026-08-17 · gözden geçirildi 2026-10-12

## Bağlam
Uygulamayı tek kişi kullanıyor. Kullanıcı yönetimi kurmak gereksiz yük.

## Karar
- Tek kimlik, ayarlardan: `APP_USER_EMAIL` / `APP_USER_PASSWORD`. `users`
  tablosu yok, kayıt yok.
- `POST /api/auth/login` doğru bilgiyle JWT (HS256, 7 gün) verir. Korunan her
  router `core/security.py:require_user` kullanır.
- Geliştirme kolaylığı: `auth_dev_bypass=true` **ve**
  `app_env=development` ise token kontrol edilmez.

## Alternatifler
- **Gerçek kullanıcı sistemi** — ikinci bir kullanıcı olana kadar gereksiz.
- **Hiç kimlik doğrulama yok** — uygulama yanlışlıkla ağa açılırsa veriler
  ortada kalır.

## Sonuçlar
- ⚠️ İki varsayılan da (`auth_dev_bypass=True`, `app_env=development`)
  "açık" yönde. Ayar yapılmadan ağa açılan bir kurulumda kimlik doğrulama
  fiilen kapalıdır. Varsayılanı `false` yapmak açık bir iş.
- Varsayılan parola `changeme`; gerçek parola `.env`'den gelmeli.
- İkinci kullanıcı gelirse bu küçük bir yama değil: her tabloya sahiplik
  sütunu ve gerçek kayıt akışı gerekir.
