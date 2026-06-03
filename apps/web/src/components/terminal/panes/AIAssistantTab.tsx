"use client";

import { useState } from "react";
import type { SignalResponse } from "@/types/intelligence";
import { safeFormat } from "@/lib/formatters";

interface AIAssistantTabProps {
  signal: SignalResponse | null;
}

export default function AIAssistantTab({ signal }: AIAssistantTabProps): JSX.Element {
  const [chatMessages, setChatMessages] = useState<Array<{ sender: "user" | "ai"; text: string }>>([
    {
      sender: "ai",
      text: "Hello! I am your AI Quant Assistant. Ask me anything about current regime states, predictive confidence, or backtest strategies.",
    },
  ]);
  const [chatInput, setChatInput] = useState<string>("");

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    const userText = chatInput;
    setChatInput("");
    setChatMessages((prev) => [...prev, { sender: "user", text: userText }]);

    setTimeout(() => {
      let reply = "";
      const sym = signal?.symbol ?? "the asset";
      const dir = signal?.ensemble.direction ?? "NEUTRAL";
      const conf = signal ? safeFormat(Number(signal.ensemble.confidence) * 100, 1) : "--";
      const regime = signal?.regime.state ?? "SIDEWAYS";

      if (userText.toLowerCase().includes("regime") || userText.toLowerCase().includes("trend")) {
        reply = `The current predictive regime for ${sym} is in a '${regime}' state, with an ensemble directional bias towards ${dir}.`;
      } else if (
        userText.toLowerCase().includes("predict") ||
        userText.toLowerCase().includes("bullish") ||
        userText.toLowerCase().includes("bearish")
      ) {
        reply = `Based on our ensemble models (TFT, XGBoost, and HMM GARCH), the predictive signal for ${sym} is ${dir} with a confidence of ${conf}%.`;
      } else if (userText.toLowerCase().includes("backtest") || userText.toLowerCase().includes("strategy")) {
        reply = `You can run strategy backtests for ${sym} in the 'Backtest Lab' tab using MACD or RSI rules. Ensemble model Kelly fraction is currently at ${safeFormat(
          signal?.ensemble.kelly_fraction,
          3
        )}.`;
      } else {
        reply = `Analyzing ${sym}... The model ensemble suggests a ${dir} bias (Confidence: ${conf}%). Regimes are trending ${regime.toLowerCase()}. Let me know if you want to backtest a custom strategy!`;
      }

      setChatMessages((prev) => [...prev, { sender: "ai", text: reply }]);
    }, 800);
  };

  return (
    <div className="flex flex-col gap-2 h-full min-h-[190px]">
      <div className="flex-1 overflow-y-auto max-h-[145px] border border-[var(--nq-border)] bg-[rgba(0,0,0,0.20)] rounded p-2 flex flex-col gap-1.5 ds-scrollable font-mono text-[9px] sm:text-[10px]">
        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`max-w-[85%] rounded px-2.5 py-1.5 ${
              msg.sender === "user"
                ? "self-end bg-[rgba(0,212,245,0.15)] border border-[rgba(0,212,245,0.25)] text-[var(--nq-text-primary)]"
                : "self-start bg-[rgba(255,255,255,0.04)] border border-[var(--nq-border)] text-[var(--nq-text-secondary)]"
            }`}
          >
            <p className="font-bold text-[7px] uppercase tracking-wider text-[var(--nq-text-muted)] mb-0.5">
              {msg.sender === "user" ? "You" : "AI Quant"}
            </p>
            <p className="whitespace-pre-line leading-relaxed">{msg.text}</p>
          </div>
        ))}
      </div>
      <div className="flex gap-2 font-mono">
        <input
          type="text"
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSendChat();
          }}
          placeholder="Ask AI Assistant about predictive signals, regime state..."
          className="flex-1 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-[10px] text-[var(--nq-text-primary)] focus:outline-none focus:border-[var(--nq-accent-cyan)] font-mono"
        />
        <button
          type="button"
          onClick={handleSendChat}
          className="rounded bg-[var(--nq-accent-purple)] hover:bg-[rgba(139,92,246,0.8)] px-3 py-1 font-semibold text-[10px] text-white transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
