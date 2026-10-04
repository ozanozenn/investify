# Çalışma Kılavuzu — Agent Sistemini Verimli Kullanmak

Bu kılavuz, kurduğumuz agent altyapısını (hook'lar, skill'ler, subagent'lar,
graph araçları, devir notu) **ne zaman, nasıl ve neden** kullanacağını anlatır.
Amaç iki şey: iş kalitesini korumak ve token maliyetini düşük tutmak.
Maliyetin neden bu şekilde olduğu için `docs/TOKEN_USAGE.md`'ye bak.

> Doğrulama notu: Aşağıdaki her komut/parça repodaki gerçek dosyalarla ve
> aracın kendi yardım çıktısıyla kontrol edildi. "Test edilmedi" diye
> işaretli bir şey varsa önce kendin dene.

---

## 1. Üç temel kural

1. **Bağlamı küçük tut.** Uzun oturum = her tur daha pahalı. Konu bitince
   `/handoff` → `/clear`.
2. **Ucuz yolu önce dene.** Soru bir sembolü/çağıranı soruyorsa graph aracı,
   metin arıyorsan grep, sadece bir dosyaya bakacaksan doğrudan oku. Geniş
   keşfi ana oturumda yapma.
3. **Büyük işi devret, küçük işi kendin yap.** Subagent'ın kendi sıfırdan
   keşfi ve raporu da faturalanır; küçük bir düzeltme için kurulum maliyeti
   işin kendisinden büyük olabilir.

---

## 2. Günlük akış (her oturum)

**Oturum başı** — otomatik: `SessionStart` hook'u `docs/handoff/CURRENT.md`'yi
ve `git status`/son commit'leri bağlama ekler. Senin yapman gereken:
- Devir notunun "Sıradaki adımlar"ına bak, oradan devam et.
- Yeni skill/agent eklendiyse oturumu **yeniden başlat** (oturum ortasında
  eklenen skill görünmez — bunu bizzat yaşadık).

**İş sırasında:**
- Büyük iş → `/feature <açıklama>` (bkz. §4).
- Küçük düzeltme → doğrudan söyle, akışa sokma.
- Mimari bir karar çıktıysa → `/adr <başlık>` (bkz. §5).

**Mola / konu değişimi / oturum sonu:**
1. `/handoff` — devir notunu güncelle (60 satır sınırı var, skill bunu uygular).
2. Uzun mola veya konu değişimi → `/clear`. Hook yeni bağlamda devir notunu
   geri yükler; bağlamın 600k'dan küçük bir noktadan başlar.
3. Model değiştirmen gerekiyorsa (`/model`) önce `/handoff`, sonra yeni oturum.
   Oturum ortasında model değişimi önbelleği sıfırlar.

---

## 3. Komutlar — ne zaman hangisi

| Komut | Ne yapar | Ne zaman | Dikkat |
|---|---|---|---|
| `/handoff` | `docs/handoff/CURRENT.md`'yi yeniden yazar, eskisini arşivler | Her iş bloğu bitince, oturum kapanırken, `/clear`'dan önce | İçerik "bu işin" olmalı; başka işe ait eski notu arşivler |
| `/clear` | Bağlamı sıfırlar | Uzun mola, konu değişimi | **Handoff'tan sonra.** Yoksa durum kaybolur |
| `/compact` | Bağlamı özetleyerek sıkıştırır | Oturum uzun ama aynı konudaysa | Özet kaybı olabilir; kritik kararları ADR/handoff'a yaz. Sonrasında hook devir notunu yeniden enjekte eder |
| `/feature <açıklama>` | 7 aşamalı akış (keşif→plan→uygulama→test→inceleme→dokümantasyon→devir) | 3+ dosya veya veri modeli değişikliği | Küçük iş için kullanma — tören maliyeti işi aşar |
| `/adr <başlık>` | `docs/adr/ADR-NNN-*.md` oluşturur (sıradaki numara) | Geri dönmesi pahalı karar alındığında | Başlık anahtarları İngilizce, gövde serbest. Bilmediğin alanı uydurmaz, sorar |
| `/model` | Modeli değiştirir | Gerçekten gerekiyorsa | Önbelleği sıfırlar (bkz. TOKEN_USAGE.md) |
| `/cost` | Oturum maliyetini gösterir | Trend izlemek için görev sonunda | Kaba bir göstergedir |
| `/permissions` | İzin kurallarını yönetir | Tekrarlayan onay istemlerini kesmek için | Geniş "her şeye izin" yerine belirli komut kalıpları |

