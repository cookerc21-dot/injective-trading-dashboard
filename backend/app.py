from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Mock data for live trades and parameters
def get_mock_data():
    return {
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
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return jsonify(get_mock_data())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
