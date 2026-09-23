with open('backend/tests/integration/test_api_backtest.py', 'r') as f:
    code = f.read()

import re
replacement = """    job.results = {
        'metrics': {
            'total_return': 10.5, 
            'cagr': 5.2, 
            'sharpe': 1.1,
            'max_drawdown': 0.1,
            'max_drawdown_duration_days': 5,
            'win_rate': 0.6,
            'avg_win': 1.5,
            'avg_loss': 1.0,
            'payoff_ratio': 1.5,
            'num_trades': 10,
            'gross_profit': 15.0,
            'gross_loss': 4.5,
            'sortino': 1.2,
            'calmar': 1.3,
            'omega': 1.4,
            'deflated_sharpe': 1.5
        },
        'equity_curve': [{'date': '2023-01-10', 'equity': 110500}],
        'drawdown_series': [],
        'trade_log': [],
    }"""
# Using a simpler replace
code = re.sub(r"    job\.results = \{.*?'trade_log': \[\],\n    \}", replacement, code, flags=re.DOTALL)
with open('backend/tests/integration/test_api_backtest.py', 'w') as f:
    f.write(code)
print('Fixed job.results mock!')
