"use client";

import * as React from "react";
import { cn, formatPrice, formatPercent, getPriceColor, getDirectionArrow } from "../lib/utils";

interface PriceDisplayProps {
  price: number;
  change?: number;
  changePercent?: number;
  currency?: string;
  size?: "sm" | "md" | "lg" | "xl";
  showArrow?: boolean;
  showChange?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: "text-price-sm",
  md: "text-base",
  lg: "text-price-md",
  xl: "text-price-lg",
} as const;

export function PriceDisplay({
  price,
  change,
  changePercent,
  currency = "₹",
  size = "md",
  showArrow = true,
  showChange = true,
  className,
}: PriceDisplayProps) {
  const changeVal = changePercent ?? change ?? 0;

  return (
    <div className={cn("flex items-baseline gap-2 font-mono", className)}>
      <span className={cn("text-nq-text-primary font-semibold", sizeClasses[size])}>
        {formatPrice(price, currency)}
      </span>
      {showChange && changePercent !== undefined && (
        <span className={cn("flex items-center gap-0.5 text-xs font-medium", getPriceColor(changeVal))}>
          {showArrow && (
            <span className="text-[10px]">{getDirectionArrow(changeVal)}</span>
          )}
          {formatPercent(changePercent)}
        </span>
      )}
      {showChange && change !== undefined && changePercent === undefined && (
        <span className={cn("flex items-center gap-0.5 text-xs font-medium", getPriceColor(change))}>
          {showArrow && (
            <span className="text-[10px]">{getDirectionArrow(change)}</span>
          )}
          {formatPrice(Math.abs(change), currency)}
        </span>
      )}
    </div>
  );
}
