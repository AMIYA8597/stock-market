/**
 * Format number as currency
 */
export function formatCurrency(value: number, currency = 'INR', decimals = 2): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format number as percentage
 */
export function formatPercent(value: number, decimals = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format large numbers with compact notation
 */
export function formatCompact(value: number, decimals = 2): string {
  const formatter = new Intl.NumberFormat('en-IN', {
    notation: 'compact',
    maximumFractionDigits: decimals,
  });
  return formatter.format(value);
}

/**
 * Format date to readable format
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format date and time
 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format time
 */
export function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Format number with provided decimals
 */
export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Determine color class based on value
 */
export function getChangeColor(value: number): string {
  if (value > 0) return 'text-[var(--accent-green)]';
  if (value < 0) return 'text-[var(--accent-red)]';
  return 'text-[var(--text-secondary)]';
}

/**
 * Get signal direction badge variant
 */
export function getSignalVariant(signal: string): 'buy' | 'sell' | 'neutral' {
  if (signal.includes('BUY')) return 'buy';
  if (signal.includes('SELL')) return 'sell';
  return 'neutral';
}

/**
 * Get regime badge variant
 */
export function getRegimeVariant(regime: string): 'bull' | 'bear' | 'sideways' | 'crisis' {
  const lower = regime.toLowerCase();
  if (lower.includes('bull')) return 'bull';
  if (lower.includes('bear')) return 'bear';
  if (lower.includes('side')) return 'sideways';
  if (lower.includes('crisis')) return 'crisis';
  return 'sideways';
}
