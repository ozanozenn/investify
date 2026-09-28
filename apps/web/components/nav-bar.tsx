"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SearchBox } from "@/components/search-box";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/cn";

const NAV_ITEMS = [
  { href: "/", label: "Ana Sayfa" },
  { href: "/haberler", label: "Haberler" },
  { href: "/takvim", label: "Takvim" },
];

export function NavBar({ showSearch = false }: { showSearch?: boolean }) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
        <Link href="/" className="shrink-0 text-sm font-semibold tracking-wide text-muted hover:text-foreground">
          INVESTIFY
        </Link>

        <nav className="flex items-center gap-4">
          {NAV_ITEMS.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "text-sm font-medium transition-colors",
                  active ? "text-foreground" : "text-muted hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {showSearch && (
          <div className="max-w-md flex-1">
            <SearchBox />
          </div>
        )}

        <div className={cn("shrink-0", !showSearch && "ml-auto")}>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
