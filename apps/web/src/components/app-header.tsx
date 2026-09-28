import { FileCheck2, Plus } from "lucide-react";
import Link from "next/link";

const NAV_LINKS = [
  { href: "/projects", label: "제출 건" },
  { href: "/projects/new", label: "새 제출 건" },
] as const;

const linkClass =
  "rounded-md px-2.5 py-2 text-sm font-medium text-muted-foreground transition hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-white/95 backdrop-blur">
      <nav
        aria-label="주요 메뉴"
        className="mx-auto flex h-16 max-w-[1360px] items-center justify-between gap-3 px-4 sm:px-6 lg:px-8"
      >
        <div className="flex min-w-0 items-center gap-5">
          <Link
            className="flex shrink-0 items-center gap-2 rounded font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
            href="/projects"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <FileCheck2 aria-hidden="true" className="h-5 w-5" />
            </span>
            <span className="text-base">ADVS</span>
          </Link>
          <span className="hidden truncate border-l border-border pl-5 text-sm text-muted-foreground md:inline">
            행정 제출서류 사전 점검
          </span>
        </div>

        <div className="flex items-center gap-1 sm:gap-2">
          <div className="hidden items-center gap-1 sm:flex">
            {NAV_LINKS.map((link) => (
              <Link className={linkClass} href={link.href} key={link.href}>
                {link.label}
              </Link>
            ))}
          </div>
          <Link
            aria-label="새 제출 건"
            className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 sm:hidden"
            href="/projects/new"
          >
            <Plus aria-hidden="true" className="h-4 w-4" />
            <span>새 제출</span>
          </Link>
        </div>
      </nav>
    </header>
  );
}
