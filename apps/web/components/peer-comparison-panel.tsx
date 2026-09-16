"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import Link from "next/link";
import { ApiError, getPeerComparison, type PeerCompanyMetric, type PeerComparisonResult } from "@/lib/api-peers";
import { formatMultiple, formatNumber } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";

const INSUFFICIENT_PEERS_REASONS: Record<string, string> = {
  no_other_companies_refreshed_in_industry_or_sector:
    "Bu grupta henüz başka bir şirket refresh edilmemiş — sistemdeki tüm şirketler arasında bu sektör/endüstriden ikinci bir örnek yok.",
};

function insufficientPeersMessage(reason: string | null): string {
  if (!reason) return "Karşılaştırma için yeterli veri henüz oluşmadı.";
  return (
    INSUFFICIENT_PEERS_REASONS[reason] ?? "Karşılaştırma için yeterli veri henüz oluşmadı."
  );
}

export function PeerComparisonPanel({ ticker }: { ticker: string }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["peer-comparison", ticker],
    queryFn: () => getPeerComparison(ticker),
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Peer Comparison" subtitle="Benzer şirketlerle karşılaştırma" />
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <Loader2 className="animate-spin" size={14} />
          Peer karşılaştırması yükleniyor...
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    // A 404 means the ticker itself has never been refreshed — the parent
    // page's own precondition. Treat it as "nothing to show yet" rather
    // than an error; the page-level state already communicates this.
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    return (
      <Card>
        <CardHeader title="Peer Comparison" subtitle="Benzer şirketlerle karşılaştırma" />
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <AlertTriangle size={14} className="text-[var(--warning)]" />
          Peer karşılaştırması yüklenemedi
        </CardBody>
      </Card>
    );
  }

  if (!data) return null;

  return <PeerComparisonContent data={data} />;
}

function PeerComparisonContent({ data }: { data: PeerComparisonResult }) {
  const { sector, industry, peer_group_basis, peer_count, insufficient_peers, insufficient_peers_reason } = data;

  if (insufficient_peers) {
    const groupLabel = sector ?? industry ?? "Bu sektörde";
    const otherLabel = industry ?? sector;
    return (
      <Card>
        <CardHeader title="Peer Comparison" subtitle="Benzer şirketlerle karşılaştırma" />
        <CardBody>
          <p className="text-sm text-foreground">
            {groupLabel} için henüz karşılaştırılabilecek başka bir şirket analiz edilmemiş.
            {otherLabel ? ` Başka bir ${otherLabel} şirketi refresh edildiğinde burada karşılaştırma görünecek.` : " Başka bir şirket refresh edildiğinde burada karşılaştırma görünecek."}
          </p>
          <p className="mt-2 text-xs text-muted">{insufficientPeersMessage(insufficient_peers_reason)}</p>
        </CardBody>
      </Card>
    );
  }

  const basisSubtitle =
    peer_group_basis === "industry"
      ? `${industry ?? "Bu endüstri"} içinde ${peer_count} şirketle karşılaştırılıyor`
      : peer_group_basis === "sector"
        ? `${industry ?? "Bu endüstri"} için yeterli veri yok, ${sector ?? "bu sektördeki"} sektöründeki ${peer_count} şirketle karşılaştırılıyor`
        : `${peer_count} şirketle karşılaştırılıyor`;

  const deltaTone: "positive" | "negative" | "neutral" =
    data.overall_score_vs_median === null
      ? "neutral"
      : data.overall_score_vs_median > 0
        ? "positive"
        : data.overall_score_vs_median < 0
          ? "negative"
          : "neutral";

  const deltaText =
    data.overall_score_vs_median === null
      ? null
      : `${data.overall_score_vs_median > 0 ? "+" : ""}${formatNumber(data.overall_score_vs_median, 1)}`;

  return (
    <Card>
      <CardHeader title="Peer Comparison" subtitle={basisSubtitle} />
      <CardBody className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            label="Overall Score"
            value={formatNumber(data.this_company.overall_score, 0)}
            hint={deltaText ? `Medyan: ${formatNumber(data.median_overall_score, 0)} (${deltaText})` : `Medyan: ${formatNumber(data.median_overall_score, 0)}`}
            tone={deltaTone}
            help="Bu şirketin 0-100 genel skoru, aynı sektördeki diğer şirketlerin skor medyanıyla kıyaslanıyor. Yeşil = medyanın üstünde, kırmızı = altında."
          />
          <StatTile
            label="P/E"
            value={formatMultiple(data.this_company.pe)}
            hint={`Medyan: ${formatMultiple(data.median_pe)}`}
            help="Fiyat/Kazanç oranı — bu şirketin çarpanı, sektör medyanına göre yüksek mi düşük mü?"
          />
          <StatTile
            label="P/B"
            value={formatMultiple(data.this_company.pb)}
            hint={`Medyan: ${formatMultiple(data.median_pb)}`}
            help="Fiyat/Defter Değeri oranı — bu şirketin çarpanı, sektör medyanına göre yüksek mi düşük mü?"
          />
          <StatTile
            label="EV/EBITDA"
            value={formatMultiple(data.this_company.ev_ebitda)}
            hint={`Medyan: ${formatMultiple(data.median_ev_ebitda)}`}
            help="Firma Değeri/FAVÖK oranı — borç seviyesinden bağımsız bir değerleme çarpanı, sektör medyanına göre yüksek mi düşük mü?"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-xs">
            <thead>
              <tr className="text-left text-muted">
                <th className="pb-2 font-medium">Şirket</th>
                <th className="pb-2 font-medium">Score</th>
                <th className="pb-2 font-medium">P/E</th>
                <th className="pb-2 font-medium">P/B</th>
                <th className="pb-2 font-medium">EV/EBITDA</th>
              </tr>
            </thead>
            <tbody>
              {data.peers.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-2 text-muted">
                    Listelenecek peer bulunamadı.
                  </td>
                </tr>
              )}
              {data.peers.map((peer) => (
                <PeerRow key={peer.ticker} peer={peer} />
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}

function PeerRow({ peer }: { peer: PeerCompanyMetric }) {
  return (
    <tr className="border-t border-border">
      <td className="py-1.5 pr-3">
        <Link href={`/company/${peer.ticker}`} className="font-medium text-[var(--accent)] hover:underline">
          {peer.ticker}
        </Link>
        <span className="ml-1.5 text-muted">{peer.name}</span>
      </td>
      <td className="py-1.5 pr-3 text-foreground">
        {peer.overall_score !== null ? <Badge tone="neutral">{formatNumber(peer.overall_score, 0)}</Badge> : "—"}
      </td>
      <td className="py-1.5 pr-3 text-foreground">{formatMultiple(peer.pe)}</td>
      <td className="py-1.5 pr-3 text-foreground">{formatMultiple(peer.pb)}</td>
      <td className="py-1.5 text-foreground">{formatMultiple(peer.ev_ebitda)}</td>
    </tr>
  );
}
