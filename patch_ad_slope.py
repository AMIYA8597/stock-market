import re

with open('backend/nqml/features/fs_v1.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_ad_slope = '''\
@feature("ad_slope", "volume", {"window": 14}, 15, "float32")
def ad_slope(bars: pd.DataFrame) -> pd.Series:
    mfm = ((bars["close"] - bars["low"]) - (bars["high"] - bars["close"])) / (bars["high"] - bars["low"])
    mfm = mfm.fillna(0)
    mfv = mfm * bars["volume"]
    adl = mfv.cumsum()
    return adl.diff(14) / adl.abs().rolling(14).mean()
'''

new_ad_slope = '''\
@feature("ad_slope", "volume", {"window": 14}, 15, "float32")
def ad_slope(bars: pd.DataFrame) -> pd.Series:
    mfm = ((bars["close"] - bars["low"]) - (bars["high"] - bars["close"])) / (bars["high"] - bars["low"])
    mfm = mfm.fillna(0)
    mfv = mfm * bars["volume"]
    ad_diff = mfv.rolling(14).sum()
    ad_abs_sum = mfv.abs().rolling(14).sum()
    return ad_diff / ad_abs_sum
'''

content = content.replace(old_ad_slope, new_ad_slope)

with open('backend/nqml/features/fs_v1.py', 'w', encoding='utf-8') as f:
    f.write(content)
