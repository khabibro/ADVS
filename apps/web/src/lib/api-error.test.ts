import { describe, expect, it } from "vitest";
import {
  ApiError,
  apiErrorMessage,
  isRetryable,
  parseApiErrorResponse,
} from "@/lib/api-error";

describe("parseApiErrorResponse", () => {
  it("reads a structured backend code and message", () => {
    const error = parseApiErrorResponse(400, {
      detail: { code: "INVALID_FILE_TYPE", message: "PDF, PNG, JPG, JPEG files are supported." },
    });
    expect(error.code).toBe("INVALID_FILE_TYPE");
    expect(error.status).toBe(400);
  });

  it("joins FastAPI validation items instead of leaking an array", () => {
    const error = parseApiErrorResponse(422, {
      detail: [
        { msg: "field required", loc: ["body", "name"] },
        { msg: "value is not a valid uuid", loc: ["body", "workflow_id"] },
      ],
    });
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.detail).toBe("field required value is not a valid uuid");
  });

  it("keeps a plain string detail", () => {
    const error = parseApiErrorResponse(404, { detail: "Project not found" });
    expect(error.code).toBe("HTTP_ERROR");
    expect(error.detail).toBe("Project not found");
  });

  it("falls back to HTTP_ERROR for an unknown code or empty body", () => {
    expect(parseApiErrorResponse(500, null).code).toBe("HTTP_ERROR");
    expect(
      parseApiErrorResponse(400, { detail: { code: "SOMETHING_NEW" } }).code,
    ).toBe("HTTP_ERROR");
  });
});

describe("apiErrorMessage", () => {
  it("never exposes technical text for each documented upload failure", () => {
    const cases: Array<[string, string]> = [
      ["INVALID_FILE_TYPE", "PDF 파일만 업로드할 수 있습니다."],
      ["FILE_TOO_LARGE", "파일 크기가 허용 범위를 초과했습니다."],
      ["EMPTY_FILE", "비어 있는 파일은 업로드할 수 없습니다."],
      ["CORRUPT_DOCUMENT", "PDF 파일을 읽을 수 없습니다."],
      ["NETWORK_ERROR", "서버에 연결할 수 없습니다. 네트워크 연결을 확인하고 다시 시도해 주세요."],
    ];
    for (const [code, expected] of cases) {
      expect(apiErrorMessage(new ApiError(400, code as never))).toBe(expected);
    }
  });

  it("uses context-specific copy for processing and verification failures", () => {
    expect(apiErrorMessage(new ApiError(500, "VALIDATION_FAILED"), "verify")).toBe(
      "자동 점검을 완료하지 못했습니다.",
    );
    expect(apiErrorMessage(new ApiError(500, "OCR_TIMEOUT"), "process")).toBe(
      "서류 분석 시간이 초과되었습니다.",
    );
    expect(apiErrorMessage(new ApiError(500, "PROCESSING_FAILED"), "process")).toBe(
      "서류 분석에 실패했습니다.",
    );
  });

  it("keeps the backend reason for a validation failure", () => {
    const error = new ApiError(400, "VALIDATION_FAILED", "CORRECTED requires corrected_value");
    expect(apiErrorMessage(error, "review")).toBe("CORRECTED requires corrected_value");
  });

  it("never renders a raw object, class name, or enum for unknown throwables", () => {
    const hostile = [
      new Error("boom"),
      { detail: { code: "X" } },
      "[object Object]",
      undefined,
      null,
    ];
    for (const throwable of hostile) {
      const message = apiErrorMessage(throwable, "load");
      expect(message).toBe("정보를 불러오지 못했습니다.");
      expect(message).not.toContain("[object");
      expect(message).not.toContain("Error");
    }
  });

  it("falls back to context copy rather than an unmapped backend code", () => {
    const error = new ApiError(500, "SOME_FUTURE_CODE" as never);
    expect(apiErrorMessage(error, "load")).toBe("정보를 불러오지 못했습니다.");
    expect(apiErrorMessage(error, "verify")).toBe("자동 점검을 완료하지 못했습니다.");
  });

  it("keeps the raw backend detail out of Error.message", () => {
    const error = new ApiError(400, "FILE_TOO_LARGE", "max size exceeded");
    expect(error.message).toBe("파일 크기가 허용 범위를 초과했습니다.");
    expect(error.detail).toBe("max size exceeded");
  });
});

describe("isRetryable", () => {
  it("marks transport, server, and OCR provider failures as retryable", () => {
    expect(isRetryable(new ApiError(0, "NETWORK_ERROR"))).toBe(true);
    expect(isRetryable(new ApiError(503, "HTTP_ERROR"))).toBe(true);
    expect(isRetryable(new ApiError(500, "OCR_TIMEOUT"))).toBe(true);
  });

  it("does not mark client validation failures as retryable", () => {
    expect(isRetryable(new ApiError(400, "INVALID_FILE_TYPE"))).toBe(false);
    expect(isRetryable(new ApiError(400, "VALIDATION_FAILED"))).toBe(false);
  });
});
