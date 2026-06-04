from flask import Flask, render_template, jsonify
import json
import os
import asyncio
from .trading_strategy import strategy

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Initialize strategy on startup
def init_strategy():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(strategy.initialize())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    # Get real market data and strategy performance
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get market data
        market_data = loop.run_until_complete(strategy.get_market_data("INJ/USDT"))
        
        # Get account info
        account_info = loop.run_until_complete(strategy.get_account_balance())
        
        # Get strategy performance
        performance = strategy.get_strategy_performance()
        
        # Generate some mock trades for display (in real implementation, these would come from blockchain)
        trades = [
            {"id": 1, "symbol": "INJ/USDT", "side": "buy", "amount": 10.5, "price": 8.50, "timestamp": "2026-06-04T10:00:00Z"},
            {"id": 2, "symbol": "INJ/USDT", "side": "sell", "amount": 5.2, "price": 8.55, "timestamp": "2026-06-04T10:05:00Z"},
        ]
        
        # If we have real trade history, use it
        if strategy.trade_history:
            trades = strategy.trade_history[-10:]  # Last 10 trades
        
        data = {
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
        }
        
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_data: {e}")
        # Return mock data on error
        return jsonify({
            "trades": [
                {"id": 1, "symbol": "INJ/USDT", "side": "buy", "amount": 10.5, "price": 8.50, "timestamp": "2026-06-04T10:00:00Z"},
                {"id": 2, "symbol": "INJ/USDT", "side": "sell", "amount": 5.2, "price": 8.55, "timestamp": "2026-06-04T10:05:00Z"},
            ],
            "parameters": {
                "strategy": "mean_reversion",
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
    # This would be used for manual trade execution
    # For now, we'll just return a success message
    return jsonify({"status": "success", "message": "Trade execution endpoint ready"})

if __name__ == '__main__':
    # Initialize strategy before starting the app
    init_strategy()
    app.run(host='0.0.0.0', port=5000, debug=True)
