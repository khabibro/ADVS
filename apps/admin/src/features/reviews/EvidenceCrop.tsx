"use client";

import { useState } from "react";
import { pageImageUrl } from "@/lib/api";
import { reviewCopy as t } from "@/lib/copy";

interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

const PAD_X = 0.08;
const PAD_Y = 0.025;
const MAX_W = 560;
const MAX_H = 170;

/** The part of the page image the value was read from; the whole page when no position is known. */
export function EvidenceCrop({
  documentId,
  page,
  box,
  size,
  caption,
}: {
  documentId: string;
  page: number;
  box: Box | null;
  size: { width: number; height: number } | null;
  caption: string;
}) {
  const [failed, setFailed] = useState(false);
  const src = pageImageUrl(documentId, page);
  if (failed) {
    return <p className="text-sm text-muted-foreground">{t.detail.noImage}</p>;
  }
  if (!box || !size) {
    return (
      <figure className="space-y-1">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt={`${caption} (페이지 전체)`}
          className="max-h-80 w-auto rounded border border-border"
          onError={() => setFailed(true)}
          src={src}
        />
        <figcaption className="text-xs text-muted-foreground">
          {t.detail.noBox}
        </figcaption>
      </figure>
    );
  }
  const x = Math.max(0, box.x - PAD_X);
  const y = Math.max(0, box.y - PAD_Y);
  const w = Math.min(1 - x, box.width + 2 * PAD_X);
  const h = Math.min(1 - y, box.height + 2 * PAD_Y);
  // Shown size in px, fixed so the aspect ratio (and with it the crop) is never distorted.
  const aspect = (w * size.width) / (h * size.height);
  const shownWidth = Math.round(Math.min(MAX_W, MAX_H * aspect));
  return (
    <figure className="space-y-1">
      <div
        className="relative max-w-full overflow-hidden rounded border border-border bg-muted"
        role="img"
        aria-label={caption}
        style={{ aspectRatio: `${aspect}`, width: shownWidth }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt=""
          className="absolute max-w-none"
          onError={() => setFailed(true)}
          src={src}
          style={{
            width: `${100 / w}%`,
            left: `${(-x / w) * 100}%`,
            top: `${(-y / h) * 100}%`,
          }}
        />
      </div>
      <figcaption className="text-xs text-muted-foreground">{caption}</figcaption>
    </figure>
  );
}
