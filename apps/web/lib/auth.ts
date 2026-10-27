// Tek kullanıcılı giriş (ADR-007). Token tarayıcıda saklanır; her API
// isteğine Authorization başlığı olarak eklenir, 401 gelirse giriş sayfasına
// yönlendirilir. Geliştirme modunda backend token istemiyorsa (bypass) hiçbir
// istek 401 dönmez ve kullanıcı giriş ekranını hiç görmez.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "investify_token";
const LOGIN_PATH = "/giris";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Depolama kapalıysa (gizli pencere vb.) oturum bu sekmeyle sınırlı kalmaz;
    // kullanıcı her 401'de yeniden giriş yapar.
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // yok say
  }
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** 401'de token'ı siler ve giriş sayfasına gönderir (dönüş adresiyle). */
export function handleUnauthorized(status: number): void {
  if (status !== 401 || typeof window === "undefined") return;
  clearToken();
  if (window.location.pathname.startsWith(LOGIN_PATH)) return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.assign(`${LOGIN_PATH}?next=${next}`);
}

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });
  if (res.status === 401) throw new Error("E-posta veya şifre hatalı.");
  if (!res.ok) throw new Error("Giriş şu anda yapılamıyor, sunucuya ulaşılamadı.");
  const body = (await res.json()) as { access_token: string };
  setToken(body.access_token);
}
