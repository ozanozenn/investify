// Hüküm etiketlerinin (ADR-011) Türkçe karşılıkları ve rozet tonları.
// components/verdict-card.tsx ile aynı eşleme; izleme listesi gibi kompakt
// görünümler buradan kullanır.

import type { VerdictConfidence, VerdictPrice, VerdictQuality, VerdictSignal } from "./types";

export type VerdictTone = "positive" | "negative" | "warning" | "neutral";

export interface VerdictLabel {
  label: string;
  tone: VerdictTone;
}

export const PRICE_LABELS: Record<VerdictPrice, VerdictLabel> = {
  UCUZ: { label: "Ucuz", tone: "positive" },
  MAKUL: { label: "Makul", tone: "warning" },
  PAHALI: { label: "Pahalı", tone: "negative" },
};

export const QUALITY_LABELS: Record<VerdictQuality, VerdictLabel> = {
  GUCLU: { label: "Güçlü", tone: "positive" },
  ORTA: { label: "Orta", tone: "warning" },
  ZAYIF: { label: "Zayıf", tone: "negative" },
};

export const CONFIDENCE_LABELS: Record<VerdictConfidence, VerdictLabel> = {
  YUKSEK: { label: "Yüksek", tone: "positive" },
  ORTA: { label: "Orta", tone: "warning" },
  DUSUK: { label: "Düşük", tone: "negative" },
};

export const SIGNAL_LABELS: Record<VerdictSignal, VerdictLabel> = {
  AL: { label: "AL", tone: "positive" },
  TUT: { label: "TUT", tone: "warning" },
  SAT: { label: "SAT", tone: "negative" },
};
