from flask import Flask, render_template, jsonify
import json
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trading_strategy import LiveTradingStrategy as TradingStrategy

strategy = TradingStrategy()
app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')


def init_strategy():
    """Initialize the trading strategy (runs once at import time)."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(strategy.initialize())
    except Exception as e:
        print(f"Strategy init (non-fatal): {e}")


# Auto-init on import (safe for both script and gunicorn)
init_strategy()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        market_data = loop.run_until_complete(strategy.get_market_data("INJ/USDT"))
        account_info = loop.run_until_complete(strategy.get_account_balance())
        performance = strategy.get_strategy_performance()

        trades = []
        if strategy.trade_history:
            trades = strategy.trade_history[-10:]

        return jsonify({
            "trades": trades,
            "parameters": {
                "strategy": "mean_reversion",
                "risk_per_trade": 0.02,
                "max_positions": 3,
                "stop_loss": 0.05,
                "take_profit": 0.1
            },
            "market_data": market_data,
            "account_info": account_info,
            "performance": performance
        })
    except Exception as e:
        print(f"Error in get_data: {e}")
        return jsonify({
            "trades": [],
            "parameters": {
                "strategy": "mean_reversion (mock)",
                "risk_per_trade": 0.02,
                "max_positions": 3,
                "stop_loss": 0.05,
                "take_profit": 0.1
            },
            "market_data": {
                "symbol": "INJ/USDT",
                "bid": 8.50,
                "ask": 8.52,
                "timestamp": "2026-06-04T10:00:00Z"
            },
            "account_info": {"balances": []},
            "performance": {
                "total_trades": 0,
                "winning_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "sharpe_ratio": 0
            }
        })


@app.route('/api/execute_trade', methods=['POST'])
def execute_trade():
    return jsonify({"status": "success", "message": "Trade execution endpoint ready"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
