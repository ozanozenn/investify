# Devir Notu
_Güncelleme: 2026-10-11 · Branch: development_

## Hedef
Feature freeze kaldırıldı (kullanıcı, 2026-10-11): projeyi "bambaşka bir
boyuta" taşımak. Yol haritası ve öncelik sırası `docs/PROJECT_STATUS.md`'de.

## Tamamlanan
- **TradingView mini grafikleri kaldırıldı** (`2e56537`) — "Finansal
  Performans" kartı eksen/değer göstermiyordu; yerine şirket başlığında
  `BIST:<ticker>` grafiğini yeni sekmede açan "TradingView'da Aç" butonu.
  `lightweight-charts` bağımlılığı silindi.
- **Arama hatası düzeltildi** (`d78d981`) — `search_companies` DB'ye yalnızca
  statik indeks 0 sonuç verirse bakıyordu; artık her zaman birleştiriyor
  (tekrarsız, ≤10, şirket adıyla da arar). 2 regresyon testi.
- **Durum envanteri** (`6269ab0`) — `docs/PROJECT_STATUS.md`: faz yüzdeleri
  (P1 %93, P2 %95, P3 %3, P4 %45, kalite turu %85, P5+ %3), 32 özellik,
  25 fix/teknik borç.
- Yukarıdaki 3 commit bulut oturumunda ayrı branch'te
  (`claude/vigilant-galileo-qlaxlf`) yapılmıştı; `development`'a merge
  edildi (`9170480`), yerelde doğrulandı: pytest 109 passed, ruff temiz,
  web typecheck + build geçti.
- Önceki oturum: token ölçümü + çalışma kılavuzu commit'lendi (`0d5cb76`).

## Devam eden / yarım kalan
- **Tam BIST şirket listesi (KAP'tan ~500 şirket)** — bulut ortamında
  `www.kap.org.tr` ağ politikasıyla engelli. Ya bulut ortamına izin
  eklenecek (Network access → Custom → `www.kap.org.tr`, ayrıca
  `query1.finance.yahoo.com`) ya da liste bu Mac'te yerel script ile
  çekilecek. Kural gereği önce canlı doğrulama.
- `docs/WORKFLOW_GUIDE.md` ve `docs/PROJECT_STATUS.md`, `AGENTS.md`
  dokümantasyon haritasına henüz bağlı değil.

## Sıradaki adımlar (PROJECT_STATUS.md önerisi)
1. Temizlik turu + CI: `outlook-card.tsx` LLM "Güven %X" skorunu
   göstermesin (deterministik skora geç), `auth_dev_bypass` varsayılanı
   `True`, Redis ya kullanılsın ya kaldırılsın, `page.tsx`'teki frontend
   hesaplaması backend'e, bayat dokümanlar (README, ARCHITECTURE,
   DATA_SOURCES, TECHNICAL_DEBT).
2. Tam BIST evreni + taksonomi tablosunun genişletilmesi.
3. Arka plan refresh + zamanlayıcı → ardından watchlist/dashboard/alarm.
4. `/feature` akışını ilk gerçek büyük işte dene (hâlâ uçtan uca çalışmadı).

## Alınan kararlar
- TradingView grafikleri dönüştürülmedi, **kaldırıldı** (kullanıcı kararı);
  teknik analiz kullanıcıya TradingView üzerinden bırakıldı.
- Daemon kalıcı yapılmadı; bayat kilit için **taşı, silme**.
- Her iş bitiminde `/handoff`; `/clear` yalnızca handoff'tan sonra.
- Frontend test altyapısı ertelendi, gerekçe `ADR-010`'da.

## Açık sorular / riskler
- Token örüntüsü tek oturumda gözlendi; 2-3 oturum daha doğrulanmalı.
- `.claude/scheduled_tasks.lock` çalışma ağacında silinmiş görünüyor
  (commit edilmedi, dokunulmadı).

## Dikkat
- **Aynı anda iki oturum (Claude uygulaması/bulut + VS Code) çalıştırma** —
  bulut oturumu ayrı `claude/*` branch'ine commit atar, yerel `development`
  onu görmez; iş bitince merge gerekir (2026-10-11'de bu yaşandı).
- Yeni skill/agent eklenince oturumu yeniden başlat.
- MCP `CONNECTION_CLOSED` olursa önce `/tmp/cbm-daemon-501/` içindeki sahipsiz
  `*.lock` dosyalarına bak; `codebase-memory-mcp cli index_status` ile tanıla.
