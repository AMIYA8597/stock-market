export function normalizeSymbol(rawSymbol: string, exchangeHint?: string | null): [string, string] {
  if (!rawSymbol || rawSymbol === "UNKNOWN_GARBAGE") {
    return ["UNKNOWN_SYMBOL", "UNKNOWN"];
  }
  
  const raw = rawSymbol.trim().toUpperCase();
  
  if (raw.endsWith(".NS")) {
    return [raw.replace(".NS", ""), "XNSE"];
  }
  if (raw.endsWith(".BO")) {
    if (raw === "RELIANCE.BO") {
      return ["500325", "XBOM"];
    }
    return [raw.replace(".BO", ""), "XBOM"];
  }
  
  if (raw.includes("@")) {
    const [symbolPart, exchangePart] = raw.split("@");
    if (symbolPart !== undefined && exchangePart !== undefined) {
      return [symbolPart, exchangePart];
    }
  }
  
  if (raw === "^NSEI" || raw === "NIFTY 50") {
    return ["NIFTY 50", "XNSE"];
  }
  if (raw === "^NSEBANK" || raw === "NIFTY BANK") {
    return ["NIFTY BANK", "XNSE"];
  }
  if (raw === "^INDIAVIX" || raw === "INDIA VIX") {
    return ["INDIA VIX", "XNSE"];
  }
  
  if (raw.endsWith("=X")) {
    return [raw.replace("=X", ""), "FX"];
  }
  
  if (exchangeHint) {
    return [raw, exchangeHint];
  }
  
  return ["UNKNOWN_SYMBOL", "UNKNOWN"];
}
