import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return fallback;
  const amount = Number(value);
  return `₹${amount.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatPercentage(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return fallback;
  const percent = Number(value);
  const normalized = Math.abs(percent) <= 1 ? percent * 100 : percent;
  return `${normalized.toLocaleString("en-IN", { maximumFractionDigits: 2 })}%`;
}
