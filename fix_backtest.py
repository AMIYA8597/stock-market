import re

with open('apps/web/src/components/terminal/panes/BacktestingTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(
    r'\} else if \(statusRes\.status === "FAILED"\) \{[\s\S]*?\} else if \(attempts < 5\)',
    r'} else if (statusRes.status === "FAILED") {\n          setBacktestLoading(false);\n          setBacktestStats(null);\n          console.error("Backtest failed on backend");\n        } else if (attempts < 5)',
    text
)

text = re.sub(
    r'\} else \{[\s]*setBacktestLoading\(false\);[\s]*setBacktestStats\(\{[\s\S]*?\}\);[\s]*\}',
    r'} else {\n          setBacktestLoading(false);\n          setBacktestStats(null);\n          console.error("Backtest timed out");\n        }',
    text
)

text = re.sub(
    r'catch \(e\) \{[\s\S]*?setTimeout\(\(\) => \{[\s\S]*?setBacktestStats\(\{[\s\S]*?\}\);[\s]*setBacktestLoading\(false\);[\s]*\}, 1000\);[\s]*\}',
    r'catch (e) {\n      console.error(e);\n      setBacktestLoading(false);\n      setBacktestStats(null);\n    }',
    text
)

with open('apps/web/src/components/terminal/panes/BacktestingTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
