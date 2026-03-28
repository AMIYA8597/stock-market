import React from 'react';
import { cn } from '../../lib/utils';

interface Column<T> {
  key: string;
  label: string;
  render?: (value: unknown, row: T, index: number) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: string | ((row: T, index: number) => string);
  onRowClick?: (row: T, index: number) => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (key: string) => void;
  className?: string;
  emptyState?: React.ReactNode;
  isLoading?: boolean;
}

function DataTable<T extends object>({
  columns,
  data,
  rowKey,
  onRowClick,
  sortBy,
  sortOrder = 'asc',
  onSort,
  className,
  emptyState = 'No data available',
  isLoading = false,
}: DataTableProps<T>) {
  const getRowKey = (row: T, index: number) => {
    if (typeof rowKey === 'function') {
      return rowKey(row, index);
    }
    const value = (row as Record<string, unknown>)[rowKey];
    return String(value ?? index);
  };

  const alignClass = (align?: string) => {
    switch (align) {
      case 'center': return 'text-center';
      case 'right': return 'text-right';
      default: return 'text-left';
    }
  };

  if (isLoading) {
    return (
      <div className={cn('rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] p-4', className)}>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 rounded bg-[var(--ds-surface-2)] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className={cn(
        'rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] p-8 text-center text-[var(--ds-text-secondary)]',
        className
      )}>
        {emptyState}
      </div>
    );
  }

  return (
    <div className={cn('overflow-x-auto rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]', className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)]">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-4 py-3 font-semibold text-[var(--ds-text-secondary)]',
                  alignClass(col.align),
                  col.width
                )}
              >
                {col.sortable ? (
                  <button
                    onClick={() => onSort?.(col.key)}
                    className="flex items-center gap-2 hover:text-[var(--ds-text-primary)]"
                  >
                    {col.label}
                    {sortBy === col.key && (
                      <span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                ) : (
                  col.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr
              key={getRowKey(row, idx)}
              className={cn(
                'border-b border-[var(--ds-border-subtle)] transition-colors hover:bg-[var(--ds-surface-2)]',
                onRowClick && 'cursor-pointer'
              )}
              onClick={() => onRowClick?.(row, idx)}
            >
              {columns.map((col) => (
                <td
                  key={`${getRowKey(row, idx)}-${col.key}`}
                  className={cn(
                    'px-4 py-3 text-[var(--ds-text-primary)]',
                    alignClass(col.align),
                    col.width
                  )}
                >
                  {col.render
                    ? col.render(row[col.key as keyof T], row, idx)
                    : String(row[col.key as keyof T] || '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export { DataTable, type Column, type DataTableProps };
