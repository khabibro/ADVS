/**
 * All requests go to this app's own /api/proxy route, which forwards them to the ADVS API and adds
 * the admin token on the server. The browser never sees the token or needs CORS for the API.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null = null,
    readonly field: string | null = null,
  ) {
    super(message);
  }
}

const FALLBACK: Record<number, string> = {
  401: "관리자 인증이 필요합니다. 서버의 ADMIN_API_TOKEN 설정을 확인해 주세요.",
  404: "요청한 항목을 찾을 수 없습니다.",
  409: "다른 사람이 먼저 저장했습니다. 새로 고친 뒤 다시 시도해 주세요.",
  502: "ADVS 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해 주세요.",
};

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  let response: Response;
  try {
    response = await fetch(`/api/proxy/${path.replace(/^\//, "")}`, {
      ...rest,
      headers: { ...(json !== undefined ? { "content-type": "application/json" } : {}), ...rest.headers },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(FALLBACK[502], 0);
  }
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message =
      (typeof detail?.message === "string" && detail.message) ||
      FALLBACK[response.status] ||
      "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
    throw new ApiError(message, response.status, detail?.code ?? null, detail?.field ?? null);
  }
  return body as T;
}
