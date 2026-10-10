"use client";

import { usePageInfo } from "@/lib/queries";
import { api } from "@/services/api";
import type { Evidence } from "@/types/api";

/**
 * The part of the original page a value was read from, with the exact box highlighted. The box
 * is the API's `normalized_box` (fractions of the page); when the API could not place it, the
 * page number and the recognised text are shown instead of a guess.
 */
export function EvidenceCrop({
  documentId,
  evidence,
  className = "",
}: {
  documentId: string;
  evidence: Evidence[];
  className?: string;
}) {
  const pages = usePageInfo(documentId);
  // A value is usually found next to its label; both are evidence and are shown together.
  const first = evidence.find((e) => e.normalized_box) ?? evidence[0];
  const placed = evidence.filter((e) => e.normalized_box && e.page_number === first?.page_number);
  const page = pages.data?.find((p) => p.page_number === first?.page_number);

  if (!first) return null;
  if (placed.length === 0 || !page) {
    return (
      <div className={`rounded-md bg-muted p-3 text-sm ${className}`}>
        <p className="text-xs text-muted-foreground">
          {first.page_number}페이지 · {first.source_kind === "embedded_pdf_text" ? "PDF 내장 텍스트" : "인식한 글자"}
          {pages.isPending && placed.length > 0 ? " · 원본 이미지를 불러오는 중입니다." : ""}
        </p>
        <p className="mt-1 whitespace-pre-wrap break-words">{evidence.map((e) => e.source_text).join(" ")}</p>
      </div>
    );
  }

  const boxes = placed.map((e) => e.normalized_box!);
  const left = Math.min(...boxes.map((b) => b.x));
  const top = Math.min(...boxes.map((b) => b.y));
  const right = Math.max(...boxes.map((b) => b.x + b.width));
  const bottom = Math.max(...boxes.map((b) => b.y + b.height));
  // Show the line(s) with a little context around them.
  const x0 = Math.max(0, left - 0.03);
  const y0 = Math.max(0, top - 0.012);
  const w = Math.min(1 - x0, right - left + 0.06);
  const h = Math.min(1 - y0, bottom - top + 0.024);
  const ratio = (w * page.width) / (h * page.height);

  return (
    <figure className={className}>
      <div
        className="relative w-full overflow-hidden rounded-md border border-border bg-white"
        data-testid="evidence-crop"
        style={{ aspectRatio: String(ratio) }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt={`${first.page_number}페이지의 인식 위치`}
          className="absolute left-0 top-0 max-w-none select-none"
          draggable={false}
          src={api.pageImageUrl(documentId, first.page_number)}
          style={{
            width: `${100 / w}%`,
            transform: `translate(${-x0 * 100}%, ${-y0 * 100}%)`,
            transformOrigin: "top left",
          }}
        />
        {boxes.map((box, index) => (
          <span
            aria-hidden="true"
            className="absolute rounded-sm border-2 border-amber-500 bg-amber-300/25"
            key={index}
            style={{
              left: `${((box.x - x0) / w) * 100}%`,
              top: `${((box.y - y0) / h) * 100}%`,
              width: `${(box.width / w) * 100}%`,
              height: `${(box.height / h) * 100}%`,
            }}
          />
        ))}
      </div>
      <figcaption className="mt-1 text-xs text-muted-foreground">
        {first.page_number}페이지 · {first.source_kind === "embedded_pdf_text" ? "PDF 내장 텍스트" : "인식한 글자"}:{" "}
        {placed.map((e) => e.source_text).join(" ")}
      </figcaption>
    </figure>
  );
}
