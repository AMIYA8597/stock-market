import React from "react";

export default function PredictionDashboard({ predictionData }: { predictionData: any }) {
  return (
    <div className="prediction-dashboard">
      <h2>Prediction Dashboard</h2>
      <div className="forecast-curves">
        {/* Render Forecast Curves */}
        <h3>Forecast Curves</h3>
      </div>
      <div className="confidence-bands">
        {/* Render Confidence Bands */}
        <h3>Confidence Bands: {predictionData?.confidence || "82"}%</h3>
      </div>
      <div className="ai-reasoning">
        {/* Render AI Reasoning */}
        <h3>AI Reasoning: {predictionData?.reason || "MACD Bullish Cross + Positive News"}</h3>
      </div>
      <div className="buy-sell-signals">
        {/* Render Buy/Sell Signals */}
        <h3>Signal: {predictionData?.prediction || "BUY"}</h3>
      </div>
      <div className="risk-scores">
        {/* Render Risk Scores */}
        <h3>Risk Score: {predictionData?.risk || "Medium"}</h3>
      </div>
    </div>
  );
}

