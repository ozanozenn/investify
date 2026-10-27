# ADR-013: İzleme listesi ve zamanlanmış toplu yenileme

**Durum:** Kabul edildi · 2026-10-27

## Bağlam
Yenileme yalnızca HTTP isteği içinde, tek hisse için çalışıyordu
(`POST /api/companies/{ticker}/refresh`); ana sayfa yalnızca bir arama
kutusuydu. Kullanıcı takip ettiği hisseleri tek ekranda, BIST kapanışından
sonra kendiliğinden güncellenmiş hâlde görmek istiyor. Tek kullanıcı, tek
API süreci; Celery/kuyruk hâlâ gereksiz (`docs/ARCHITECTURE.md` "System shape").

## Karar
- Tablo `watchlist_items` (`app/models/watchlist.py`, migration
  `7b6f462d1089`): hisse başına bir satır + son toplu işin zamanı, durumu
  (SUCCESS/FAILED), tetikleyicisi ve hatası. Kullanıcı kolonu yok (ADR-007).
- API `app/api/routers/watchlist.py`: `GET /api/watchlist` (özet + zamanlayıcı
  durumu), `POST` `{ticker}`, `DELETE /{ticker}`, `POST /refresh`.
- Ekleme, şirket rotalarıyla aynı yoldan doğrular (`get_or_create_company`):
  şirket DB'de varsa ağ çağrısı yok, yoksa `CompanyDataProvider`; bulunamazsa
  404. Eklemede tam analiz **çalışmaz** — ilk snapshot şirket sayfasında ya da
  sonraki toplu yenilemede oluşur. Biçim hatası 422; zaten listedeyse 200.
- Özet sunucuda son iki snapshot'tan kurulur (`services/watchlist.py`): ad,
  fiyat, `as_of`, genel skor, hüküm özeti (ADR-011), skor değişimi, son
  yenileme zamanı, son toplu iş başarısız mı. Desteklenmeyen sektörde skor
  `None` (0 yanıltıcı olurdu).
- İş `services/watchlist_refresh.py`: hisseler sırayla, her biri kendi
  `AsyncSession`'ıyla `run_refresh`'ten geçer; bir hata diğerlerini durdurmaz.
- Zamanlayıcı `services/watchlist_scheduler.py`: küçük bir asyncio döngüsü,
  `app/lifespan.py` başlatır/durdurur. Ayarlar `Settings`'te:
  `WATCHLIST_REFRESH_ENABLED` (varsayılan açık; testlerde `tests/conftest.py`
  kapatır), `WATCHLIST_REFRESH_DAYS=mon-fri`, `WATCHLIST_REFRESH_TIME=18:30`
  (`TIMEZONE` = Europe/Istanbul). Geçersiz ayar açılışta hata verir.
- `POST /api/watchlist/refresh` aynı işi **arka planda** başlatır ve hemen 202
  döner; ilerleme `GET` yanıtındaki `scheduler.running` ile izlenir (arayüz iş
  sürerken 3 sn'de bir sorar). Çalışırken 409, liste boşken 400.
- Çoklu worker: her worker kendi zamanlayıcısını başlatır. Tekrarı üç katman
  önler: süreç içi `asyncio.Lock`; Postgres `pg_try_advisory_lock` (kilidi
  alamayan atlar); zamanlanmış çalıştırma aynı dilimde zaten yenilenmiş
  hisseleri atlar.
- Arayüz: `components/watchlist-panel.tsx`, `market-strip.tsx`,
  `watchlist-button.tsx`; durum yalnızca React Query'de.

## Alternatifler
- **APScheduler** — tek bir "hafta içi SS:DD" kuralı için yeni bağımlılık;
  iş deposu/misfire özelliklerine ihtiyaç yok.
- **Celery Beat + worker** — ayrı süreç ve kuyruk; tek kullanıcı için ağır.
- **Eklerken tam analiz** — eklemeyi saniyelerce bekletir; şirket sayfasından
  eklendiğinde analiz zaten vardır.
- **Elle tetiklemeyi senkron yapmak** — uzun listede HTTP zaman aşımı riski.
- **Ayrı durum tablosu** — hisse başına tek "son sonuç" yeterli; ayrıntı
  zaten `analysis_snapshots` ve `data_fetch_logs`'ta.

## Sonuçlar
- Listedeki hisseler her iş günü kapanıştan sonra yeni snapshot alır
  (ADR-005), skor değişimi bu sayede anlamlı.
- Sunucu planlanan anda kapalıysa o çalıştırma telafi edilmez; bir sonraki
  dilimde çalışır.
- Çalıştırma durumu (`running`, son rapor) bellekte: çoklu worker'da `GET`
  başka worker'a düşerse "çalışıyor" görünmeyebilir. Hisse bazındaki sonuç
  DB'de kalıcı. SQLite'ta (testler) advisory lock yok, yalnızca süreç içi kilit.
- Hisse başına ayrı zaman aşımı yok; sağlayıcıların kendi HTTP zaman
  aşımlarına güveniliyor.
- Uyarı/bildirim motoru kapsam dışı. Özet hisse başına iki snapshot okur;
  liste büyürse tek sorguya geçilmeli.
