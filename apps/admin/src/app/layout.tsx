import type { Metadata } from "next";
import Link from "next/link";
import { copy } from "@/lib/copy";
import "./globals.css";

export const metadata: Metadata = {
  title: "ADVS 관리",
  description: "점검 기준 관리",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <header className="border-b border-border">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-4 text-sm">
            <Link className="font-semibold" href="/">
              ADVS Admin
            </Link>
            <Link href="/reviews">{copy.nav.reviews}</Link>
            <Link href="/reviews/log">{copy.nav.reviewLog}</Link>
            <Link href="/workflows">{copy.nav.workflows}</Link>
            <Link href="/audit">{copy.nav.audit}</Link>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
      </body>
    </html>
  );
}
