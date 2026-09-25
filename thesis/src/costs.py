import yaml
import os

def load_costs_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'costs.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def calculate_delivery_round_trip(buy_price, sell_price, quantity):
    """
    Calculates the net profit/loss after all costs for a delivery trade.
    """
    config = load_costs_config()['delivery']
    
    buy_value = buy_price * quantity
    sell_value = sell_price * quantity
    
    # Buy side costs
    buy_stt = buy_value * config['stt']
    buy_stamp = buy_value * config['stamp_duty']
    buy_exc = buy_value * config['exchange']
    buy_sebi = buy_value * config['sebi']
    buy_gst = (buy_exc + buy_sebi) * config['gst']
    buy_slippage = buy_value * config['slippage']
    
    total_buy_cost = buy_stt + buy_stamp + buy_exc + buy_sebi + buy_gst + buy_slippage
    
    # Sell side costs
    sell_stt = sell_value * config['stt']
    sell_exc = sell_value * config['exchange']
    sell_sebi = sell_value * config['sebi']
    sell_gst = (sell_exc + sell_sebi) * config['gst']
    sell_dp = config['dp_charge']
    sell_slippage = sell_value * config['slippage']
    
    total_sell_cost = sell_stt + sell_exc + sell_sebi + sell_gst + sell_dp + sell_slippage
    
    gross_pnl = sell_value - buy_value
    net_pnl = gross_pnl - total_buy_cost - total_sell_cost
    
    # Return gross, net, and total cost percentage relative to buy value
    return {
        'gross_pnl': gross_pnl,
        'net_pnl': net_pnl,
        'total_costs': total_buy_cost + total_sell_cost,
        'cost_pct_of_buy': (total_buy_cost + total_sell_cost) / buy_value
    }

if __name__ == "__main__":
    # Test hand-computed Rs 1,00,000 round-trip example
    # Assume buy at 1000, qty 100, sell at 1000 (0% return)
    # The costs should be approximately 0.34% of 1,00,000 = Rs 340.
    res = calculate_delivery_round_trip(1000.0, 1000.0, 100)
    print(f"Costs on Rs 1,00,000 round trip (0% return): {res['total_costs']}")
    print(f"As percentage: {res['cost_pct_of_buy'] * 100:.4f}%")
