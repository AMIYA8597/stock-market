"use client";

import * as React from "react";
import { cn } from "../lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular";
}

function Skeleton({ className, variant = "text", ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse bg-nq-bg-elevated",
        variant === "text" && "h-4 w-full rounded",
        variant === "circular" && "rounded-full",
        variant === "rectangular" && "rounded-nq",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
