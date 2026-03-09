// stores/authStore.ts
// Auth state management.
// Full implementation in Story 1.5 (JWT).
// RULE: JWT access token stored in memory only — never localStorage.

import { create } from "zustand";

interface AuthStore {
  // Access token in memory only — never localStorage
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
  clearAuth: () => set({ accessToken: null }),
}));
