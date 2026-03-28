import React from 'react';

export interface HeatCell {
  row: number;
  col: number;
  value: number;
}

interface SimpleHeatGridProps {
  rows: number;
  cols: number;
  cells: HeatCell[];
  min?: number;
  max?: number;
}

export function SimpleHeatGrid({ rows, cols, cells, min = 0, max = 1 }: SimpleHeatGridProps): JSX.Element {
  const byKey = new Map(cells.map((cell) => [`${cell.row}-${cell.col}`, cell.value]));

  return (
    <div
      className="grid gap-1"
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
    >
      {Array.from({ length: rows * cols }, (_, idx) => {
        const row = Math.floor(idx / cols);
        const col = idx % cols;
        const value = byKey.get(`${row}-${col}`) ?? 0;
        const normalized = Math.max(0, Math.min(1, (value - min) / Math.max(max - min, 1e-9)));
        return (
          <div
            key={`heat-${row}-${col}`}
            className="h-6 rounded"
            style={{ background: `rgba(255,184,0,${0.08 + normalized * 0.8})` }}
            title={`r${row + 1} c${col + 1}: ${value.toFixed(3)}`}
          />
        );
      })}
    </div>
  );
}
