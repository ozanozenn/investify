# V1 — Yerel doğrulama rehberi

V1'in kodu tamam ve testleri geçiyor (sahte sağlayıcılarla). Ama geliştirme
yapılan bulut ortamında KAP, Yahoo, İş Yatırım, Google News, TCMB EVDS ve
OpenAI'ye erişim kapalıydı. Aşağıdakiler **gerçek veriyle hiç
denenmedi** ve internete açık bir makinede bir kez yapılmalı.

Hepsi `apps/api` klasöründe çalışır:

```bash
cd apps/api
git pull origin development        # (ya da V1 dalı)
.venv/bin/pip install -e ".[dev]"  # yeni bağımlılık yok ama emin olmak için
.venv/bin/alembic upgrade head     # izleme listesi tablosu (ADR-013)
```

## 1. Giriş ayarı (zorunlu)

Kimlik doğrulama artık varsayılan **açık** (ADR-007). `.env` dosyanda:

- `APP_USER_EMAIL` ve `APP_USER_PASSWORD` — giriş ekranında bunları kullan.
- `JWT_SECRET` — rastgele uzun bir değer.
- Sadece yerelde girişi atlamak istersen: `AUTH_DEV_BYPASS=true`
  (yalnızca `APP_ENV=development` iken işler).

`APP_ENV` `development` değilse varsayılan parola/anahtarla uygulama
**açılmaz** — bu bilinçli.

## 2. Hükmü gerçek hisselerle dene

Uygulamayı aç (`docker compose up -d --build` ya da api + web ayrı), giriş
yap, şu hisseleri tek tek açıp **Yenile**'ye bas: `THYAO`, `ASELS`, `FROTO`,
`BIMAS`, `EREGL`, `TUPRS`, `PGSUS`, `SISE`.

Kontrol et:
- Hüküm kartı (Ucuz/Makul/Pahalı) sayfadaki değerleme kutularıyla ve kendi
  bilgilerinle mantıklı mı? Eşikler: `config/verdict.yaml`.
- Sektör yöntemi, aynı sektörden en az 2 şirket yenilenince oy verir —
  THYAO + PGSUS gibi ikilileri birlikte yenile.
- Kalite bayrakları ve reel büyüme kutuları dolu mu? (Reel büyüme gerçek
  TÜFE ister: `EVDS_API_KEY` tanımlı olmalı.)
- Başlıktaki fiyat ~60 sn'de bir tazeleniyor mu, "önceki kapanışa göre"
  değişimi görünüyor mu?

## 3. Bankalar (ADR-014)

```bash
.venv/bin/python scripts/verify_bank_fields.py GARAN AKBNK YKBNK --raw
```

Yahoo'nun Türk bankaları için hangi kalemleri verdiğini yazar. Eksik
kalemler `missing_fields`'e düşer (tahmin edilmez). Sonra uygulamada
`GARAN`, `AKBNK`, `YKBNK`'yı yenileyip banka göstergeleri kartına bak.

## 4. İş Yatırım finansal tabloları (ADR-015, varsayılan KAPALI)

```bash
.venv/bin/python scripts/verify_isyatirim.py --dump-codes
.venv/bin/python scripts/verify_isyatirim.py SISE BIMAS --quarterly
```

İlki THYAO/ASELS/FROTO'yu Yahoo ile yan yana karşılaştırır ve kalem
kodlarının canlı etiketlerini basar; İş Yatırım boş dönerse hata koduyla
çıkar. Sonuçlar makulse `.env`'de önce temkinli ayar:

```
FINANCIAL_PROVIDER_PRIMARY=yfinance
FINANCIAL_PROVIDER_FALLBACK=isyatirim
FINANCIAL_CROSS_CHECK=true
```

Bir süre sorunsuz giderse İş Yatırım'ı ana kaynak yap
(`PRIMARY=isyatirim`, `FALLBACK=yfinance`). Enflasyon muhasebesi (TMS 29)
yüzünden iki kaynak farklı çıkabilir; tolerans `config/financial_sources.yaml`.

## 5. Tam BIST şirket listesi (ADR-015)

```bash
.venv/bin/python scripts/import_bist_companies.py --dry-run
.venv/bin/python scripts/import_bist_companies.py
git add app/providers/company/bist_companies.json && git commit -m "data: BIST şirket listesi"
```

300'den az şirket gelirse yazmayı reddeder. KAP betiği engellerse dosyaları
tarayıcıdan indirip `--from-file` / `--sectors-from-file` ile ver.

## 6. LLM (prompt v4, ADR-003)

`.env`'de `GEMINI_API_KEY` (ücretsiz katman) ya da `OPENAI_API_KEY` tanımla,
birkaç hisseyi yenile:
- Yapay Zekâ Özeti hükmü açıklıyor mu, hükümle çelişiyor mu?
- "Bu metinde analiz verisinde bulunmayan N sayı" uyarısı çıkıyor mu? Sık
  çıkıyorsa prompt'u birlikte düzeltelim.

## 7. İzleme listesi ve otomatik yenileme (ADR-013)

Birkaç hisseyi "İzleme listesine ekle" ile ekle, ana sayfada **Şimdi
yenile**'ye bas. Otomatik yenileme varsayılan hafta içi 18:30 (İstanbul);
`WATCHLIST_REFRESH_TIME` / `WATCHLIST_REFRESH_DAYS` ile değişir.

---

Bir adımda sorun çıkarsa çıktıyı/ekran görüntüsünü paylaş; düzeltmeyi
birlikte yaparız.
