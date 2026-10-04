# Devir Notu
_Güncelleme: 2026-10-02 · Branch: development_

## Hedef
Kullanıcının eklediği genel agent-kurulum taslağını (AGENTS.md, CLAUDE.md,
.claude/agents, .claude/skills, docs/handoff) Investify'ın gerçek kod
tabanına, kurallarına ve mevcut `docs/adr/` sistemine uyarlamak.

## Tamamlanan
- Eski kök `AGENTS.md` (alakasız, test amaçlı) silindi; kitin dosyaları
  gerçek konumlarına taşındı, `investify-claude-kit/` klasörü silindi.
- `AGENTS.md` gerçek, kaynaklı içerikle dolduruldu (91 satır, <120 sınırı).
- `CLAUDE.md`: Scout/Verify/Auditor → gerçek agent adları
  (`codebase-memory-scout` / `codebase-memory` / `codebase-memory-auditor`,
  `~/.claude/agents/`'da doğrulandı) ile düzeltildi.
- `.claude/skills/adr/SKILL.md`: `docs/decisions/` değil `docs/adr/`,
  `ADR-NNN` (3 haneli), başlık anahtarları İngilizce/gövde serbest.
- `docs/ARCHITECTURE.md`'ye Phase 2-4 yapısal ekleri (DCF, peer/diff
  servisleri, Gemini, number_format/context_formatter, market/calendar
  router'ları) işlendi.
- 5 yeni ADR yazıldı: `ADR-006` (Python sürümü/local dev — ADR-001'deki
  boş referansı kapattı), `ADR-007` (tek-kullanıcılı auth), `ADR-008`
  (LLM sağlayıcı zinciri), `ADR-009` (Phase 4 veri kaynakları — `ADR-002`'yi
  "Amended by" ile günceller), `ADR-010` (test stratejisi + repo yapısı:
  monorepo kalıyor, frontend için Vitest+RTL kararı — henüz kurulmadı).
- `docs/TECHNICAL_DEBT.md`'deki mevcut frontend-test-yok notu `ADR-010`'a
  bağlandı (zaten Phase 1'den beri biliniyordu, tekrar yazılmadı).

## Devam eden / yarım kalan
- Hiçbir şey yarım değil — bu iş bloğu tamamlandı.

## Sıradaki adımlar
1. Frontend test altyapısını gerçekten kur (Vitest + React Testing Library,
   bkz. `ADR-010`) — ayrı bir iş olarak planlandı, bu turda yapılmadı.
2. `code-reviewer`/`test-runner`/`docs-keeper` agent'larını ve `/feature`
   akışını ilk büyük ölçekli özellikte gerçekten dene (şimdiye kadar hiç
   kullanılmadı).
3. Kullanıcının "feature freeze / sadece doğrulama" modu hâlâ geçerli —
   yeni özellik başlatmadan önce onayını al (bkz. kalıcı hafıza:
   `feedback_feature_freeze_verification_mode`).

## Alınan kararlar
- Monorepo yapısı korunuyor, ayrı repo'ya geçilmiyor (ADR-010, ADR-001'i
  yeniden teyit ediyor).
- ADR dizini/numaralama hiç değişmiyor (`docs/adr/`, `ADR-NNN`, 3 haneli) —
  kitin `docs/decisions/` önerisi reddedildi, mevcut referansları kırmamak
  için.
- ADR başlık anahtarları (Status/Context/Decision/Consequences) her zaman
  İngilizce kalır, gövde Türkçe/İngilizce serbest.
- Finansal hesaplamalarda `float` kullanımı (Decimal değil) bilinçli bir
  tercih olarak AGENTS.md'ye yazıldı — kitin aksi yöndeki taslak korkuluğu
  kaldırıldı.

## Açık sorular / riskler
- Yok.

## Dikkat
`session-start.sh` hook'u artık her oturum başında/`/compact` sonrası bu
dosyayı ve git durumunu bağlama otomatik ekliyor — küçük bir token maliyeti
var, bilinçli kabul edildi (devamlılık değeri daha yüksek).
