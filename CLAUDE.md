@AGENTS.md

# Claude Code'a özel

## Kod keşfi
- Yapısal sorular (kim çağırıyor, etki alanı, mimari) için önce
  codebase-memory-mcp araçlarını kullan: `get_architecture`, `search_graph`,
  `trace_path`, `detect_changes`. Grep/okuma ile dosya dosya gezme son çare.
- Geniş keşfi ana bağlamda yapma; aşağıdaki agent'lara devret (büyük ölçekli
  işlerde — küçük/orta düzeltmelerde doğrudan sen yap).

## Orkestrasyon
Ana oturum = orkestratör + uygulayıcı. Büyük ölçekli işlerde yan işleri
subagent'lara ver (küçük düzeltmelerde kendin yap):

| İş                              | Agent                      |
|----------------------------------|-----------------------------|
| Hızlı, ön-onaylı kod keşfi       | `codebase-memory-scout`     |
| Hedefli doğrulama / analiz       | `codebase-memory`           |
| Sınırlı kapsamlı denetim (ör. dead-code taraması) | `codebase-memory-auditor` |
| Testleri çalıştır, analiz        | `test-runner`               |
| Değişikliği gözden geçir         | `code-reviewer`             |
| Docs/ADR güncelliği              | `docs-keeper`               |

(`~/.claude/agents/`'daki gerçek adlar bunlar — "Scout/Verify/Auditor"
sadece kavramsal isimlerdi, 2026-10-02'de bu tabloyla netleştirildi.)

Subagent'a görev verirken: hedefi, ilgili dosya/sembolleri ve beklenen çıktı
formatını açıkça yaz. Subagent senin konuşmanı görmez.

## Devir (handoff)
- Oturum başında docs/handoff/CURRENT.md otomatik yüklenir; oradan devam et.
- Anlamlı bir iş bloğu bitince veya bağlam dolmaya yaklaşınca `/handoff` çalıştır.
