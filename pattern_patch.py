import re

with open('backend/app/services/pattern_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

piercing_line = '''            # Piercing Line
            if (
                not prev_bull
                and bull
                and curr_open < prev_close
                and curr_close > (prev_open + prev_close) / 2
                and curr_close < prev_open
                and dn_t
            ):
                markers.append({
                    "time": time_val,
                    "position": "belowBar",
                    "shape": "arrowUp",
                    "color": "#00E676",
                    "text": "Piercing Line",
                })
                continue

            # Dark Cloud Cover
            if (
                prev_bull
                and not bull
                and curr_open > prev_close
                and curr_close < (prev_open + prev_close) / 2
                and curr_close > prev_open
                and up_t
            ):
                markers.append({
                    "time": time_val,
                    "position": "aboveBar",
                    "shape": "arrowDown",
                    "color": "#D81B60",
                    "text": "Dark Cloud Cover",
                })
                continue
'''

content = content.replace('        if i >= 2:', piercing_line + '\n        if i >= 2:')
with open('backend/app/services/pattern_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
