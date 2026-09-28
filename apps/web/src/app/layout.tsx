import type { Metadata } from "next";
import { AppHeader } from "@/components/app-header";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ADVS · 행정 제출서류 사전 점검", template: "%s | ADVS" },
  description:
    "기업·학생 제출에 필요한 서류를 업로드하고 제출 전 자동 점겁니다.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-dvh">
        <Providers>
          <div className="flex min-h-dvh flex-col">
            <AppHeader />
            <main className="mx-auto w-full max-w-shell flex-1 px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
