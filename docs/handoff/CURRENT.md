# Devir Notu
_Güncelleme: 2026-10-05 · Branch: development_

## Hedef
Agent altyapısını verimli kullanmayı öğrenmek ve token maliyetini ölçerek
düşürmek. Kılavuz, ölçüm dokümanı ve MCP onarımı bu işin parçası.

## Tamamlanan
- MCP `codebase-memory` bağlantısı onarıldı: bayat kilit `/tmp/cbm-daemon-501/`
  kenara taşındı (silinmedi), indeks yeniden oluşturuldu (1643 düğüm, 5253 kenar).
- Daemon kararı: `daemon start` **açılmadı** (oturuma bağlı kalıyor, 4 MB).
- Token ölçümü: `docs/TOKEN_USAGE.md`. Bulgu: büyük yeniden-yazımların
  %57'si 30+ dk boşluk sonrası; 1-5 dk'da %0; model değişimi önbelleği sıfırlar.
- Çalışma kılavuzu: `docs/WORKFLOW_GUIDE.md`.
- Agent kurulumu commit'lendi ve push edildi (`6054b28`, `e817834`, `26c5599`,
  `14d8e5b`); geri alma prosedürü `docs/AGENT_SETUP.md`.

## Devam eden / yarım kalan
- `docs/TOKEN_USAGE.md` ve `docs/WORKFLOW_GUIDE.md` **commit edilmedi** (untracked).
- `docs/WORKFLOW_GUIDE.md`, `AGENTS.md` dokümantasyon haritasına henüz bağlı değil.

## Sıradaki adımlar
1. Kullanıcı onayıyla: `TOKEN_USAGE.md` + `WORKFLOW_GUIDE.md` commit, AGENTS.md'ye bağlantı.
2. Bir sonraki uzun oturumda token ölçümünü tekrarla, `TOKEN_USAGE.md`'yi doğrula
   (şu an tek oturum verisi var, genelleme yapılmadı).
3. `/feature` akışını ilk gerçek büyük işte dene (hâlâ hiç uçtan uca çalışmadı).

## Alınan kararlar
- Daemon kalıcı yapılmadı: fayda ~8 sn/oturum, risk: arka planda unutulan süreç.
- Bayat kilit için **taşı, silme** — geri alınabilirlik.
- Her iş bitiminde `/handoff`; `/clear` yalnızca handoff'tan sonra.
- Frontend test altyapısı ertelendi, gerekçe `ADR-010`'da.

## Açık sorular / riskler
- MCP bağlantısı oturum yeniden başlatılınca yeniden test edilmeli.
- Token örüntüsü tek oturumda gözlendi; 2-3 oturum daha doğrulanmalı.

## Dikkat
- Yeni skill/agent eklenince oturumu yeniden başlat (oturum ortasında görünmez).
- MCP `CONNECTION_CLOSED` olursa önce `/tmp/cbm-daemon-501/` içindeki sahipsiz
  `*.lock` dosyalarına bak; `codebase-memory-mcp cli index_status` ile tanıla.
- Bu oturumdaki bilgi: `codebase-memory-mcp` CLI'si daemon yokken geçici
  daemon başlatır, her komut ~başlangıç bedeli öder.
