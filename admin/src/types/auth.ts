/**
 * Auth-specific type definitions for the admin app.
 *
 * Implementation: Story 1.8
 */

export type UserRole =
  | "platform_admin"
  | "store_owner"
  | "store_manager"
  | "cashier"
  | "waiter";

export interface IUser {
  id: string;
  email: string;
  role: UserRole;
  store_id: string | null;
  store_name?: string | null;
}

export interface ILoginCredentials {
  email: string;
  password: string;
}

export interface ITokenResponse {
  access: string;
  role: UserRole;
  store_id: string | null;
}

export interface IJWTPayload {
  user_id: string;
  email?: string;
  role: UserRole;
  store_id: string | null;
  exp: number;
  iat: number;
  token_type: "access";
}
