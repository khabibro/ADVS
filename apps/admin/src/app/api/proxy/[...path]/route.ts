import { type NextRequest, NextResponse } from "next/server";

/**
 * Server-side proxy to the ADVS API for the admin console.
 * - adds X-ADVS-Admin-Token from ADMIN_API_TOKEN, so the token stays on the server;
 * - forwards only the routes the console needs.
 */
const API_URL = (process.env.ADVS_API_URL ?? process.env.API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
const ALLOWED = [/^admin\//, /^projects$/, /^project-summaries$/, /^workflows$/];

async function forward(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const target = path.map(encodeURIComponent).join("/");
  if (!ALLOWED.some((pattern) => pattern.test(target))) {
    return NextResponse.json({ detail: { code: "NOT_ALLOWED", message: "허용되지 않은 요청입니다." } }, { status: 403 });
  }
  const headers: Record<string, string> = { accept: "application/json" };
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;
  if (process.env.ADMIN_API_TOKEN) headers["x-advs-admin-token"] = process.env.ADMIN_API_TOKEN;
  try {
    const upstream = await fetch(`${API_URL}/${target}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.text(),
      cache: "no-store",
    });
    const text = await upstream.text();
    return new NextResponse(text || null, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: { code: "API_UNREACHABLE", message: "ADVS 서버에 연결할 수 없습니다." } },
      { status: 502 },
    );
  }
}

export { forward as GET, forward as POST, forward as PUT, forward as PATCH };