---

## 4. `/feature` — büyük işlerde adım adım

Akış: **Keşif → Plan → Uygulama → Doğrulama → İnceleme → Dokümantasyon → Devir.**

- **Keşif** → codebase-memory agent'ına devredilir (sadece özet döner).
- **Plan** → 3+ dosya veya veri modeli değişikliğinde **sana sunulur, onay beklenir**.
  Burada durmak zorunlu; feature-freeze kuralı da burada devreye girer.
- **Uygulama** → küçük adımlar, her adımda derlenebilir/çalışır durumda.
- **Doğrulama** → `test-runner` (pytest + ruff). En fazla 3 tur, sonra sana döner.
- **İnceleme** → `code-reviewer`. "Kritik" maddeler düzeltilir.
- **Dokümantasyon** → `docs-keeper`. ADR önerisi gelirse `/adr`.
- **Devir** → `/handoff`.

**Ne zaman kullanma:** tek dosyalık düzeltme, metin değişikliği, bilinen bir
hatanın düzeltilmesi. Bunları doğrudan yap, sonra gerekiyorsa `/handoff`.

**Dürüst durum:** Bu akış henüz hiç uçtan uca çalıştırılmadı. İlk gerçek
büyük işte dene, sonra "yardımcı oldu mu, sadece adım mı ekledi" diye değerlendir
ve gerekirse `docs/AGENT_SETUP.md`'deki geri alma prosedürüne göre ayarla
(değişiklik için onay gerekir).

---

## 5. Subagent'lar — ne zaman, nasıl çağrılır

| Agent | Ne için | Ne zaman |
|---|---|---|
| `codebase-memory-scout` | Hızlı, ön-onaylı kod keşfi | "X nerede?" gibi dar sorular |
| `codebase-memory` | Hedefli doğrulama/analiz | "Bu değişiklik neleri etkiler?" |
| `codebase-memory-auditor` | Sınırlı kapsamlı denetim | Dead-code taraması gibi geniş tarama |
| `test-runner` | Test + lint + tip raporu | Büyük değişiklik sonrası |
| `code-reviewer` | Doğruluk/güvenlik/konvansiyon incelemesi | Commit öncesi, büyük işte |
| `docs-keeper` | Dokümanların kodla senkronu | Komut/yapı değiştiğinde |

**Çağırma şablonu** — subagent konuşmanı görmez, bu yüzden her şeyi yaz:
```
Hedef: <ne bulunacak/yapılacak>
Dosya/semboller: <yollar, fonksiyon adları>
Kapsam dışı: <dokunma>
Çıktı formatı: <tablo / 5 madde / GEÇTİ|BAŞARISIZ gibi>
Uzunluk sınırı: <ör. 300 kelime>
```

**Kural:** Subagent'tan dönen ham çıktıyı ana oturuma yapıştırma; sadece özeti
kullan. Bu, bağlamı küçük tutmanın ana yoludur.

---

## 6. Kod keşfi — hangi aracı ne zaman

| Soru | En ucuz yol |
|---|---|
| "Bu fonksiyonu kim çağırıyor?" | `search_graph` / `trace_path` (graph) |
| "Bu sembolün kaynak kodu?" | `get_code_snippet` (graph) |
| "Mimari nasıl?" | `get_architecture` (graph) — bir kere, sonra handoff/ARCHITECTURE.md |
| "Bu bir metin/literal arama" | grep |
| "Bu tek dosyanın içeriği" | doğrudan Read (sadece gereken satır aralığı) |
| "Büyük keşif" | subagent (§5) |

**Graph indeksi bayatlarsa:** `codebase-memory-mcp cli index_status` ile
kontrol et. Yeni yazılmış kod grafikte yoksa `index_repository` çalıştır.

