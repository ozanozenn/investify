"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { searchCompanies } from "@/lib/api";

export function SearchBox({ autoFocus = false, size = "md" }: { autoFocus?: boolean; size?: "md" | "lg" }) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 180);
    return () => clearTimeout(t);
  }, [query]);

  const { data: results = [] } = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => searchCompanies(debounced),
    enabled: debounced.trim().length > 0,
  });

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function goTo(ticker: string) {
    setOpen(false);
    setQuery("");
    router.push(`/company/${ticker.toUpperCase()}`);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (results[0]) {
      goTo(results[0].ticker);
    } else if (query.trim()) {
      goTo(query.trim());
    }
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <form onSubmit={onSubmit}>
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 focus-within:border-[var(--accent)]">
          <Search size={size === "lg" ? 18 : 15} className="text-muted" />
          <input
            autoFocus={autoFocus}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            placeholder="Ticker ara (örn. THYAO, ASELS, GARAN...)"
            className={`w-full bg-transparent py-2.5 text-foreground outline-none placeholder:text-muted ${
              size === "lg" ? "text-base py-3.5" : "text-sm"
            }`}
          />
        </div>
      </form>
      {open && results.length > 0 && (
        <ul className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-border bg-surface shadow-xl">
          {results.map((r) => (
            <li key={r.ticker}>
              <button
                type="button"
                onClick={() => goTo(r.ticker)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface-hover"
              >
                <span className="font-tabular font-semibold text-foreground">{r.ticker}</span>
                <span className="truncate pl-3 text-xs text-muted">{r.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
