export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function detailMessage(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("detail" in body)) return null;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : null))
      .filter((m): m is string => Boolean(m))
      .join("; ") || null;
  }
  return null;
}

export async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(detailMessage(body) ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

/** For endpoints that return 204 No Content (e.g. DELETE) — no body to parse. */
export async function assertOk(response: Response): Promise<void> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(detailMessage(body) ?? `Request failed with status ${response.status}`);
  }
}
