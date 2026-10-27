// LLM analizinin (analysis_json) gösterim yardımcıları. Hesaplama yok —
// yalnızca hangi alanın gösterileceğini seçer; eski (v1-v3) ve yeni (v4)
// snapshot şekilleri birlikte desteklenir.
import type { LLMAnalysis } from "@/lib/types";

/** "ŞU AN ÖNEMLİ OLANLAR": v4'te LLM bunu sıralı olarak kendisi verir.
 *  Yalnızca alan hiç yoksa (v1-v3 snapshot) eski katalizör/risk dilimine
 *  düşülür; v4'te boş liste bilinçli bir "yok" demektir. */
export function getWhatMattersNow(analysis: LLMAnalysis): string[] {
  if (analysis.what_matters_now) return analysis.what_matters_now;
  return [...(analysis.key_catalysts ?? []).slice(0, 3), ...(analysis.key_risks ?? []).slice(0, 2)].slice(0, 5);
}

// apps/api/app/llm/hallucination_guard.py `_flag` biçimi:
// "unverified number '<sayı>' in: <metin>"
const FLAG_LITERAL_RE = /^unverified number '([^']*)'/;

/** Halüsinasyon bayraklarındaki sayı metinleri, tekrarsız ve sırası korunarak. */
export function flaggedNumbers(flags: string[]): string[] {
  const out: string[] = [];
  for (const flag of flags) {
    const literal = FLAG_LITERAL_RE.exec(flag)?.[1];
    if (literal && !out.includes(literal)) out.push(literal);
  }
  return out;
}
