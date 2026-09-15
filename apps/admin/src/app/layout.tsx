import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "ADVS Admin",
  description: "Administrative configuration shell for ADVS",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <header className="border-b border-border">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-4 text-sm">
            <Link className="font-semibold" href="/">
              ADVS Admin
            </Link>
            <Link href="/document-types">문서 유형</Link>
            <Link href="/checklists">체크리스트</Link>
            <Link href="/rules">검증 규칙</Link>
            <Link href="/projects">프로젝트</Link>
            <Link href="/history">이력</Link>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
      </body>
    </html>
  );
}