**Bağlantı sorunu:** MCP `CONNECTION_CLOSED` verirse büyük olasılıkla bayat
bir kilit dosyası var — `/tmp/cbm-daemon-501/` altında sahipsiz `*.lock`
dosyaları. Bunu bu oturumda çözdük (kilit dizinini kenara taşıyarak). Tekrar
olursa aynı tanılamayı yap; **silmek yerine taşı**.

**Daemon (kalıcı süreç):** Şu an oturuma bağlı (`daemon status` ile görünür).
`daemon start` kalıcı yapar — bu oturumda bilinçli olarak açmadık, gerekçesi
`docs/TOKEN_USAGE.md`'de değil bu oturumdaki karar notunda. Durdurma komutu
(`daemon stop`) bu sürümde `--help` çıktısında doğrulanmadı; kullanmadan önce kontrol et.

---

## 7. Hook'lar — ne yapar, ne maliyeti

- **`SessionStart`** (`.claude/hooks/session-start.sh`): devir notunu ve git
  durumunu bağlama ekler. Tetiklendiği durumlar: yeni oturum, devam (resume),
  `/clear`, `/compact`. Maliyeti her tetiklenmede ~devir notu boyutu (60 satır).
- **İzin kuralları** (`.claude/settings.json` → `permissions.deny`): `.env*`
  dosyalarını okumayı/yazmayı engeller. Maliyeti yok, güvenlik ağı.

Hook'u kapatmak istersen: `.claude/settings.json`'daki `hooks` bloğunu kaldır.
Bu bir kurulum değişikliği — onay gerekir (bkz. `docs/AGENT_SETUP.md`).

---

## 8. Model seçimi

- Varsayılan: ana oturumda çalıştığın model (`inherit`). Subagent'lar da bunu miras alır.
- Finansal doğruluk kritik bir iş için daha güçlü model: `/model` ile oturum
  başında seç ve o oturumda kal.
- Ortada değiştirme; önce `/handoff`.

---

## 9. Token bütçesi — kısa kontrol listesi

Her büyük adımdan önce:
- [ ] Bağlamda gereksiz büyük çıktı var mı? (Uzun log, büyük dosya) → özet/subagent.
- [ ] Bu iş küçük mü? → doğrudan yap, `/feature` kullanma.
- [ ] Geniş keşif mi? → graph veya subagent.
- [ ] Uzun mola mı var? → önce `/handoff`, sonra `/clear`.
- [ ] Model değişimi mi? → önce `/handoff`, yeni oturum.

Görev sonunda: ne kadar sürdü, hangi araç ne kadar kullanıldı — kısa not
(`docs/TOKEN_USAGE.md`'deki yöntemle). Birkaç görev sonra gerçek örüntü çıkar.

---

## 10. Sık karşılaşılan sorunlar

| Belirti | Neden | Çözüm |
|---|---|---|
| `/feature` "no matching commands" | Skill oturum ortasında eklendi | Oturumu yeniden başlat |
| Graph araçları çalışmıyor | Bayat kilit (`/tmp/cbm-daemon-501/`) | Kilidi kenara taşı, `index_status` ile kontrol et |
| Graph'ta yeni kod yok | İndeks bayat | `index_repository` |
| Devir notu eski görünüyor | `/handoff` çalıştırılmamış | `/handoff` çalıştır |
| Her turda yavaş/pahalı | Büyük bağlam + uzun mola | `/handoff` → `/clear` |
| Sürekli onay istemi | İzin kuralı eksik | `/permissions` ile belirli kalıpları ekle |

---

## 11. Ne zaman neyi güncellemeli

- **Mimari karar** → `/adr` (yeni ADR) veya mevcut ADR'ye "Amended by".
- **Proje kuralı** (her oturumda bilinmesi gereken) → `AGENTS.md` (kısa tut, 120 satır sınırı).
- **Oturumun durumu** → `/handoff` (`docs/handoff/CURRENT.md`).
- **Bilinen açık / borç** → `docs/TECHNICAL_DEBT.md`.
- **Agent kurulumunun kendisi** → önce öner, onay al (`docs/AGENT_SETUP.md`).
