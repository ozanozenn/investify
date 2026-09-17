import Link from "next/link";
import { Disclaimer } from "@/components/disclaimer";
import { SearchBox } from "@/components/search-box";
import { ThemeToggle } from "@/components/theme-toggle";

const QUICK_TICKERS = ["THYAO", "ASELS", "FROTO", "TUPRS", "GARAN", "SISE", "AKBNK", "EREGL"];

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between px-6 py-4">
        <span className="text-sm font-semibold tracking-wide text-muted">INVESTIFY</span>
        <ThemeToggle />
      </header>

      <main className="flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-24">
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
      </main>

      <footer className="px-6 pb-8">
        <Disclaimer />
      </footer>
    </div>
  );
}
