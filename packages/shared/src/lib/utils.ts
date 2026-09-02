import { format, parseISO } from "date-fns";

const currencyFormatter = new Intl.NumberFormat("en-KE", {
  style: "currency",
  currency: "KES",
  minimumFractionDigits: 2,
});

export function formatCurrency(amount: string | number): string {
  return currencyFormatter.format(
    typeof amount === "string" ? parseFloat(amount) : amount
  );
}

export function formatDate(dateString: string): string {
  return format(parseISO(dateString), "MMM dd, yyyy");
}

export function formatDateTime(dateString: string): string {
  return format(parseISO(dateString), "MMM dd, yyyy HH:mm");
}

export function formatTime(dateString: string): string {
  return format(parseISO(dateString), "HH:mm");
}

export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
