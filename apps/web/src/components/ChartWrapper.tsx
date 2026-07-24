/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
import React from "react";
import { cssVariables } from "../styles/design";

// Inject CSS variables into the document head (once)
if (typeof document !== "undefined") {
  const style = document.createElement("style");
  style.id = "design-tokens";
  style.textContent = cssVariables;
  document.head.appendChild(style);
}

/**
 * ChartWrapper selects and renders the appropriate chart component based on the
 * `type` prop. It also applies a consistent container with premium UI styling
 * (glass‑morphism, drop shadow, smooth transitions).
 */
export const ChartWrapper: React.FC<{
  type: "candlestick" | "line" | "area" | "ohlcv";
  data: any; // chart‑specific data format
}> = ({ type, data }) => {
  const Container = (
    <div
      className="chart-wrapper"
      style={{
        background: "rgba(255,255,255,0.08)",
        backdropFilter: "blur(12px)",
        borderRadius: "var(--border-radius)",
        boxShadow: "var(--shadow-md)",
        padding: "1rem",
        transition: "background var(--transition-normal)"
      }}
    ></div>
  );

  // Dynamically import the required chart component
  // (Assumes the components are exported from their respective files.)
  const ChartComponent = (() => {
    switch (type) {
      case "candlestick":
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        return require("./charts/LightweightCandlestickChart").default;
      case "line":
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        return require("./charts/SimpleLineAreaChart").default;
      case "area":
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        return require("./charts/SimpleLineAreaChart").default;
      case "ohlcv":
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        return require("./charts/OHLCVChart").default;
      default:
        return () => <div>Unsupported chart type</div>;
    }
  })();

  return (
    <div className="chart-wrapper-container" style={{ margin: "1rem 0" }}>
      {Container}
      <ChartComponent data={data} />
    </div>
  );
};

// Add CSS for the wrapper (injected globally via a <style> tag elsewhere or a CSS module)
// This is a minimal example; the real project can move it to a .css file.
if (typeof document !== "undefined") {
  const style = document.createElement("style");
  style.id = "chart-wrapper-styles";
  style.textContent = `
    .chart-wrapper-container {
      animation: fadeInUp var(--transition-normal) ease-out;
    }
    .chart-wrapper:hover {
      background: rgba(255,255,255,0.12);
    }
  `;
  document.head.appendChild(style);
}
