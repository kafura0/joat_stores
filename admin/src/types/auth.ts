/**
 * Auth-specific type definitions for the admin app.
 *
 * Implementation: Story 1.8
 */

export type UserRole =
  | "platform_admin"
  | "store_owner"
  | "store_manager"
  | "customer";

export interface IUser {
  id: string;
  email: string;
  role: UserRole;
  store_id: string | null; // null for platform_admin
  /** Human-readable store name. Populated from store detail API (Epic 4). Null until then. */
  store_name?: string | null;
}

export interface ILoginCredentials {
  email: string;
  password: string;
}

/** Shape of POST /api/v1/auth/token/ 200 response body */
export interface ITokenResponse {
  access: string;
  role: UserRole;
  store_id: string | null;
}

/** Decoded JWT access token payload */
export interface IJWTPayload {
  user_id: string;
  email?: string; // not guaranteed in all token versions — use login email as fallback
  role: UserRole;
  store_id: string | null;
  exp: number;
  iat: number;
  token_type: "access";
}
