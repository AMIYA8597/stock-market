import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export interface LineAreaPoint {
  label: string;
  value: number;
}

interface SimpleLineAreaChartProps {
  data: LineAreaPoint[];
  mode?: 'area' | 'line';
  stroke?: string;
  fill?: string;
  yTickFormatter?: (value: number) => string;
}

export function SimpleLineAreaChart({
  data,
  mode = 'area',
  stroke = 'var(--nq-accent-cyan)',
  fill = 'rgba(0, 212, 245, 0.25)',
  yTickFormatter,
}: SimpleLineAreaChartProps): JSX.Element {
  if (mode === 'line') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 6, left: 0 }}>
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
          <Line type="monotone" dataKey="value" stroke={stroke} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 6, left: 0 }}>
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
        <Area type="monotone" dataKey="value" stroke={stroke} fill={fill} strokeWidth={2} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
