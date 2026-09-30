"use client";

import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Label } from 'recharts';

const PLACEHOLDER_DATA: { id: number; predicted: number; actual: number }[] = [];

export default function LeakageLabPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-2">Leakage Lab</h1>
      <p className="mb-6 text-gray-600">
        Comparing model predictions against actual subsequent prints.
      </p>

      {PLACEHOLDER_DATA.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4 text-yellow-800">
          No prediction data available yet. This chart will populate once the prediction engine has generated and stored predictions with subsequent actual returns.
        </div>
      )}

      <div className="bg-white p-4 rounded-lg shadow border h-[500px]">
        <h2 className="text-lg font-semibold mb-4">Predicted vs Actual Returns</h2>
        <ResponsiveContainer width="100%" height="80%">
          <ScatterChart
            margin={{
              top: 20,
              right: 20,
              bottom: 20,
              left: 20,
            }}
          >
            <CartesianGrid />
            <XAxis type="number" dataKey="predicted" name="Predicted Return" tickFormatter={(val) => `${(val * 100).toFixed(1)}%`}>
              <Label value="Predicted Return" offset={-10} position="insideBottom" />
            </XAxis>
            <YAxis type="number" dataKey="actual" name="Actual Return" tickFormatter={(val) => `${(val * 100).toFixed(1)}%`}>
              <Label value="Actual Return" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
            </YAxis>
            <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(value: number) => `${(value * 100).toFixed(2)}%`} />
            <Scatter name="Returns" data={PLACEHOLDER_DATA} fill="#3b82f6" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
