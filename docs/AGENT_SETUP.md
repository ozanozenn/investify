# Agent Çalışma Sistemi — Kapsam ve Geri Alma

Bu doküman, 2026-10 tarihinde eklenen agent çalışma sisteminin neden
oluştuğunu, nelerden oluştuğunu, her parçanın gerçek maliyetini ve
gerektiğinde nasıl geri alınacağını kayıt altına alır.

## Geri alma kuralı (bağlayıcı)

> **Bu sistemin hiçbir parçası, proje sahibinin açık onayı olmadan
> kaldırılamaz, devre dışı bırakılamaz veya geri alınamaz.**

Bir oturum/agent bu kurulumun bir parçasını gereksiz, maliyetli veya yanlış
buluyorsa: **önerir, gerekçesini yazar, onay bekler.** Kendiliğinden silmez.
Bu kural, sistemin kendisini değerlendiren agent'ın aynı zamanda onu
kaldırma yetkisine sahip olmaması içindir.

Tersi de geçerli: proje sahibi istediği an, aşağıdaki tariflerle, herhangi
bir parçadan tek başına vazgeçebilir — hepsi düz dosyadır, migration/şema
değişikliği/dış servis bağımlılığı yoktur.

## Ne eklendi ve gerçek maliyeti ne

| Parça | Dosya | Oturum başına token maliyeti |
|---|---|---|
| Proje rehberi (araçtan bağımsız) | `AGENTS.md` | Her oturumda yüklenir — ~1-1.5k |
| Claude Code'a özel kurallar | `CLAUDE.md` | Her oturumda yüklenir — ~0.5k |
| Oturum başı devir enjeksiyonu | `.claude/settings.json` (`hooks`) + `.claude/hooks/session-start.sh` | Her oturum başı **ve her `/compact` sonrası** — uzun oturumlarda katlanır |
| Skill'ler | `.claude/skills/{feature,handoff,adr}/SKILL.md` | **Sıfır** — yalnızca ad+açıklama listelenir, içerik çağrılınca yüklenir |
| Subagent'lar | `.claude/agents/{code-reviewer,test-runner,docs-keeper}.md` | **Sıfır** — ana bağlama girmez, yalnız agent çalışırken kendi bağlamına yüklenir |
| ADR'ler | `docs/adr/ADR-NNN-*.md` | **Sıfır** — okunmadıkça yüklenmez |
| Devir notu | `docs/handoff/CURRENT.md` | Hook açıksa yukarıdaki satıra dahil |

**Sonuç:** "çok dosya eklendi" ≠ "çok token harcanıyor". Sürekli gider yalnız
`AGENTS.md` + `CLAUDE.md` + hook çıktısıdır. Tasarruf gerekirse hedef önce
hook, sonra `AGENTS.md`'nin kısaltılması olmalı — skill/agent/ADR silmek
token kazandırmaz.

## Parça parça geri alma

| Vazgeçilen | Yapılacak | Yan etki |
|---|---|---|
| Bir skill (ör. `/feature`) | `git rm .claude/skills/feature/SKILL.md` | Yok — hiçbir dosya ona bağlı değil |
| Oturum başı hook (token gideri) | `.claude/settings.json`'daki `"hooks"` bloğunu sil (`"permissions"` kalsın) | Devir notu otomatik yüklenmez; elle okunabilir |
| Bir subagent | Dosyayı sil + `CLAUDE.md`'deki tablo satırını çıkar + `.claude/skills/feature/SKILL.md`'de ilgili adımı düzelt | 3 dosya dokunulur |
| Bir ADR | Dosyayı sil + ona referans veren yerleri temizle (`AGENTS.md`, diğer ADR'lerdeki "Amended by"/çapraz atıflar) | Dangling referans kalmasın diye grep şart |
| `AGENTS.md` kuralları | Doğrudan düzenle | Codex gibi diğer araçlar da bunu okuyor — değişiklik hepsini etkiler |

## Tümünü geri alma

Sistem üç ayrı commit hâlinde eklendi, bu yüzden tek tek geri alınabilir:

| Commit | Kapsam |
|---|---|
| `6054b28` | Agent sistemi (AGENTS.md, CLAUDE.md, subagent'lar, skill'ler, hook, handoff) |
| `e817834` | ADR-006…010 + ADR-002 güncellemesi |
| `26c5599` | ARCHITECTURE.md Phase 2-4 senkronu |

`git revert <sha>` ilgili parçayı geri alır. Revert geçmişi silmez, üstüne
ters bir commit yazar — yani karar da, geri alınışı da kayıtta kalır.

## Git'in dışında kalan tek şey

Claude'un oturumlar arası kalıcı hafızası repoda değildir:
`~/.claude/projects/-Users-ozan-projects-investify/memory/`. `git revert`
oraya dokunmaz. Oradaki kayıtlardan (ör. Türkçe-only kuralı, feature freeze,
LLM çıktı stili) vazgeçilecekse ilgili dosyanın **ayrıca** silinmesi/
güncellenmesi gerekir.
