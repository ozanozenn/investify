import { Info } from "lucide-react";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";
import { formatCompact, formatPercent } from "@/lib/format";
import type { BankMetrics } from "@/lib/types";

/**
 * Banka göstergeleri (ADR-014). Bankalarda genel "Finansal Göstergeler"
 * kartının yerine gösterilir. Her sayı backend'deki banka motorundan gelir;
 * bu bileşen yalnızca biçimler, hiçbir şey hesaplamaz.
 */

// Veri sağlayıcıdan gelmeyen kalemlerin Türkçe adları (yalnızca görüntüleme).
const MISSING_LABELS: Record<string, string> = {
  NET_INCOME: "Net kâr",
  EQUITY: "Özkaynak",
  TOTAL_ASSETS: "Toplam aktif",
  NET_INTEREST_INCOME: "Net faiz geliri",
  OPERATING_EXPENSE: "Faaliyet giderleri",
  REVENUE: "Toplam gelir",
  CREDIT_LOSS_PROVISION: "Kredi karşılık gideri",
  LOANS: "Krediler",
  DEPOSITS: "Mevduat",
  no_previous_period: "Önceki yıl verisi",
};

export const BANK_DCF_NOTE =
  "Bankalar için DCF uygulanmaz; değerleme PD/DD ve özkaynak kârlılığı üzerinden yapılır.";

/** Skor kartındaki kategori açıklamalarının banka sürümü. */
export const BANK_CATEGORY_HELP: Record<string, string> = {
  growth: "Banka ne kadar hızlı büyüyor? Net faiz geliri, net kâr ve özkaynak büyümesine bakar.",
  profitability:
    "Banka ne kadar kârlı? Özkaynak kârlılığı (ROE), aktif kârlılığı (ROA) ve yaklaşık net faiz marjına bakar.",
  balance_sheet:
    "Bankanın sermaye tamponu ve kredi riski: özkaynak/toplam aktif, kredi karşılığı yükü ve (veri varsa) kredi/mevduat oranı.",
  cash_flow: "Bankalarda uygulanmaz — bankanın nakit akışı mevduat ve kredi hareketleriyle dalgalanır.",
  valuation: "Bankanın PD/DD ve F/K çarpanları, kendi tarihsel medyanına göre pahalı mı ucuz mu?",
};

export function BankMetricsCard({ metrics, currency }: { metrics: BankMetrics; currency: string }) {
  const missing = metrics.missing_fields.filter((f) => f in MISSING_LABELS).map((f) => MISSING_LABELS[f]);

  return (
    <Card>
      <CardHeader
        title="Banka Göstergeleri"
        subtitle={`${metrics.as_of_period} dönemi itibarıyla · banka motoru ${metrics.engine_version}`}
      />
      <CardBody className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            label="Özkaynak Kârlılığı (ROE)"
            value={formatPercent(metrics.roe)}
            help="Net kâr / ortalama özkaynak. Bankacılıkta en temel kârlılık göstergesidir."
          />
          <StatTile
            label="Aktif Kârlılığı (ROA)"
            value={formatPercent(metrics.roa, 2)}
            help="Net kâr / ortalama toplam aktif — bankanın büyüklüğüne göre ne kadar kâr ürettiği."
          />
          <StatTile
            label="Net Faiz Marjı (yaklaşık)"
            value={formatPercent(metrics.nim_proxy, 2)}
            help="Net faiz geliri / ortalama TOPLAM aktif. Gerçek net faiz marjı yalnızca faiz getirili aktiflere bölünür; veri sağlayıcı bu kalemi vermediği için bu değer gerçek marjdan biraz düşüktür."
          />
          <StatTile
            label="Özkaynak / Toplam Aktif"
            value={formatPercent(metrics.equity_to_assets)}
            help="Varlıkların ne kadarının özkaynakla finanse edildiği — sermaye tamponunun kaba bir göstergesi. Yasal sermaye yeterlilik oranı değildir."
          />
          <StatTile
            label="Net Faiz Geliri Büyümesi"
            value={formatPercent(metrics.nii_growth_yoy)}
            help="Son yılın net faiz gelirinin bir önceki yıla göre değişimi (nominal TL)."
          />
          <StatTile
            label="Net Kâr Büyümesi"
            value={formatPercent(metrics.net_income_growth_yoy)}
            help="Son yılın net kârının bir önceki yıla göre değişimi (nominal TL)."
          />
          <StatTile
            label="Kredi Karşılığı / Net Faiz Geliri"
            value={formatPercent(metrics.provision_to_nii)}
            help="Riskli krediler için ayrılan karşılık giderinin net faiz gelirine oranı. Yüksekse faiz kazancının büyük kısmını kredi riski yiyor demektir."
          />
          <StatTile
            label="Kredi / Mevduat"
            value={formatPercent(metrics.loan_to_deposit)}
            help="Verilen kredilerin toplanan mevduata oranı. Veri sağlayıcı mevduat kalemi vermediğinde hesaplanmaz."
          />
          <StatTile
            label="Gider / Gelir (yaklaşık)"
            value={formatPercent(metrics.cost_income_ratio)}
            help="Faaliyet giderleri / toplam gelir. Payda veri sağlayıcının toplam gelir kalemi olduğu için yaklaşıktır; skora katılmaz."
          />
          <StatTile label="Net Faiz Geliri" value={formatCompact(metrics.latest_net_interest_income, currency)} />
          <StatTile label="Net Kâr" value={formatCompact(metrics.latest_net_income, currency)} />
          <StatTile label="Toplam Aktif" value={formatCompact(metrics.latest_total_assets, currency)} />
        </div>
        {missing.length > 0 && (
          <p className="text-[11px] text-muted">
            Veri sağlayıcıdan gelmeyen kalemler: {missing.join(", ")}. Bu kalemlere dayanan oranlar
            hesaplanmadı (tahmin edilmez).
          </p>
        )}
      </CardBody>
    </Card>
  );
}

/** Bankalarda DCF panelinin yerine gösterilen kısa not. */
export function BankDcfNote() {
  return (
    <Card>
      <CardHeader title="İndirgenmiş Nakit Akışı (DCF)" />
      <CardBody className="flex items-start gap-3">
        <Info className="mt-0.5 shrink-0 text-muted" size={16} />
        <p className="text-sm text-foreground">{BANK_DCF_NOTE}</p>
      </CardBody>
    </Card>
  );
}
