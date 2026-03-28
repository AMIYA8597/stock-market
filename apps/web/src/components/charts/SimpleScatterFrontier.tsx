import React from 'react';
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

export interface FrontierPoint {
  risk: number;
  ret: number;
  highlight?: boolean;
}

interface SimpleScatterFrontierProps {
  points: FrontierPoint[];
}

export function SimpleScatterFrontier({ points }: SimpleScatterFrontierProps): JSX.Element {
  const regular = points.filter((item) => !item.highlight);
  const highlighted = points.filter((item) => item.highlight);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ScatterChart margin={{ top: 8, right: 12, bottom: 6, left: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" />
        <XAxis
          type="number"
          dataKey="risk"
          tick={{ fill: 'var(--nq-text-tertiary)', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
        />
        <YAxis
          type="number"
          dataKey="ret"
          tick={{ fill: 'var(--nq-text-tertiary)', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
          width={48}
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          contentStyle={{
            background: 'var(--nq-bg-overlay)',
            border: '1px solid var(--nq-border)',
            borderRadius: 8,
            color: 'var(--nq-text-primary)',
            fontSize: 12,
          }}
          formatter={(value: number) => `${(value * 100).toFixed(2)}%`}
        />
        <Scatter data={regular} fill="rgba(0,212,245,0.65)" />
        <Scatter data={highlighted} fill="rgba(0,230,118,0.95)" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
