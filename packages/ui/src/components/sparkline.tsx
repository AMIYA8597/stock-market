"use client";

import * as React from "react";
import { cn } from "../lib/utils";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  positive?: boolean;
  className?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  strokeWidth = 1.5,
  positive,
  className,
}: SparklineProps) {
  if (data.length < 2) return null;

  const isUp = positive ?? data[data.length - 1]! > data[0]!;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 1;

  const points = data.map((val, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
    const y = padding + (1 - (val - min) / range) * (height - 2 * padding);
    return `${x},${y}`;
  });

  const polylinePoints = points.join(" ");

  // Create gradient fill path
  const firstPoint = points[0]!;
  const lastPoint = points[points.length - 1]!;
  const fillPath = `M${firstPoint} ${points.map((p) => `L${p}`).join(" ")} L${lastPoint.split(",")[0]},${height} L${firstPoint.split(",")[0]},${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cn("overflow-visible", className)}
    >
      <defs>
        <linearGradient id={`spark-grad-${isUp ? "up" : "down"}`} x1="0" y1="0" x2="0" y2="1">
          <stop
            offset="0%"
            stopColor={isUp ? "var(--nq-bull)" : "var(--nq-bear)"}
            stopOpacity="0.2"
          />
          <stop
            offset="100%"
            stopColor={isUp ? "var(--nq-bull)" : "var(--nq-bear)"}
            stopOpacity="0"
          />
        </linearGradient>
      </defs>
      <path
        d={fillPath}
        fill={`url(#spark-grad-${isUp ? "up" : "down"})`}
      />
      <polyline
        points={polylinePoints}
        fill="none"
        stroke={isUp ? "var(--nq-bull)" : "var(--nq-bear)"}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
