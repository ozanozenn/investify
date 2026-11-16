import Link from "next/link";
import { Disclaimer } from "@/components/disclaimer";
import { MarketStrip } from "@/components/market-strip";
import { NavBar } from "@/components/nav-bar";
import { SearchBox } from "@/components/search-box";
import { WatchlistPanel } from "@/components/watchlist-panel";

const QUICK_TICKERS = ["THYAO", "ASELS", "FROTO", "TUPRS", "GARAN", "SISE", "AKBNK", "EREGL"];

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 pb-16 pt-10">
        <section className="flex flex-col items-center gap-5">
          <div className="text-center">
            <h1 className="text-2xl font-semibold text-foreground sm:text-3xl">
              BIST Yatırım Zekâsı
            </h1>
            <p className="mt-2 text-sm text-muted">
              Bir şirket kodu girin — kanıta dayalı, izlenebilir yatırım araştırma ekranını görün.
            </p>
          </div>

          <div className="w-full max-w-xl">
            <SearchBox autoFocus size="lg" />
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2">
            {QUICK_TICKERS.map((t) => (
              <Link
                key={t}
                href={`/company/${t}`}
                className="rounded-full border border-border bg-surface px-3 py-1.5 font-tabular text-xs font-medium text-muted hover:border-[var(--accent)] hover:text-foreground"
              >
                {t}
              </Link>
            ))}
          </div>
        </section>

        <MarketStrip />

        <WatchlistPanel />
      </main>

      <footer className="px-6 pb-8">
        <Disclaimer />
      </footer>
    </div>
  );
}
