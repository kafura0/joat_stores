/**
 * Auth helpers: login, logout, token refresh, JWT decode.
 *
 * RULES:
 *   - Access token stored in Zustand (memory) only — never localStorage
 *   - Refresh token managed by the backend as httpOnly cookie
 *   - Never import next-auth — conflicts with custom store_id JWT claim
 *
 * Implementation: Story 1.8
 */

"use client";

import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type { IJWTPayload, IUser, UserRole } from "@/types/auth";

// Non-sensitive session presence indicator cookie for middleware route guard.
// Does NOT contain the access token — that stays in Zustand memory.
const SESSION_COOKIE = "auth_session";

function setSessionCookie(): void {
  if (typeof document !== "undefined") {
    // Max-Age=604800 = 7 days — keeps session cookie alive across browser restarts
    // so a valid refresh cookie isn't wasted on a forced re-login
    document.cookie = `${SESSION_COOKIE}=1; path=/; SameSite=Lax; Max-Age=604800`;
  }
}

function clearSessionCookie(): void {
  if (typeof document !== "undefined") {
    document.cookie = `${SESSION_COOKIE}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }
}

/**
 * Decode JWT payload (base64url) without a library.
 * Returns null if the token is malformed.
 */
export function decodeToken(token: string): IJWTPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    // base64url → base64 padding
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    const json = atob(padded);
    return JSON.parse(json) as IJWTPayload;
  } catch {
    return null;
  }
}

/**
 * Returns true if the token's exp claim is in the past.
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeToken(token);
  if (!payload) return true;
  // exp is in seconds; Date.now() is in ms
  return payload.exp * 1000 < Date.now();
}

/**
 * POST /api/v1/auth/token/
 *
 * On success: stores access token + decoded user in authStore,
 *             sets presence cookie for middleware.
 * Returns the user's role so the caller can redirect appropriately.
 * Throws on 401 (invalid credentials) or network error.
 */
export async function performLogin(
  email: string,
  password: string
): Promise<UserRole> {
  const res = await api.post<{ data: { access: string; user: { id: string; email: string; role: UserRole; store_id: string | null } } }>(
    "/auth/token/",
    { email, password }
  );

  const { access, user: apiUser } = res.data.data;
  const { role, store_id } = apiUser;
  const payload = decodeToken(access);

  if (!payload) {
    throw new Error("Received malformed access token from server.");
  }

  const user: IUser = {
    id: payload.user_id,
    email: payload.email ?? email, // JWT may omit email; fall back to the login email
    role,
    store_id,
  };

  const { setAccessToken, setUser } = useAuthStore.getState();
  setAccessToken(access);
  setUser(user);
  setSessionCookie();

  return role;
}

/**
 * POST /api/v1/auth/logout-all/
 *
 * Best-effort — always clears local state even if API call fails.
 */
export async function performLogout(): Promise<void> {
  try {
    await api.post("/auth/logout-all/");
  } catch {
    // Best-effort; proceed with local clear regardless
  } finally {
    useAuthStore.getState().clearAuth();
    clearSessionCookie();
  }
}

/**
 * POST /api/v1/auth/token/refresh/
 *
 * Reads refresh token from httpOnly cookie (sent automatically by browser).
 * On success: updates accessToken in authStore.
 * Returns the new access token, or null on failure.
 */
export async function performRefresh(): Promise<string | null> {
  try {
    const res = await api.post<{ data: { access: string } }>(
      "/auth/token/refresh/",
      {},
      { withCredentials: true }
    );

    const { access } = res.data.data;
    const payload = decodeToken(access);

    const { setAccessToken, setUser, user } = useAuthStore.getState();
    setAccessToken(access);

    // Re-hydrate user from new token if we don't have user info yet.
    // email is not guaranteed in the JWT payload; leave it as "" if absent —
    // the next full login will populate it correctly.
    if (payload && !user) {
      setUser({
        id: payload.user_id,
        email: payload.email ?? "",
        role: payload.role,
        store_id: payload.store_id,
      });
    }

    setSessionCookie();
    return access;
  } catch {
    useAuthStore.getState().clearAuth();
    clearSessionCookie();
    return null;
  }
}
