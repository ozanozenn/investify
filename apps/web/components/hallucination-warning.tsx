import { AlertTriangle } from "lucide-react";
import { flaggedNumbers } from "@/lib/analysis";
import type { LLMAnalysis } from "@/lib/types";

/** Yapay zekâ metninde, LLM'e verilen analiz verisinde karşılığı
 *  bulunamayan sayılar (ADR-003 halüsinasyon kontrolü). Kontrol yalnızca
 *  uyarıdır — analiz yine gösterilir, ama okuyucu hangi rakamlara
 *  güvenmemesi gerektiğini görür. Bayrak yoksa hiçbir şey çizilmez. */
export function HallucinationWarning({ meta }: { meta: LLMAnalysis["_meta"] | undefined }) {
  const flags = meta?.hallucination_flags ?? [];
  if (flags.length === 0) return null;

  const numbers = flaggedNumbers(flags);
  const count = numbers.length > 0 ? numbers.length : flags.length;

  return (
    <div
      role="note"
      className="mt-3 flex items-start gap-2 rounded-md border border-[color-mix(in_srgb,var(--warning)_45%,var(--border))] px-3 py-2 text-xs"
    >
      <AlertTriangle size={14} className="mt-0.5 shrink-0 text-[var(--warning)]" />
      <div className="space-y-0.5">
        <p className="font-medium text-foreground">
          Bu metinde analiz verisinde bulunmayan {count} sayı tespit edildi
          {numbers.length > 0 && (
            <>
              : <span className="font-mono">{numbers.join(" · ")}</span>
            </>
          )}
        </p>
        <p className="text-muted">
          Bu rakamlar deterministik verilerle doğrulanamadı; metni bu rakamlar açısından temkinli okuyun.
          {meta?.hallucination_retry && " Yapay zekâdan bir kez düzeltme istendi, ancak tamamen giderilemedi."}
        </p>
      </div>
    </div>
  );
}
