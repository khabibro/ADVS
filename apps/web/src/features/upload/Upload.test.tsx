import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { UploadProvider } from "./UploadProvider";
import { RowUploadButton, UploadDropzone, UploadNotices, UploadQueueList } from "./UploadParts";

vi.mock("@/services/api", () => ({
  api: { uploadRules: vi.fn(), uploadDocument: vi.fn(), processDocument: vi.fn() },
}));

const onChanged = vi.fn();

function doc(overrides: Record<string, unknown> = {}) {
  return {
    id: "doc-1",
    original_filename: "a.pdf",
    mime_type: "application/pdf",
    size_bytes: 10,
    processing_status: "COMPLETED",
    document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
    created_at: "2026-10-10T00:00:00Z",
    ...overrides,
  } as never;
}

function file(name: string, type = "application/pdf", lastModified = 1) {
  return new File(["x"], name, { type, lastModified });
}

function setup(withRow = false) {
  return renderWithQuery(
    <UploadProvider
      onChanged={onChanged}
      projectId="p"
      requirementNames={{
        BUSINESS_REGISTRATION_CERTIFICATE: "사업자등록증",
        SME_CONFIRMATION_CERTIFICATE: "중소기업확인서",
      }}
    >
      <UploadDropzone />
      {withRow ? (
        <RowUploadButton
          documentType="SME_CONFIRMATION_CERTIFICATE"
          replace={false}
          requirementName="중소기업확인서"
        />
      ) : null}
      <UploadQueueList />
      <UploadNotices />
    </UploadProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.uploadRules).mockResolvedValue({
    extensions: [".jpg", ".pdf", ".png", ".webp"],
    mime_types: ["application/pdf", "image/jpeg"],
    max_size_mb: 20,
    max_pages: 30,
  });
  vi.mocked(api.uploadDocument).mockResolvedValue(doc({ processing_status: "UPLOADED" }));
  vi.mocked(api.processDocument).mockResolvedValue(doc());
});

describe("upload", () => {
  it("takes the accepted files from the API and says so", async () => {
    setup();
    const input = (await screen.findByLabelText("서류 파일 선택")) as HTMLInputElement;
    await waitFor(() => expect(input.accept).toBe(".jpg,.pdf,.png,.webp"));
    expect(screen.getByText(/PDF, JPG, PNG, WEBP · 파일당 최대 20MB/)).toBeInTheDocument();
  });

  it("starts uploading as soon as files are chosen, one after the other", async () => {
    const user = userEvent.setup();
    setup();
    const input = await screen.findByLabelText("서류 파일 선택");
    await waitFor(() => expect(input).toBeEnabled());
    await user.upload(input, [file("a.pdf", "application/pdf", 1), file("b.jpg", "image/jpeg", 2)]);
    await waitFor(() => expect(api.processDocument).toHaveBeenCalledTimes(2));
    expect(api.uploadDocument).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("2개 서류의 분석이 끝났습니다.")).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
  });

  it("rejects an unsupported file with what to do and does not call the API", async () => {
    setup();
    const input = await screen.findByLabelText("서류 파일 선택");
    await waitFor(() => expect(input).toBeEnabled());
    await userEvent.upload(input as HTMLInputElement, [file("메모.txt", "text/plain")], {
      applyAccept: false,
    });
    expect(await screen.findByText(/메모\.txt: 지원하지 않는 파일 형식입니다\. PDF, JPG, PNG, WEBP 파일을 선택해 주세요\./)).toBeInTheDocument();
    expect(api.uploadDocument).not.toHaveBeenCalled();
  });

  it("explains a corrupt file and retries it", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadDocument)
      .mockRejectedValueOnce(new ApiError(400, "CORRUPT_DOCUMENT"))
      .mockResolvedValueOnce(doc({ processing_status: "UPLOADED" }));
    setup();
    const input = await screen.findByLabelText("서류 파일 선택");
    await waitFor(() => expect(input).toBeEnabled());
    await user.upload(input, file("깨짐.pdf"));
    expect(await screen.findByRole("alert")).toHaveTextContent("원본에서 다시 저장하거나 스캔해서 올려 주세요");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));
    await waitFor(() => expect(api.processDocument).toHaveBeenCalledTimes(1));
    expect(api.uploadDocument).toHaveBeenCalledTimes(2);
  });

  it("re-analyses without uploading again when only the analysis failed", async () => {
    const user = userEvent.setup();
    vi.mocked(api.processDocument)
      .mockRejectedValueOnce(new ApiError(500, "OCR_TIMEOUT"))
      .mockResolvedValueOnce(doc());
    setup();
    const input = await screen.findByLabelText("서류 파일 선택");
    await waitFor(() => expect(input).toBeEnabled());
    await user.upload(input, file("스캔.pdf"));
    await user.click(await screen.findByRole("button", { name: "다시 분석" }));
    await waitFor(() => expect(api.processDocument).toHaveBeenCalledTimes(2));
    expect(api.uploadDocument).toHaveBeenCalledTimes(1);
  });

  it("tells the user when the backend recognised a different document than the row chosen", async () => {
    const user = userEvent.setup();
    setup(true);
    const row = await screen.findByTestId("row-upload-SME_CONFIRMATION_CERTIFICATE");
    await waitFor(() => expect(screen.getByRole("button", { name: /중소기업확인서 업로드/ })).toBeEnabled());
    await user.upload(row, file("사업자.pdf"));
    const notice = await screen.findByText(/중소기업확인서 칸에 올린 파일은 사업자등록증\(으\)로 인식/);
    expect(notice).toBeInTheDocument();
    expect(within(screen.getByRole("status")).getAllByRole("listitem").length).toBeGreaterThan(0);
  });

  it("opens the file chooser of its own input when the slot button is clicked (mouse and keyboard)", async () => {
    const user = userEvent.setup();
    setup(true);
    const row = (await screen.findByTestId("row-upload-SME_CONFIRMATION_CERTIFICATE")) as HTMLInputElement;
    const opened = vi.fn();
    row.addEventListener("click", opened);
    const button = screen.getByRole("button", { name: /중소기업확인서 업로드/ });
    await waitFor(() => expect(button).toBeEnabled());
    await user.click(button);
    expect(opened).toHaveBeenCalledTimes(1);
    button.focus();
    await user.keyboard("{Enter}");
    await user.keyboard(" ");
    expect(opened).toHaveBeenCalledTimes(3);
  });
});
