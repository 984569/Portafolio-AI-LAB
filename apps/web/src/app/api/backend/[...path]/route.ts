import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const MAX_BODY = 16_384;

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const route = path.join("/");
  const readAllowed = request.method === "GET" && (
    route === "health" || route === "ready" || route === "api/v1/datasets" ||
    route === "api/v1/experiments" || route === "api/v1/training" || route === "api/v1/models" ||
    route === "api/v1/agent-desk/status" || route === "api/v1/agent-desk/runs" ||
    /^api\/v1\/agent-desk\/runs\/[a-f0-9-]{36}$/.test(route) ||
    /^api\/v1\/experiments\/[a-zA-Z0-9-]{1,80}$/.test(route) ||
    /^api\/v1\/training\/[a-f0-9-]{36}$/.test(route)
  );
  const writeAllowed = request.method === "POST" && (route === "api/v1/experiments" ||
    route === "api/v1/training" || route === "api/v1/agent-desk/runs" ||
    /^api\/v1\/training\/[a-f0-9-]{36}\/(cancel|evaluate|compare)$/.test(route));
  if (!readAllowed && !writeAllowed) {
    return NextResponse.json({ detail: "Ruta no disponible." }, { status: 404 });
  }
  const origin = request.headers.get("origin");
  // Next may normalize nextUrl to localhost even when the browser used 127.0.0.1.
  // Compare against the actual Host header, restricted to this local server.
  const host = request.headers.get("host");
  const localHost = host && /^(localhost|127\.0\.0\.1|\[::1\])(?::\d{1,5})?$/.test(host);
  if (!localHost || (writeAllowed && origin && origin !== `http://${host}`)) {
    return NextResponse.json({ detail: "Origen no permitido." }, { status: 403 });
  }
  if (writeAllowed && request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
    return NextResponse.json({ detail: "Se requiere application/json." }, { status: 415 });
  }
  try {
    const base = new URL(process.env.API_BASE_URL ?? "http://127.0.0.1:8000");
    if (base.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(base.hostname) ||
      base.username || base.password || base.search || base.hash || base.pathname !== "/") {
      throw new Error("Invalid server configuration");
    }
    let body: string | undefined;
    if (writeAllowed) {
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let total = 0;
      if (reader) {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          total += value.byteLength;
          if (total > MAX_BODY) {
            await reader.cancel();
            return NextResponse.json({ detail: "Solicitud demasiado grande." }, { status: 413 });
          }
          chunks.push(value);
        }
      }
      body = Buffer.concat(chunks).toString("utf8");
      try { JSON.parse(body); } catch {
        return NextResponse.json({ detail: "El cuerpo debe ser JSON válido." }, { status: 400 });
      }
    }
    const upstream = await fetch(new URL(`/${route}`, base), {
      method: request.method,
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(route.endsWith("/compare") || route.endsWith("/evaluate") ? 60_000 : 10_000),
    });
    const payload = await upstream.json();
    return NextResponse.json(payload, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "API no disponible. Inicia el servicio local y vuelve a intentar." }, {
      status: 502, headers: { "Cache-Control": "no-store" },
    });
  }
}

export { proxy as GET, proxy as POST };
