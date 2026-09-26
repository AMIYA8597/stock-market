
import pandas as pd


def validate_ohlcv_row(row: pd.Series) -> tuple[str, list]:
    """
    Validates a single OHLCV row.
    Returns (quality_status, list_of_flags)
    quality_status in {VALID, WARNING, INVALID}
    """
    flags = []
    status = "VALID"

    # 1. Positive prices
    for col in ['open', 'high', 'low', 'close']:
        if pd.isna(row.get(col)) or row.get(col) <= 0:
            flags.append(f"invalid_{col}")
            status = "INVALID"

    if status == "INVALID":
        return status, flags

    # 2. OHLC Consistency Check
    if row['high'] < max(row['open'], row['close']):
        flags.append("high_less_than_open_or_close")
        status = "INVALID"

    if row['low'] > min(row['open'], row['close']):
        flags.append("low_greater_than_open_or_close")
        status = "INVALID"

    # 3. Volume Check
    if pd.isna(row.get('volume')) or row.get('volume') < 0:
        flags.append("invalid_volume")
        status = "INVALID"
    elif row.get('volume') == 0:
        flags.append("zero_volume")
        if status == "VALID":
            status = "WARNING"

    # 4. Jump detection (e.g. >20% move without corporate action could be a warning)
    # This is simplified; real jump detection requires previous row context.

    return status, flags

def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Applies validation rules to an entire DataFrame and annotates it."""
    if df.empty:
        return df

    statuses = []
    flags_list = []

    for _idx, row in df.iterrows():
        status, flags = validate_ohlcv_row(row)
        statuses.append(status)
        flags_list.append(",".join(flags) if flags else None)

    df['quality_status'] = statuses
    df['quality_flags'] = flags_list

    return df
