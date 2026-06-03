"use client";

import { useMemo } from "react";

export default function CalendarTab(): JSX.Element {
  const calendarEvents = useMemo(
    () => [
      {
        time: "Today 18:30",
        country: "IN",
        event: "RBI Interest Rate Decision",
        impact: "HIGH",
        actual: "6.50%",
        forecast: "6.50%",
        previous: "6.50%",
      },
      {
        time: "Today 20:00",
        country: "US",
        event: "Fed Interest Rate Decision",
        impact: "HIGH",
        actual: "--",
        forecast: "5.25%",
        previous: "5.25%",
      },
      {
        time: "Tomorrow 19:30",
        country: "US",
        event: "Core CPI YoY",
        impact: "HIGH",
        actual: "--",
        forecast: "3.4%",
        previous: "3.5%",
      },
      {
        time: "Jun 05 18:00",
        country: "US",
        event: "Non-Farm Payrolls",
        impact: "HIGH",
        actual: "--",
        forecast: "185K",
        previous: "175K",
      },
      {
        time: "Jun 06 14:30",
        country: "EU",
        event: "ECB Interest Rate Decision",
        impact: "MEDIUM",
        actual: "--",
        forecast: "4.25%",
        previous: "4.50%",
      },
      {
        time: "Jun 07 19:00",
        country: "US",
        event: "Initial Jobless Claims",
        impact: "LOW",
        actual: "--",
        forecast: "215K",
        previous: "210K",
      },
    ],
    []
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[10px] font-mono">
        <thead>
          <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
            <th className="pb-1.5">Time</th>
            <th className="pb-1.5">Country</th>
            <th className="pb-1.5">Event</th>
            <th className="pb-1.5">Impact</th>
            <th className="pb-1.5">Actual</th>
            <th className="pb-1.5">Forecast</th>
            <th className="pb-1.5 text-right">Previous</th>
          </tr>
        </thead>
        <tbody>
          {calendarEvents.map((item, idx) => (
            <tr
              key={idx}
              className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors"
            >
              <td className="py-1.5 text-[var(--nq-text-muted)]">{item.time}</td>
              <td className="py-1.5 font-bold text-[var(--nq-text-secondary)]">{item.country}</td>
              <td className="py-1.5 text-[var(--nq-text-primary)]">{item.event}</td>
              <td className="py-1.5">
                <span
                  className={`inline-flex rounded px-1.5 py-0.5 text-[8px] font-bold border ${
                    item.impact === "HIGH"
                      ? "bg-[rgba(255,59,92,0.08)] border-[rgba(255,59,92,0.2)] text-[#FF3B5C]"
                      : item.impact === "MEDIUM"
                      ? "bg-[rgba(255,184,0,0.08)] border-[rgba(255,184,0,0.2)] text-[#FFB800]"
                      : "bg-[rgba(59,130,246,0.08)] border-[rgba(59,130,246,0.2)] text-[#3B82F6]"
                  }`}
                >
                  {item.impact}
                </span>
              </td>
              <td className="py-1.5 text-[var(--nq-text-secondary)]">{item.actual}</td>
              <td className="py-1.5 text-[var(--nq-text-secondary)]">{item.forecast}</td>
              <td className="py-1.5 text-right text-[var(--nq-text-muted)]">{item.previous}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
