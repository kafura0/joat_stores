// lib/utils.ts
// Shared formatting utilities.
// RULE: Always use these — never format currency or dates inline in components.

/**
 * Format a monetary amount in KES.
 * @param amount - string decimal e.g. "1500.00"
 * @returns formatted string e.g. "KES 1,500"
 */
export function formatCurrency(amount: string): string {
  return `KES ${parseFloat(amount).toLocaleString("en-KE")}`;
}

/**
 * Format a UTC ISO datetime string in Africa/Nairobi timezone.
 * @param isoString - ISO 8601 UTC string e.g. "2026-02-24T12:00:00Z"
 * @returns formatted string in East Africa Time
 */
export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString("en-KE", {
    timeZone: "Africa/Nairobi",
  });
}
