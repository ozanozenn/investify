"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { DcfPanel } from "@/components/dcf-panel";
import { Disclaimer } from "@/components/disclaimer";
import { HistoricalComparisonPanel } from "@/components/historical-comparison-panel";
import { NavBar } from "@/components/nav-bar";
import { NewsPanel } from "@/components/news-panel";
import { OutlookCard } from "@/components/outlook-card";
import { PeerComparisonPanel } from "@/components/peer-comparison-panel";
import { VerdictCard } from "@/components/verdict-card";
import { Badge, toneForScore } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { BigScore, ScoreBar } from "@/components/ui/score-bar";
import { StatTile } from "@/components/ui/stat-tile";
import { ApiError, getCompanyAnalysis, refreshCompanyAnalysis } from "@/lib/api";
import { formatCompact, formatDateTime, formatMultiple, formatNumber, formatPercent, formatRelativeTime } from "@/lib/format";
import type { CategoryScore } from "@/lib/types";

const MACRO_HELP: Record<string, string> = {
  policy_rate: "TCMB'nin belirlediği referans faiz oranı. Yüksek faiz genelde kredi/yatırım maliyetini artırır, ekonomiyi yavaşlatır.",
  cpi_yoy: "Tüketici Fiyat Endeksi'nin yıllık değişimi — yani resmi enflasyon oranı.",
  usdtry: "1 ABD Doları kaç Türk Lirası ediyor. Dövizle borcu/geliri olan şirketleri doğrudan etkiler.",
  eurtry: "1 Euro kaç Türk Lirası ediyor. Dövizle borcu/geliri olan şirketleri doğrudan etkiler.",
};

const CATEGORY_LABELS: Record<string, string> = {
  FINANCIAL_RESULT: "Finansal Sonuç",
  DIVIDEND: "Temettü",
  INVESTMENT: "Yatırım",
  CONTRACT: "Sözleşme",
  MANAGEMENT: "Yönetim",
  CAPITAL: "Sermaye",
  OTHER: "Diğer",
};

export default function CompanyDetailPage() {
  const params = useParams<{ ticker: string }>();
  const ticker = params.ticker.toUpperCase();
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["company-analysis", ticker],
    queryFn: () => getCompanyAnalysis(ticker),
  });

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const fresh = await refreshCompanyAnalysis(ticker);
      queryClient.setQueryData(["company-analysis", ticker], fresh);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="min-h-screen pb-16">
      <NavBar showSearch />

      <div className="mx-auto max-w-6xl px-4 pt-4">
        {isLoading && <LoadingState ticker={ticker} />}
        {isError && <ErrorState ticker={ticker} error={error as Error} />}
        {data && (
          <CompanyDetail
            data={data}
            ticker={ticker}
            onRefresh={handleRefresh}
            refreshing={refreshing}
          />
        )}
      </div>
    </div>
  );
}

function LoadingState({ ticker }: { ticker: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-32 text-muted">
      <Loader2 className="animate-spin" size={22} />
      <p className="text-sm">
        {ticker} için veri toplanıyor ve analiz ediliyor — piyasa verisi, finansal tablolar, KAP,
        makro ve LLM yorumu gerçek zamanlı hesaplanıyor.
      </p>
    </div>
  );
}

function ErrorState({ ticker, error }: { ticker: string; error: Error }) {
  const detail = error instanceof ApiError ? `${error.status}: ${error.message}` : error.message;
  return (
    <div className="mx-auto mt-16 max-w-lg rounded-lg border border-border bg-surface p-6 text-center">
      <AlertTriangle className="mx-auto mb-3 text-[var(--warning)]" size={28} />
      <h2 className="text-sm font-semibold">{ticker} için analiz alınamadı</h2>
      <p className="mt-2 text-xs text-muted">{detail}</p>
    </div>
  );
}

type CompanyData = NonNullable<ReturnType<typeof useQuery<Awaited<ReturnType<typeof getCompanyAnalysis>>>>["data"]>;

