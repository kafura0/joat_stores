"use client";

import { create } from "zustand";

import type { IUser, UserRole } from "../types";

interface AuthStore {
  accessToken: string | null;
  user: IUser | null;

  setAccessToken: (token: string | null) => void;
  setUser: (user: IUser | null) => void;
  clearAuth: () => void;

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
