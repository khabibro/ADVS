"use client";

import { cn } from "@advs/ui";
import { ExternalLink, FileCheck2, FolderKanban, LayoutDashboard, ListChecks } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { WEB_URL } from "@/lib/labels";

const NAV = [
  { href: "/", label: "대시보드", icon: LayoutDashboard, match: (path: string) => path === "/" },
  { href: "/workflows", label: "점검 기준 관리", icon: ListChecks, match: (path: string) => path.startsWith("/workflows") },
  { href: "/projects", label: "제출 건 현황", icon: FolderKanban, match: (path: string) => path.startsWith("/projects") },
];

export function Sidebar() {
  const pathname = usePathname() ?? "/";
  return (
    <aside className="flex w-full shrink-0 flex-col bg-sidebar text-sidebar-foreground lg:min-h-screen lg:w-60">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-md bg-white/10 text-white">
          <FileCheck2 aria-hidden="true" className="h-5 w-5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-white">ADVS 관리자</p>
          <p className="text-xs text-sidebar-foreground/70">제출서류 사전 점검</p>
        </div>
      </div>
      <nav aria-label="관리자 메뉴" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:pb-0">
        {NAV.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition",
                active ? "bg-white/10 text-white" : "text-sidebar-foreground/80 hover:bg-white/5 hover:text-white",
              )}
              href={item.href}
              key={item.href}
            >
              <Icon aria-hidden="true" className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto hidden border-t border-white/10 px-5 py-4 lg:block">
        <a
          className="inline-flex items-center gap-1.5 text-xs text-sidebar-foreground/80 hover:text-white"
          href={WEB_URL}
          rel="noreferrer"
          target="_blank"
        >
          신청 화면 열기
          <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
        </a>
      </div>
    </aside>
  );
}
