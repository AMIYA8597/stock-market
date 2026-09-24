"use client";

import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Label } from 'recharts';

// Mock data for predicted vs actual returns
const mockData = [
  { id: 1, predicted: 0.05, actual: 0.04 },
  { id: 2, predicted: -0.02, actual: -0.01 },
  { id: 3, predicted: 0.08, actual: 0.07 },
  { id: 4, predicted: -0.05, actual: -0.06 },
  { id: 5, predicted: 0.01, actual: 0.02 },
  { id: 6, predicted: 0.03, actual: 0.01 },
  { id: 7, predicted: -0.01, actual: 0.0 },
  { id: 8, predicted: 0.06, actual: 0.05 },
  { id: 9, predicted: -0.03, actual: -0.04 },
  { id: 10, predicted: 0.02, actual: 0.03 },
  { id: 11, predicted: 0.04, actual: 0.045 },
  { id: 12, predicted: -0.04, actual: -0.035 },
];

export default function LeakageLabPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-2">Leakage Lab</h1>
      <p className="mb-6 text-gray-600">
        Comparing model predictions against actual subsequent prints.
      </p>

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
            <Scatter name="Returns" data={mockData} fill="#3b82f6" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
