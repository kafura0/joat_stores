/**
 * Auth state management for the admin app.
 *
 * RULES:
 *   - Access token stored in memory ONLY — never localStorage/sessionStorage
 *   - User identity (role, store_id) decoded from JWT payload
 *   - Cleared on logout or refresh failure
 *
 * Implementation: Story 1.8
 */

"use client";

import { create } from "zustand";

import type { IUser, UserRole } from "@/types/auth";

interface AuthStore {
  /** JWT access token — in memory only, never persisted */
  accessToken: string | null;
  /** Decoded user info from JWT payload */
  user: IUser | null;

  setAccessToken: (token: string | null) => void;
  setUser: (user: IUser | null) => void;
  clearAuth: () => void;

  // Derived helpers
  isAuthenticated: () => boolean;
  getRole: () => UserRole | null;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  accessToken: null,
  user: null,

  setAccessToken: (token) => set({ accessToken: token }),
  setUser: (user) => set({ user }),
  clearAuth: () => set({ accessToken: null, user: null }),

  isAuthenticated: () => get().accessToken !== null,
  getRole: () => get().user?.role ?? null,
}));
