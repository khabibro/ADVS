/**
 * Single normalization layer for every failure that can reach the UI.
 *
 * Nothing outside this module is allowed to render an error: backend enum
 * codes, FastAPI validation payloads, and transport failures all collapse into
 * one `ApiError` with safe Korean presentation copy. This guarantees a user
 * never sees `[object Object]`, an `ApiError` class name, a raw enum, or a
 * stack trace.
 */

export type ApiErrorCode =
  | "INVALID_FILE_TYPE"
  | "FILE_TOO_LARGE"
  | "EMPTY_FILE"
  | "CORRUPT_DOCUMENT"
  | "TOO_MANY_PAGES"
  | "RESOURCE_NOT_FOUND"
  | "OCR_PROVIDER_ERROR"
  | "OCR_TIMEOUT"
  | "OCR_DISABLED"
  | "OCR_INITIALIZATION_ERROR"
  | "OCR_PROCESSING_ERROR"
  | "OCR_INVALID_RESPONSE"
  | "OCR_EMPTY_RESULT"
  | "PDF_RENDER_ERROR"
  | "UNSUPPORTED_FILE"
  | "PROCESSING_FAILED"
  | "VALIDATION_FAILED"
  | "VALIDATION_ERROR"
  | "NETWORK_ERROR"
  | "HTTP_ERROR";

/** Fixed copy per backend code. Never derived from backend message text. */
const CODE_MESSAGES: Record<ApiErrorCode, string> = {
  INVALID_FILE_TYPE: "PDF 파일만 업로드할 수 있습니다.",
  FILE_TOO_LARGE: "파일 크기가 허용 범위를 초과했습니다.",
  EMPTY_FILE: "비어 있는 파일은 업로드할 수 없습니다.",
  CORRUPT_DOCUMENT: "PDF 파일을 읽을 수 없습니다.",
  TOO_MANY_PAGES: "PDF 페이지 수가 허용 범위를 초과했습니다.",
  RESOURCE_NOT_FOUND: "요청한 정보를 찾을 수 없습니다.",
  OCR_PROVIDER_ERROR: "서류 분석 서비스에 연결하지 못했습니다.",
  OCR_TIMEOUT: "서류 분석 시간이 초과되었습니다.",
  OCR_DISABLED: "현재 서류 분석 기능을 사용할 수 없습니다.",
  OCR_INITIALIZATION_ERROR: "서류 분석 기능을 시작하지 못했습니다.",
  OCR_PROCESSING_ERROR: "서류 분석 중 오류가 발생했습니다.",
  OCR_INVALID_RESPONSE: "서류 분석 결과를 읽지 못했습니다.",
  OCR_EMPTY_RESULT: "서류에서 읽을 수 있는 내용을 찾지 못했습니다.",
  PDF_RENDER_ERROR: "PDF 페이지를 읽지 못했습니다.",
  UNSUPPORTED_FILE: "지원하지 않는 파일 형식입니다.",
  PROCESSING_FAILED: "서류 분석에 실패했습니다.",
  VALIDATION_FAILED: "입력값을 확인해 주세요.",
  VALIDATION_ERROR: "입력값을 확인해 주세요.",
  NETWORK_ERROR: "서버에 연결할 수 없습니다. 네트워크 연결을 확인하고 다시 시도해 주세요.",
  HTTP_ERROR: "요청을 처리하지 못했습니다.",
};

/** Context-aware copy for the same underlying code. */
const CONTEXT_OVERRIDES: Partial<
  Record<ApiErrorCode, Partial<Record<ErrorContext, string>>>
> = {
  VALIDATION_FAILED: { verify: "자동 점검을 완료하지 못했습니다." },
  OCR_TIMEOUT: { process: "서류 분석 시간이 초과되었습니다." },
  PROCESSING_FAILED: { process: "서류 분석에 실패했습니다." },
};

export type ErrorContext = "upload" | "process" | "verify" | "review" | "load";

