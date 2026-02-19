import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import numeral from "numeral";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a number as price with trailing zeros: ₹1,234.50 */
export function formatPrice(value: number, currency: string = "₹"): string {
  return `${currency}${numeral(value).format("0,0.00")}`;
}

/** Format a number as compact: 1.2M, 3.4B etc */
export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1e12) return numeral(value).format("0.00a").toUpperCase();
  if (Math.abs(value) >= 1e9) return numeral(value).format("0.00a").toUpperCase();
  if (Math.abs(value) >= 1e6) return numeral(value).format("0.00a").toUpperCase();
  if (Math.abs(value) >= 1e3) return numeral(value).format("0.00a").toUpperCase();
  return numeral(value).format("0,0.00");
}

/** Format percentage with sign: +2.45% or -1.23% */
export function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${numeral(value).format("0.00")}%`;
}

/** Format large volume: 1.2M, 345K etc */
export function formatVolume(value: number): string {
  return numeral(value).format("0.00a").toUpperCase();
}

/** Get the color class for a price change */
export function getPriceColor(change: number): string {
  if (change > 0) return "text-nq-bull";
  if (change < 0) return "text-nq-bear";
  return "text-nq-text-secondary";
}

/** Get the background color class for a price change */
export function getPriceBgColor(change: number): string {
  if (change > 0) return "bg-nq-bull-bg";
  if (change < 0) return "bg-nq-bear-bg";
  return "bg-nq-bg-card";
}

/** Direction triangle character */
export function getDirectionArrow(change: number): string {
  if (change > 0) return "▲";
  if (change < 0) return "▼";
  return "–";
}
