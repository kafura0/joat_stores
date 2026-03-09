// types/index.ts
// Shared TypeScript type definitions.
// RULE: All types live here — never define types inline in component files.
// RULE: Interfaces prefixed I (IProduct, IOrder); plain types PascalCase (OrderStatus).

// Placeholder — types added as domain stories are implemented.

export type TenantType = "retail" | "restaurant" | "bar" | "contracting";

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "fulfilled"
  | "completed"
  | "cancelled";

export interface IApiResponse<T> {
  data: T;
}

export interface IApiListResponse<T> {
  data: T[];
  meta: {
    count: number;
    next: string | null;
    previous: string | null;
  };
}

export interface IApiError {
  field: string | null;
  message: string;
  code: string;
}

export interface IApiErrorResponse {
  errors: IApiError[];
}
