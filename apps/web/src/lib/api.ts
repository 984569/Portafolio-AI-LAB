export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    cache: "no-store",
    headers,
    signal: init?.signal ?? AbortSignal.timeout(15_000),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item: { msg?: string }) => item.msg ?? "Campo inválido").join(". ")
        : "No fue posible conectar con la API. Comprueba que esté en ejecución.";
    throw new Error(message);
  }
  if (body === null || typeof body !== "object") {
    throw new Error("La API devolvió una respuesta inválida. Vuelve a intentar.");
  }
  return body as T;
}
