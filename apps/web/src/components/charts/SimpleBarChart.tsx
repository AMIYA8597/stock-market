import React from 'react';
import { ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis, Cell } from 'recharts';

export interface SimpleBarPoint {
  label: string;
  value: number;
  color?: string;
}

interface SimpleBarChartProps {
  data: SimpleBarPoint[];
  defaultColor?: string;
  yTickFormatter?: (value: number) => string;
}

export function SimpleBarChart({
  data,
  defaultColor = 'var(--nq-accent-purple)',
  yTickFormatter,
}: SimpleBarChartProps): JSX.Element {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 12, bottom: 6, left: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: 'var(--nq-text-tertiary)', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fill: 'var(--nq-text-tertiary)', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={yTickFormatter}
          width={48}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--nq-bg-overlay)',
            border: '1px solid var(--nq-border)',
            borderRadius: 8,
            color: 'var(--nq-text-primary)',
            fontSize: 12,
          }}
        />
        <Bar dataKey="value" radius={[3, 3, 0, 0]} isAnimationActive={false}>
          {data.map((item, idx) => (
            <Cell key={`bar-${item.label}-${idx}`} fill={item.color ?? defaultColor} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