const CONTEXT_FALLBACK: Record<ErrorContext, string> = {
  upload: "파일 업로드에 실패했습니다.",
  process: "서류 분석에 실패했습니다.",
  verify: "자동 점검을 완료하지 못했습니다.",
  review: "검토 내용을 저장하지 못했습니다.",
  load: "정보를 불러오지 못했습니다.",
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  /** Safe backend-authored detail, already known to be user-presentable. */
  readonly detail: string | null;

  constructor(
    status: number,
    code: ApiErrorCode,
    detail: string | null = null,
  ) {
    // `message` is always safe Korean so that even a stray `String(error)`
    // cannot leak a raw backend detail. The backend-authored reason stays on
    // `detail` and is only surfaced by `apiErrorMessage`.
    super(CODE_MESSAGES[code] ?? CODE_MESSAGES.HTTP_ERROR);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

const KNOWN_CODES = new Set<string>(Object.keys(CODE_MESSAGES));

function toCode(value: unknown): ApiErrorCode {
  return typeof value === "string" && KNOWN_CODES.has(value)
    ? (value as ApiErrorCode)
    : "HTTP_ERROR";
}

type FastApiValidationItem = { msg?: unknown; loc?: unknown };

/**
 * Parses the three error shapes the FastAPI app can emit:
 * `detail: string`, `detail: {code, message}`, and `detail: ValidationItem[]`.
 */
export function parseApiErrorResponse(
  status: number,
  body: unknown,
): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string" && detail.length > 0) {
    return new ApiError(status, toCode(detail), detail);
  }
  if (Array.isArray(detail)) {
    const items = detail as FastApiValidationItem[];
    const messages = items
      .map((item) => (typeof item.msg === "string" ? item.msg : null))
      .filter((value): value is string => Boolean(value));
    // FastAPI prefixes constraint failures with the field name; keep the whole
    // message because it is the only place the offending input is named.
    return new ApiError(
      status,
      "VALIDATION_ERROR",
      messages.length > 0 ? messages.join(" ") : null,
    );
  }
  if (detail && typeof detail === "object") {
    const { code, message } = detail as { code?: unknown; message?: unknown };
    return new ApiError(
      status,
      toCode(code),
      typeof message === "string" && message.length > 0 ? message : null,
    );
  }
  return new ApiError(status, "HTTP_ERROR", null);
}

/**
 * The backend-authored reason, when it is safe to show. Only validation codes
 * qualify: they are the one family whose detail is written for the user and
 * explains exactly which input was rejected.
 */
export function apiErrorDetail(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  if (error.code !== "VALIDATION_FAILED" && error.code !== "VALIDATION_ERROR") {
    return null;
  }
  return error.detail;
}

/**
 * The only function components may call to describe a failure.
 * Unknown throwables collapse to generic context copy instead of leaking
 * internals.
 */
export function apiErrorMessage(
  error: unknown,
  context: ErrorContext = "load",
): string {
  if (!(error instanceof ApiError)) {
    return CONTEXT_FALLBACK[context];
  }
  const override = CONTEXT_OVERRIDES[error.code]?.[context];
  if (override) return override;
  // `VALIDATION_FAILED` / `VALIDATION_ERROR` carry a safe backend-authored
  // reason that is more useful than generic copy, so it is surfaced.
  if (
    error.detail &&
    (error.code === "VALIDATION_FAILED" || error.code === "VALIDATION_ERROR")
  ) {
    return error.detail;
  }
  // A code the frontend does not know yet must never render as `undefined`.
  return CODE_MESSAGES[error.code] ?? CONTEXT_FALLBACK[context];
}

/** True when retrying the exact same request could plausibly succeed. */
export function isRetryable(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  if (error.code === "NETWORK_ERROR") return true;
  if (error.status >= 500) return true;
  if (
    error.code === "OCR_TIMEOUT" ||
    error.code === "OCR_PROVIDER_ERROR" ||
    error.code === "OCR_PROCESSING_ERROR"
  ) {
    return true;
  }
  return false;
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof TypeError) {
    return new ApiError(0, "NETWORK_ERROR");
  }
  return new ApiError(0, "HTTP_ERROR");
}
