"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { Button } from "@advs/ui";
import { api } from "@/services/api";

export function UploadDocumentsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  return (
    <section className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">서류 업로드</h1>
      <label className="flex min-h-44 cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-muted">
        <Upload className="h-8 w-8" />
        <span>{file ? file.name : "PDF, PNG, JPG, JPEG 파일 선택"}</span>
        <input className="sr-only" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      </label>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <Button
        disabled={!file}
        onClick={async () => {
          try {
            if (!file) return;
            const document = await api.uploadDocument(id, file);
            await api.processDocument(document.id);
            router.push(`/projects/${id}/documents/${document.id}`);
          } catch {
            setError("업로드 또는 처리 중 오류가 발생했습니다.");
          }
        }}
      >
        업로드 및 처리
      </Button>
    </section>
  );
}

