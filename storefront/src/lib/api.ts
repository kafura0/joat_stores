// lib/api.ts
// axios instance with auth interceptor.
// Full implementation in Story 1.5 (JWT) and Story 1.8 (admin auth).

import axios from "axios";

/**
 * API client
 *
 * RULE: ALL HTTP requests must go through this instance — never use fetch() directly.
 * This instance will add:
 *   - Authorization: Bearer <access_token> header (from memory)
 *   - Automatic token refresh on 401 using httpOnly refresh cookie
 *   - {data, meta, errors} response envelope parsing
 *
 * Story 1.5 wires the auth interceptor.
 */
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// TODO: Story 1.5 — add auth interceptor (request + response)
// TODO: Story 1.5 — add 401 → token refresh → retry logic
