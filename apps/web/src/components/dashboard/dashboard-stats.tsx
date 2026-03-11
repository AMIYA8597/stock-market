"use client";

import { IndianRupee, Signal, Target, AlertTriangle } from "lucide-react";
import { StatCard } from "@neuroquant/ui";

export function DashboardStats() {
  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        label="Portfolio P&L Today"
        value="₹24,580"
        change={1.82}
        changeLabel="vs yesterday"
        icon={<IndianRupee className="h-4 w-4" />}
      />
      <StatCard
        label="Active Signals"
        value="12"
        change={3}
        changeLabel="3 new today"
        icon={<Signal className="h-4 w-4" />}
      />
      <StatCard
        label="Model Accuracy (30d)"
        value="68.4%"
        change={2.1}
        changeLabel="directional accuracy"
        icon={<Target className="h-4 w-4" />}
      />
      <StatCard
        label="Alerts"
        value="5"
        change={-2}
        changeLabel="2 critical"
        icon={<AlertTriangle className="h-4 w-4" />}
      />
    </div>
  );
}
