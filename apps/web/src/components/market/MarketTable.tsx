/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { InstrumentInfo } from "@neuroquant/types";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { safeFormat } from "@/lib/formatters";
import { cn } from "@neuroquant/ui";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

interface MarketTableProps {
  instruments: InstrumentInfo[];
  isLoading?: boolean;
}

type SortField = "symbol" | "price" | "change" | "volume";
type SortOrder = "asc" | "desc";

export function MarketTable({ instruments, isLoading = false }: MarketTableProps) {
  const [sortField, setSortField] = useState<SortField>("volume");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [filter, setFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  const processedData = useMemo(() => {
    const data = instruments.filter(
      (inst) =>
        inst.symbol.toLowerCase().includes(filter.toLowerCase()) ||
        inst.displayName.toLowerCase().includes(filter.toLowerCase())
    );

    data.sort((a, b) => {
      // Sorting based on previous ticks (if loaded). Since we paginate before fetching ticks for all,
      // true global sorting by live price/volume requires server-side sorting. 
      // For now, client side sorting works on the cached/initial data we have.
      if (sortField === "symbol") {
        if (a.symbol < b.symbol) return sortOrder === "asc" ? -1 : 1;
        if (a.symbol > b.symbol) return sortOrder === "asc" ? 1 : -1;
      }
      return 0;
    });
    return data;
  }, [instruments, sortField, sortOrder, filter]);

  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return processedData.slice(startIndex, startIndex + itemsPerPage);
  }, [processedData, currentPage]);
  
  const totalPages = Math.ceil(processedData.length / itemsPerPage);

  const trackedSymbols = useMemo(
    () => paginatedData.map((inst) => inst.symbol.toUpperCase()),
    [paginatedData]
  );
  
  const { ticks } = usePriceFeed(trackedSymbols);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 opacity-50 ml-1" />;
    return sortOrder === "asc" ? (
      <ArrowUp className="w-3 h-3 text-nq-accent ml-1" />
    ) : (
      <ArrowDown className="w-3 h-3 text-nq-accent ml-1" />
    );
  };

  // removed duplicated useMemo blocks

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <input
          type="text"
          placeholder="Filter symbols..."
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setCurrentPage(1);
          }}
          className="w-full sm:w-64 bg-nq-bg-card border border-nq-border rounded-md px-3 py-1.5 text-sm outline-none focus:border-nq-accent transition-colors"
        />
        <div className="text-xs text-nq-text-tertiary">
          {processedData.length} symbols
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-nq-border bg-nq-bg-card">
        {/* Desktop Header */}
        <div className="hidden md:grid grid-cols-[1.5fr_1fr_1fr_1fr] px-4 py-3 text-xs font-semibold text-nq-text-secondary border-b border-nq-border sticky top-0 bg-nq-bg-card z-10">
          <button
            onClick={() => handleSort("symbol")}
            className="flex items-center hover:text-nq-text-primary uppercase tracking-wider"
          >
            Symbol <SortIcon field="symbol" />
          </button>
          <button
            onClick={() => handleSort("price")}
            className="flex items-center justify-end hover:text-nq-text-primary uppercase tracking-wider"
          >
            LTP <SortIcon field="price" />
          </button>
          <button
            onClick={() => handleSort("change")}
            className="flex items-center justify-end hover:text-nq-text-primary uppercase tracking-wider"
          >
            % Change <SortIcon field="change" />
          </button>
          <button
            onClick={() => handleSort("volume")}
            className="flex items-center justify-end hover:text-nq-text-primary uppercase tracking-wider"
          >
            Volume <SortIcon field="volume" />
          </button>
        </div>

        {/* Data Rows */}
        <div className="flex flex-col">
          {isLoading ? (
            Array.from({ length: 10 }).map((_, i) => (
              <div
                key={`skeleton-${i}`}
                className="border-b border-nq-border last:border-b-0 px-4 py-3 md:py-4"
              >
                <div className="grid gap-2 md:grid-cols-[1.5fr_1fr_1fr_1fr] md:items-center">
                  <span className="h-4 w-24 rounded bg-nq-bg-elevated animate-pulse" />
                  <span className="h-4 w-16 rounded bg-nq-bg-elevated animate-pulse md:ml-auto" />
                  <span className="h-4 w-20 rounded bg-nq-bg-elevated animate-pulse md:ml-auto" />
                  <span className="h-4 w-14 rounded bg-nq-bg-elevated animate-pulse md:ml-auto" />
                </div>
              </div>
            ))
          ) : paginatedData.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-nq-text-tertiary">
              No symbols found.
            </div>
          ) : (
            processedData.map((inst) => {
              const live = ticks.get(inst.symbol.toUpperCase());
              const price = live?.price ?? 0;
              const change = live?.change_pct ?? 0;
              const volume = live?.volume ?? 0;
              const isPositive = change >= 0;

              return (
                <Link
                  key={inst.symbol}
                  href={`/markets/stocks/${encodeURIComponent(inst.symbol)}`}
                  className="border-b border-nq-border last:border-b-0 px-4 py-3 md:py-4 hover:bg-[rgba(255,255,255,0.02)] transition-colors group"
                >
                  <div className="grid gap-3 md:grid-cols-[1.5fr_1fr_1fr_1fr] md:items-center">
                    {/* Symbol / Name */}
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-nq-text-primary text-sm md:text-base group-hover:text-nq-accent transition-colors">
                          {inst.symbol}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-nq-bg-elevated border border-nq-border text-nq-text-tertiary">
                          {inst.exchange}
                        </span>
                      </div>
                      <span className="text-xs text-nq-text-secondary truncate mt-0.5">
                        {inst.displayName}
                      </span>
                    </div>

                    {/* Price - Mobile Label / Desktop Right Align */}
                    <div className="flex items-center justify-between md:justify-end">
                      <span className="text-xs text-nq-text-tertiary md:hidden">
                        LTP
                      </span>
                      <span className="font-mono text-sm md:text-base flex items-center gap-2">
                        ₹{Number(price).toLocaleString("en-IN", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                        {live?.source && (
                          <span
                            className={cn(
                              "text-[8px] px-1.5 py-0.5 rounded border uppercase tracking-wider font-sans",
                              live.source === "realtime"
                                ? "text-[#00E676] border-[#00E676] bg-[rgba(0,230,118,0.1)]"
                                : live.source === "computed"
                                ? "text-[#B388FF] border-[#B388FF] bg-[rgba(179,136,255,0.1)]"
                                : "text-[#FFB800] border-[#FFB800] bg-[rgba(255,184,0,0.1)]"
                            )}
                          >
                            {live.source === "realtime" ? "Real-time" : live.source === "computed" ? "Computed" : "Delayed"}
                          </span>
                        )}
                      </span>
                    </div>

                    {/* Change - Mobile Label / Desktop Right Align */}
                    <div className="flex items-center justify-between md:justify-end">
                      <span className="text-xs text-nq-text-tertiary md:hidden">
                        Change
                      </span>
                      <span
                        className={cn(
                          "font-mono text-sm md:text-base font-medium px-2 py-1 md:p-0 rounded md:bg-transparent",
                          isPositive
                            ? "text-[#00E676] bg-[rgba(0,230,118,0.1)] md:bg-transparent"
                            : "text-[#FF3B5C] bg-[rgba(255,59,92,0.1)] md:bg-transparent"
                        )}
                      >
                        {isPositive ? "+" : ""}
                        {safeFormat(change, 2)}%
                      </span>
                    </div>

                    {/* Volume - Mobile Label / Desktop Right Align */}
                    <div className="flex items-center justify-between md:justify-end">
                      <span className="text-xs text-nq-text-tertiary md:hidden">
                        Volume
                      </span>
                      <span className="font-mono text-sm text-nq-text-secondary">
                        {Number(volume).toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })
          )}
        </div>
      </div>
      
      {/* Pagination Controls */}
      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-between py-4 border-t border-nq-border">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 text-sm font-medium rounded-md border border-nq-border bg-nq-bg-card text-nq-text-secondary disabled:opacity-50 hover:bg-[rgba(255,255,255,0.02)] transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-nq-text-secondary">
            Page <span className="font-semibold text-nq-text-primary">{currentPage}</span> of{" "}
            <span className="font-semibold text-nq-text-primary">{totalPages}</span>
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 text-sm font-medium rounded-md border border-nq-border bg-nq-bg-card text-nq-text-secondary disabled:opacity-50 hover:bg-[rgba(255,255,255,0.02)] transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
