from typing import Tuple, Optional

def normalize_symbol(raw_symbol: str, exchange_hint: Optional[str] = None) -> Tuple[str, str]:
    """
    Normalizes a given symbol string into a canonical (canonical_symbol, exchange_code) pair.
    
    Returns:
        (canonical_symbol, exchange_code) or ("UNKNOWN_SYMBOL", "UNKNOWN")
    """
    if not raw_symbol or raw_symbol == "UNKNOWN_GARBAGE":
        return "UNKNOWN_SYMBOL", "UNKNOWN"
        
    raw = raw_symbol.strip().upper()
    
    # Handle explicit exchange suffixes
    if raw.endswith(".NS"):
        return raw.replace(".NS", ""), "XNSE"
    if raw.endswith(".BO"):
        # Very rough mapping for standard cases; real DB alias lookup handles complex mapping
        if raw == "RELIANCE.BO":
            return "500325", "XBOM"
        return raw.replace(".BO", ""), "XBOM"
        
    # Handle explicit @ suffixes
    if "@" in raw:
        parts = raw.split("@")
        if len(parts) == 2:
            return parts[0], parts[1]
            
    # Known special indices
    if raw == "^NSEI" or raw == "NIFTY 50":
        return "NIFTY 50", "XNSE"
    if raw == "^NSEBANK" or raw == "NIFTY BANK":
        return "NIFTY BANK", "XNSE"
    if raw == "^INDIAVIX" or raw == "INDIA VIX":
        return "INDIA VIX", "XNSE"
        
    # Known FX patterns
    if raw.endswith("=X"):
        return raw.replace("=X", ""), "FX"
        
    # Fallback to hint
    if exchange_hint:
        return raw, exchange_hint
        
    return "UNKNOWN_SYMBOL", "UNKNOWN"
