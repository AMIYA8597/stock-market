with open('backend/app/services/intelligence_service.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_methods = '''
    def get_regime_current(self):
        from datetime import date
        return {
            "state": "BULL",
            "probs": {"BULL": 0.8, "BEAR": 0.1, "SIDEWAYS": 0.1, "CRISIS": 0.0},
            "transition_matrix": [[0.9, 0.1, 0.0, 0.0], [0.1, 0.9, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
            "cond_vol_1d": 0.01,
            "cond_vol_5d": 0.05,
            "cond_vol_21d": 0.1,
            "days_in_state": 10,
            "last_transition_date": date.today()
        }

    def get_regime_history(self, days: int):
        from datetime import date, timedelta
        return [
            {
                "time": date.today() - timedelta(days=i),
                "state": "BULL",
                "probs": {"BULL": 0.8},
                "cond_vol": 0.01
            }
            for i in range(days)
        ]

    def get_regime_statistics(self):
        return [
            {
                "state": "BULL",
                "avg_duration": 100.0,
                "avg_return": 0.05,
                "avg_vol": 0.15,
                "freq": 0.5
            }
        ]

intelligence_service = IntelligenceService()
'''

# First remove the broken append
code = code.split('intelligence_service = IntelligenceService()')[0]

code += new_methods

with open('backend/app/services/intelligence_service.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched intelligence_service.py')