function CompanyDetail({
  data,
  ticker,
  onRefresh,
  refreshing,
}: {
  data: CompanyData;
  ticker: string;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const { company, market, metrics, valuation, scores, macro, disclosures, analysis, data_quality, sources, unsupported_reason, versions } = data;

  const whatMattersNow = [...analysis.key_catalysts.slice(0, 3), ...analysis.key_risks.slice(0, 2)].slice(0, 5);

  return (
    <div className="space-y-4">
      <HeaderSection
        company={company}
        market={market}
        ticker={ticker}
        dataQuality={data_quality}
        onRefresh={onRefresh}
        refreshing={refreshing}
      />

      {unsupported_reason && (
        <Card className="border-[color-mix(in_srgb,var(--warning)_45%,var(--border))]">
          <CardBody className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 shrink-0 text-[var(--warning)]" size={18} />
            <p className="text-sm text-foreground">{unsupported_reason}</p>
          </CardBody>
        </Card>
      )}

      {data.verdict && <VerdictCard verdict={data.verdict} />}

      <Card>
        <CardHeader title="Yapay Zekâ Özeti" subtitle={analysis._meta.llm_is_mocked ? "Mock LLM — OPENAI_API_KEY veya GEMINI_API_KEY tanımlı değil" : `Model: ${analysis._meta.llm_model}`} />
        <CardBody>
          <p className="text-sm leading-relaxed text-foreground">{analysis.executive_summary}</p>
        </CardBody>
      </Card>

      <SectionLabel>Neden? — Skor ve değerleme</SectionLabel>

      <Card>
        <CardHeader title="Skor Kartı" subtitle={`Deterministik skorlama motoru ${versions.scoring_engine}`} />
        <CardBody className="grid gap-4 sm:grid-cols-[auto_1fr]">
          <BigScore
            score={scores.overall}
            label="Genel"
            help="0-100 arası tek bir özet puan. Aşağıdaki 5 kategorinin ağırlıklı ortalamasıdır — şirketin sayılarla ne kadar sağlıklı göründüğünü tek bakışta özetler. Bir alım/satım tavsiyesi değildir."
          />
          <div className="grid gap-3 sm:grid-cols-2">
            {(["growth", "profitability", "balance_sheet", "cash_flow", "valuation"] as const).map((key) => (
              <ScoreBar
                key={key}
                label={CATEGORY_LABEL[key] ?? key}
                score={(scores[key] as CategoryScore).score}
                help={CATEGORY_HELP[key]}
              />
            ))}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Değerleme" subtitle={`Son ${valuation.history_years_used} yıl tarihsel karşılaştırma`} />
        <CardBody className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <ValuationTile
            label="F/K"
            current={valuation.pe}
            historical={valuation.pe_historical_median}
            ratio={valuation.pe_vs_history_ratio}
            help="Fiyat/Kazanç oranı — hissenin fiyatı, şirketin hisse başına yıllık kârının kaç katı? Yüksek olması genelde 'pahalı' veya 'yüksek büyüme bekleniyor' anlamına gelir."
          />
          <ValuationTile
            label="PD/DD"
            current={valuation.pb}
            historical={valuation.pb_historical_median}
            ratio={valuation.pb_vs_history_ratio}
            help="Piyasa Değeri/Defter Değeri oranı — hissenin fiyatı, şirketin muhasebe defterindeki özkaynak değerinin kaç katı?"
          />
          <ValuationTile
            label="FD/FAVÖK"
            current={valuation.ev_ebitda}
            historical={valuation.ev_ebitda_historical_median}
            ratio={valuation.ev_ebitda_vs_history_ratio}
            help="Firma Değeri/FAVÖK oranı — borç ve nakit farkını da hesaba katarak şirketin ne kadara 'satın alınabileceğini', ürettiği faaliyet kârına oranlar. Farklı borç seviyesindeki şirketleri kıyaslamak için F/K'dan daha adildir."
          />
        </CardBody>
      </Card>

      <DcfPanel ticker={ticker} currentPrice={market.price} currency={market.currency} />

      <div className="grid gap-4 lg:grid-cols-2">
        <HistoricalComparisonPanel ticker={ticker} />
        <PeerComparisonPanel ticker={ticker} />
      </div>

      <SectionLabel>Detaylar — Finansallar ve yapay zekâ yorumu</SectionLabel>

      <Card>
        <CardHeader title="Finansal Göstergeler" subtitle={`${metrics.as_of_period} dönemi itibarıyla`} />
        <CardBody className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Yıllık Gelir Büyümesi" value={formatPercent(metrics.revenue_growth_yoy)} help="Son yıllık dönemin bir önceki yıla göre ciro büyümesi." />
          <StatTile label="3 Yıllık Ort. Büyüme (BYBO)" value={formatPercent(metrics.revenue_cagr_3y)} help="Son 3 yıllık bileşik yıllık büyüme oranı." />
          <StatTile label="FAVÖK Marjı" value={formatPercent(metrics.ebitda_margin)} help="FAVÖK / Hasılat." />
          <StatTile label="Net Kâr Marjı" value={formatPercent(metrics.net_margin)} help="Net Kâr / Hasılat." />
          <StatTile label="Özkaynak Kârlılığı (ROE)" value={formatPercent(metrics.roe)} help="Net Kâr / Ortalama Özkaynak." />
          <StatTile
            label="Net Borç / FAVÖK"
            value={formatMultiple(metrics.net_debt_to_ebitda)}
            tone={metrics.net_debt_to_ebitda !== null && metrics.net_debt_to_ebitda > 3 ? "negative" : "neutral"}
            help="Net Borç / FAVÖK — kaldıraç göstergesi. Düşük daha sağlıklıdır."
          />
          <StatTile label="Borç / Özkaynak" value={formatMultiple(metrics.debt_to_equity)} help="Toplam Borç / Özkaynak." />
          <StatTile label="Serbest Nakit Akışı Marjı" value={formatPercent(metrics.fcf_margin)} help="Serbest Nakit Akışı / Hasılat." />
        </CardBody>
      </Card>

      {whatMattersNow.length > 0 && (
        <Card>
          <CardHeader title="ŞU AN ÖNEMLİ OLANLAR" />
          <CardBody>
            <ul className="grid gap-2 sm:grid-cols-2">
              {whatMattersNow.map((item, i) => (
                <li key={i} className="rounded-md bg-surface-hover px-3 py-2 text-xs text-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader title="Yatırım Görünümü" />
        <CardBody className="grid gap-3 sm:grid-cols-3">
          <OutlookCard title="Kısa Vade (0-6 ay)" horizon={analysis.short_term} />
          <OutlookCard title="Orta Vade (6-24 ay)" horizon={analysis.medium_term} />
          <OutlookCard title="Uzun Vade (2-5+ yıl)" horizon={analysis.long_term} />
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Yatırım Tezi" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <ThesisList title="Olumlu Senaryo" items={analysis.bull_case} tone="positive" />
          <ThesisList title="Olumsuz Senaryo" items={analysis.bear_case} tone="negative" />
          <ThesisList title="Katalizörler" items={analysis.key_catalysts} tone="accent" />
          <ThesisList title="Riskler" items={analysis.key_risks} tone="warning" />
          <ThesisList title="Tezi Geçersiz Kılacak Faktörler" items={analysis.thesis_breakers} tone="negative" full />
        </CardBody>
      </Card>

      <SectionLabel>Bağlam — Haberler, KAP ve makro</SectionLabel>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader title="Son KAP Açıklamaları" subtitle="kap.org.tr" />
          <CardBody className="space-y-2">
            {disclosures.length === 0 && <p className="text-xs text-muted">KAP verisi bulunamadı.</p>}
            {disclosures.map((d, i) => (
              <a
                key={i}
                href={d.source_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-surface-hover"
              >
                <div className="min-w-0">
                  <div className="truncate text-foreground">{d.title}</div>
                  <div className="mt-0.5 text-muted">{formatDateTime(d.published_at)}</div>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <Badge tone="neutral">{CATEGORY_LABELS[d.category] ?? d.category}</Badge>
                  <ExternalLink size={12} className="text-muted" />
                </div>
              </a>
            ))}
          </CardBody>
        </Card>

        <NewsPanel ticker={ticker} />

        <Card>
          <CardHeader title="Makroekonomik Görünüm" subtitle="TCMB EVDS / piyasa" />
          <CardBody className="grid grid-cols-2 gap-3">
            {macro.map((m) => (
              <StatTile
                key={m.code}
                label={m.label + (m.is_mock ? " (mock)" : "")}
                value={m.code.includes("try") ? formatNumber(m.value, 2) : formatPercent(m.value / 100, 1)}
                hint={formatRelativeTime(m.observation_date)}
                help={MACRO_HELP[m.code] ?? "Şirketle doğrudan ilgili olmayan, genel ekonomik ortamı gösteren bir makro gösterge."}
              />
            ))}
          </CardBody>
        </Card>
      </div>

      {analysis.what_to_watch.length > 0 && (
        <Card>
          <CardHeader title="TAKİP EDİLECEKLER" />
          <CardBody>
            <ul className="space-y-1.5">
              {analysis.what_to_watch.map((item, i) => (
                <li key={i} className="text-sm text-foreground">
                  · {item}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader title="Kaynaklar" subtitle="Bu bilgi nereden geldi?" />
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-xs">
            <thead>
              <tr className="text-left text-muted">
                <th className="pb-2 font-medium">Alan</th>
                <th className="pb-2 font-medium">Kaynak</th>
                <th className="pb-2 font-medium">Alındı</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="py-1.5 pr-3 text-foreground">{s.field}</td>
                  <td className="py-1.5 pr-3">
                    {s.source_url ? (
                      <a href={s.source_url} target="_blank" rel="noreferrer" className="text-[var(--accent)] hover:underline">
                        {s.source} {s.is_mock && "(mock)"}
                      </a>
                    ) : (
                      <span className={s.is_mock ? "text-[var(--warning)]" : "text-foreground"}>
                        {s.source} {s.is_mock && "(mock)"}
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 text-muted">{formatRelativeTime(s.fetched_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      <Disclaimer />
    </div>
  );
}

const CATEGORY_LABEL: Record<string, string> = {
  growth: "Büyüme",
  profitability: "Kârlılık",
  balance_sheet: "Bilanço",
  cash_flow: "Nakit Akışı",
  valuation: "Değerleme",
};

const CATEGORY_HELP: Record<string, string> = {
  growth: "Şirket ne kadar hızlı büyüyor? Ciro/kâr artış oranlarına bakar.",
  profitability: "Şirket sattığından ne kadar kâr çıkarabiliyor? Kâr marjları ve özkaynak getirisine (ROE) bakar.",
  balance_sheet: "Şirketin borç yükü ne kadar sağlıklı? Net Borç/FAVÖK, Borç/Özkaynak gibi kaldıraç göstergelerine bakar.",
  cash_flow: "Şirket kâğıt üzerindeki kârı gerçek nakde çevirebiliyor mu? Serbest nakit akışı ve nakit dönüşüm oranına bakar.",
  valuation: "Şirketin borsa fiyatı, kendi tarihsel ortalamasına göre pahalı mı ucuz mu?",
};

function HeaderSection({
  company,
  market,
  ticker,
  dataQuality,
  onRefresh,
  refreshing,
}: {
  company: CompanyData["company"];
  market: CompanyData["market"];
  ticker: string;
  dataQuality: CompanyData["data_quality"];
  onRefresh: () => void;
  refreshing: boolean;
}) {
  return (
    <Card>
      <CardBody className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-tabular text-xl font-bold text-foreground">{ticker}</h1>
            {company.sector && <Badge tone="neutral">{company.sector}</Badge>}
            {company.industry && <Badge tone="neutral">{company.industry}</Badge>}
          </div>
          <p className="mt-1 text-sm text-muted">{company.name}</p>
          {company.description && (
            <p className="mt-2 max-w-xl text-xs leading-relaxed text-muted line-clamp-2">
              {company.description}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <div className="text-right">
            <div className="font-tabular text-2xl font-semibold text-foreground">
              {market.price ? `${market.price.toFixed(2)} ${market.currency}` : "—"}
            </div>
            <div className="mt-0.5 text-xs text-muted">
              Piyasa Değeri {formatCompact(market.market_cap, market.currency)}
            </div>
          </div>
          <div className="text-right text-xs text-muted">
            <div>Güncellendi: {formatRelativeTime(market.as_of)}</div>
            <div className="mt-0.5 flex items-center justify-end gap-1">
              Veri Kalitesi
              <InfoTooltip text="Bu analizin arkasındaki verinin ne kadar tam, güncel ve kapsamlı olduğunun özeti (0-100). Düşükse bazı veri kaynaklarına o an ulaşılamamış olabilir — analiz sonucu eksik veriyle üretilmiş olabilir demektir." />
              <Badge tone={toneForScore(dataQuality.overall * 100)}>{(dataQuality.overall * 100).toFixed(0)}</Badge>
            </div>
          </div>
          <a
            href={`https://tr.tradingview.com/chart/?symbol=${encodeURIComponent(`BIST:${ticker}`)}`}
            target="_blank"
            rel="noopener noreferrer"
            title="Hissenin fiyat grafiğini TradingView'da yeni sekmede açar — teknik analizi orada kendin yapabilirsin."
            className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-hover"
          >
            <ExternalLink size={13} />
            TradingView&apos;da Aç
          </a>
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-hover disabled:opacity-50"
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Yenileniyor..." : "Yenile"}
          </button>
        </div>
      </CardBody>
      {dataQuality.warnings.length > 0 && (
        <div className="flex flex-wrap gap-1.5 border-t border-border px-4 py-2">
          {dataQuality.warnings.map((w, i) => (
            <Badge key={i} tone="warning">
              {w}
            </Badge>
          ))}
        </div>
      )}
    </Card>
  );
}

function ValuationTile({
  label,
  current,
  historical,
  ratio,
  help,
}: {
  label: string;
  current: number | null;
  historical: number | null;
  ratio: number | null;
  help?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2.5">
      <div className="flex items-center gap-1 text-[11px] text-muted">
        {label}
        {help && <InfoTooltip text={help} />}
      </div>
      <div className="mt-1 font-tabular text-lg font-semibold text-foreground">{formatMultiple(current)}</div>
      <div className="mt-1 text-[11px] text-muted">
        Tarihsel medyan: <span className="font-tabular">{formatMultiple(historical)}</span>
      </div>
      {ratio !== null && (
        <div className="mt-0.5 flex items-center gap-1 text-[11px]">
          <span className={ratio > 1.15 ? "text-[var(--negative)]" : ratio < 0.9 ? "text-[var(--positive)]" : "text-muted"}>
            Tarihsele göre {ratio > 1 ? "+" : ""}
            {((ratio - 1) * 100).toFixed(0)}%
          </span>
          <InfoTooltip text="Şirketin şu anki çarpanı, kendi son yıllardaki tipik (medyan) çarpanından ne kadar farklı. Pozitif = şu an tarihine göre daha pahalı, negatif = daha ucuz." />
        </div>
      )}
    </div>
  );
}

function ThesisList({
  title,
  items,
  tone,
  full = false,
}: {
  title: string;
  items: string[];
  tone: "positive" | "negative" | "warning" | "accent";
  full?: boolean;
}) {
  return (
    <div className={full ? "sm:col-span-2" : ""}>
      <div className="mb-1.5 flex items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</span>
        <Badge tone={tone}>{items.length}</Badge>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted">Bulgu yok.</p>
      ) : (
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li key={i} className="text-xs leading-relaxed text-foreground">
              · {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h2 className="pt-4 text-xs font-semibold uppercase tracking-wide text-muted">{children}</h2>;
}
