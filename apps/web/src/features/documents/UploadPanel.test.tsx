import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { UploadPanel } from "./UploadPanel";

vi.mock("@/services/api", () => ({
  api: { uploadDocument: vi.fn(), processDocument: vi.fn() },
}));

const onUploaded = vi.fn();

function stored(overrides: Record<string, unknown> = {}) {
  return {
    id: "doc-1",
    original_filename: "사업자등록증.pdf",
    mime_type: "application/pdf",
    size_bytes: 2048,
    processing_status: "UPLOADED",
    document_type: "UNKNOWN",
    document_type_display_name: "알 수 없는 문서",
    classification_confidence: null,
    classification_meta: null,
    error_code: null,
    error_message: null,
    created_at: "2026-09-28T00:00:00Z",
    ...overrides,
  } as never;
}

function pdf(name: string, lastModified = 1) {
  return new File(["%PDF-1.4"], name, {
    type: "application/pdf",
    lastModified,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.uploadDocument).mockResolvedValue(stored());
  vi.mocked(api.processDocument).mockResolvedValue(
    stored({
      processing_status: "COMPLETED",
      document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
      document_type_display_name: "사업자등록증",
    }),
  );
});

describe("UploadPanel", () => {
  it("offers a PDF-scoped, multi-select file input", () => {
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    const input = screen.getByLabelText("PDF 파일 추가") as HTMLInputElement;
    expect(input.multiple).toBe(true);
    expect(input.accept).toContain("pdf");
  });

  it("queues four PDFs selected in one interaction", async () => {
    const user = userEvent.setup();
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    await user.upload(screen.getByLabelText("PDF 파일 추가"), [
      pdf("사업자등록증.pdf", 1),
      pdf("중소기업확인서.pdf", 2),
      pdf("국세 납세증명서.pdf", 3),
      pdf("4대 사회보험료 완납증명서.pdf", 4),
    ]);
    expect(screen.getByText("4개 파일을 추가했습니다.")).toBeInTheDocument();
    for (const name of [
      "사업자등록증.pdf",
      "중소기업확인서.pdf",
      "국세 납세증명서.pdf",
      "4대 사회보험료 완납증명서.pdf",
    ]) {
      expect(screen.getByTitle(name)).toBeInTheDocument();
    }
    expect(screen.getByTestId("upload-submit")).toHaveTextContent("4개 파일 업로드");
  });

  it("refuses the same local file twice in one queue", async () => {
    const user = userEvent.setup();
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    const input = screen.getByLabelText("PDF 파일 추가");
    await user.upload(input, pdf("같은파일.pdf", 7));
    await user.upload(input, pdf("같은파일.pdf", 7));
    expect(
      screen.getByText("이미 목록에 있는 파일 1개는 중복으로 제외했습니다."),
    ).toBeInTheDocument();
    expect(screen.getByTestId("upload-submit")).toHaveTextContent("1개 파일 업로드");
  });

  it("rejects a non-PDF selection with a Korean message and keeps valid files", async () => {
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    // `applyAccept: false` lets the component's own validation be exercised.
    await userEvent.upload(
      screen.getByLabelText("PDF 파일 추가") as HTMLInputElement,
      [pdf("정상.pdf", 1), new File(["x"], "메모.txt", { type: "text/plain" })] as File[],
      { applyAccept: false },
    );
    expect(
      screen.getByText(/1개를 추가하지 못했습니다: PDF 파일만 선택할 수 있습니다./),
    ).toBeInTheDocument();
    expect(screen.getByTestId("upload-submit")).toHaveTextContent("1개 파일 업로드");
  });

  it("lets the same file be selected again after the queue resolves", async () => {
    const user = userEvent.setup();
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    const input = screen.getByLabelText("PDF 파일 추가") as HTMLInputElement;
    await user.upload(input, pdf("재선택.pdf", 5));
    await user.click(screen.getByTestId("upload-submit"));
    await waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(1));
    // The native input must be reset, otherwise selecting the same file again
    // would not fire a change event.
    expect(input.value).toBe("");
    // The completed item resolved out of the queue, so the same file can be
    // selected again and must fire a fresh change event.
    await user.upload(input, pdf("재선택.pdf", 5));
    expect(screen.getByTitle("재선택.pdf")).toBeInTheDocument();
    expect(screen.getByTestId("upload-submit")).toHaveTextContent("1개 파일 업로드");
  });

  it("disables the primary action while uploading and shows the pending label", async () => {
    const user = userEvent.setup();
    let release: (value: unknown) => void = () => undefined;
    vi.mocked(api.uploadDocument).mockReturnValue(
      new Promise((resolve) => {
        release = resolve;
      }) as never,
    );
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    await user.upload(screen.getByLabelText("PDF 파일 추가"), [pdf("a.pdf", 1), pdf("b.pdf", 2)]);
    await user.click(screen.getByTestId("upload-submit"));

    const submit = screen.getByTestId("upload-submit");
    expect(submit).toBeDisabled();
    expect(submit).toHaveTextContent("업로드 중...");
    release(stored());
  });

  it("issues no duplicate mutation when the action is activated repeatedly", async () => {
    let release: (value: unknown) => void = () => undefined;
    vi.mocked(api.uploadDocument).mockReturnValue(
      new Promise((resolve) => {
        release = resolve;
      }) as never,
    );
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    await userEvent.upload(
      screen.getByLabelText("PDF 파일 추가"),
      [pdf("a.pdf", 1), pdf("b.pdf", 2), pdf("c.pdf", 3)],
    );
    const submit = screen.getByTestId("upload-submit");
    // Rapid activation, the way a user triple-clicks a button.
    await Promise.all([
      userEvent.click(submit),
      userEvent.click(submit).catch(() => undefined),
      userEvent.click(submit).catch(() => undefined),
      userEvent.click(submit).catch(() => undefined),
    ]);
    expect(api.uploadDocument).toHaveBeenCalledTimes(1);

    release(stored());
    // The single click continues through the rest of the queue exactly once.
    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalledTimes(3));
    expect(api.processDocument).toHaveBeenCalledTimes(3);
  });

  it("runs upload and processing as separate visible stages per file", async () => {
    const user = userEvent.setup();
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    await user.upload(screen.getByLabelText("PDF 파일 추가"), pdf("a.pdf", 1));
    await user.click(screen.getByTestId("upload-submit"));
    await waitFor(() => expect(api.processDocument).toHaveBeenCalledWith("doc-1"));
    expect(api.uploadDocument).toHaveBeenCalledWith("p", expect.any(File));
    await waitFor(() =>
      expect(screen.getByText(/1개 파일의 분석이 끝났습니다/)).toBeInTheDocument(),
    );
    expect(onUploaded).toHaveBeenCalledWith(
      expect.objectContaining({ document_type: "BUSINESS_REGISTRATION_CERTIFICATE" }),
    );
  });

  it("shows a Korean error and keeps the queue when an upload fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadDocument).mockRejectedValue(
      new ApiError(400, "FILE_TOO_LARGE"),
    );
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    await user.upload(screen.getByLabelText("PDF 파일 추가"), pdf("큰파일.pdf", 1));
    await user.click(screen.getByTestId("upload-submit"));
    expect(
      await screen.findByText("파일 크기가 허용 범위를 초과했습니다."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /실패한 1개 다시 시도/ })).toBeEnabled();
  });

  it("keeps other files intact when one fails and retries only the failed one", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadDocument)
      .mockResolvedValueOnce(stored({ id: "doc-ok" }))
      .mockRejectedValueOnce(new ApiError(400, "CORRUPT_DOCUMENT"))
      .mockResolvedValue(stored({ id: "doc-retry" }));
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    await user.upload(screen.getByLabelText("PDF 파일 추가"), [
      pdf("정상.pdf", 1),
      pdf("손상.pdf", 2),
    ]);
    await user.click(screen.getByTestId("upload-submit"));

    expect(
      await screen.findByText("PDF 파일을 읽을 수 없습니다."),
    ).toBeInTheDocument();
    // The healthy file still completed and left the queue.
    expect(screen.getByText(/1개 파일의 분석이 끝났습니다/)).toBeInTheDocument();
    expect(screen.getByTitle("손상.pdf")).toBeInTheDocument();
    expect(screen.queryByTitle("정상.pdf")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /실패한 1개 다시 시도/ }));
    await waitFor(() =>
      expect(api.uploadDocument).toHaveBeenLastCalledWith("p", expect.any(File)),
    );
    expect(api.uploadDocument).toHaveBeenCalledTimes(3);
  });

  it("does not offer the upload action when there is nothing to send", () => {
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    expect(screen.queryByTestId("upload-submit")).not.toBeInTheDocument();
  });

  it("allows removing a waiting file but not an in-flight one", async () => {
    const user = userEvent.setup();
    let release: (value: unknown) => void = () => undefined;
    vi.mocked(api.uploadDocument).mockReturnValue(
      new Promise((resolve) => {
        release = resolve;
      }) as never,
    );
    renderWithQuery(<UploadPanel onUploaded={onUploaded} projectId="p" />);
    await user.upload(screen.getByLabelText("PDF 파일 추가"), [
      pdf("대기.pdf", 1),
      pdf("실행.pdf", 2),
    ]);
    await user.click(
      screen.getByRole("button", { name: "대기.pdf 목록에서 제거" }),
    );
    expect(screen.queryByTitle("대기.pdf")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("upload-submit"));
    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalled());
    expect(
      screen.getByRole("button", { name: "실행.pdf 목록에서 제거" }),
    ).toBeDisabled();
    release(stored());
  });
});
