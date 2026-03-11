/**
 * Axios API client with auth interceptors.
 *
 * RULES:
 *   - ALL HTTP requests must go through this instance
 *   - Request interceptor attaches Authorization: Bearer <accessToken>
 *   - Response interceptor retries on 401 after token refresh (once)
 *   - Refresh failure → clear auth + redirect to /login?expired=1
 *
 * Implementation: Story 1.8
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "@/stores/authStore";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
if (!API_URL && typeof window !== "undefined") {
  console.error(
    "[api] NEXT_PUBLIC_API_URL is not set — API calls will fall back to http://localhost/api/v1"
  );
}

export const api = axios.create({
  baseURL: API_URL ?? "http://localhost/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // send httpOnly refresh cookie on all requests
});

// ── Request interceptor: attach Bearer token ─────────────────────────────────
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const { accessToken } = useAuthStore.getState();
  if (accessToken && config.headers) {
    config.headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return config;
});

// Track whether a refresh is already in-flight to avoid parallel refresh loops
let isRefreshing = false;
type PendingResolve = (token: string) => void;
type PendingReject = (err: unknown) => void;
let pendingQueue: Array<{ resolve: PendingResolve; reject: PendingReject }> = [];

function processQueue(error: unknown, token: string | null): void {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token);
    else reject(error);
  });
  pendingQueue = [];
}

// ── Response interceptor: 401 → refresh → retry ──────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Don't refresh if this IS the refresh request (avoid infinite loop)
    if (originalRequest.url?.includes("/auth/token/refresh/")) {
      useAuthStore.getState().clearAuth();
      if (typeof window !== "undefined") {
        window.location.href = "/login?expired=1";
      }
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue concurrent requests while refresh is in-flight
      return new Promise<string>((resolve, reject) => {
        pendingQueue.push({ resolve, reject });
      }).then((token) => {
        if (originalRequest.headers) {
          originalRequest.headers["Authorization"] = `Bearer ${token}`;
        }
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshRes = await api.post<{ data: { access: string } }>(
        "/auth/token/refresh/",
        {},
        { withCredentials: true }
      );

      const newToken = refreshRes.data.data.access;
      useAuthStore.getState().setAccessToken(newToken);

      processQueue(null, newToken);

      if (originalRequest.headers) {
        originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
      }
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      useAuthStore.getState().clearAuth();
      if (typeof window !== "undefined") {
        window.location.href = "/login?expired=1";
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
