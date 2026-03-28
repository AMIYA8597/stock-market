import React from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';

export interface DonutSlice {
  name: string;
  value: number;
  color: string;
}

interface SimpleDonutChartProps {
  data: DonutSlice[];
  centerLabel?: string;
}

export function SimpleDonutChart({ data, centerLabel }: SimpleDonutChartProps): JSX.Element {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={46}
          outerRadius={72}
          paddingAngle={2}
          isAnimationActive={false}
        >
          {data.map((slice, idx) => (
            <Cell key={`slice-${slice.name}-${idx}`} fill={slice.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: 'var(--nq-bg-overlay)',
            border: '1px solid var(--nq-border)',
            borderRadius: 8,
            color: 'var(--nq-text-primary)',
            fontSize: 12,
          }}
        />
        {centerLabel ? (
          <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" fill="var(--nq-text-secondary)" fontSize="11">
            {centerLabel}
          </text>
        ) : null}
      </PieChart>
    </ResponsiveContainer>
  );
}
