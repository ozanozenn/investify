import { Disclaimer } from "@/components/disclaimer";
import { MarketDisclosuresPanel } from "@/components/market-disclosures-panel";
import { MarketNewsPanel } from "@/components/market-news-panel";
import { NavBar } from "@/components/nav-bar";

export default function HaberlerPage() {
  return (
    <div className="min-h-screen pb-16">
      <NavBar />

      <div className="mx-auto max-w-6xl px-4 pt-6">
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-foreground">Haberler</h1>
          <p className="mt-1 text-sm text-muted">
            Tüm BIST şirketlerine ait en güncel KAP açıklamaları ve genel piyasa haberleri.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <MarketDisclosuresPanel />
          <MarketNewsPanel />
        </div>

        <div className="mt-8">
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}
