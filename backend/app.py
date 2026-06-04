"""Multi-asset Injective Dashboard — Flask + CoinGecko API."""
import os
import json
import sys
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trading_strategy import (
    ASSETS,
    fetch_price,
    fetch_historical,
    run_backtest,
    BACKTEST_STRATEGIES,
)

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)

PRICE_HISTORY_CACHE = {}  # asset -> list of price snapshots
MAX_HISTORY_POINTS = 200


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/assets")
def list_assets():
    """Return available trading assets."""
    result = []
    for aid, info in ASSETS.items():
        result.append({
            "id": aid,
            "name": info["name"],
            "type": info["type"],
        })
    return jsonify({"assets": result})


@app.route("/api/price/<asset_id>")
def get_price(asset_id):
    """Live price for one asset."""
    asset_id = asset_id.upper()
    data = fetch_price(asset_id)
    if data is None:
        return jsonify({"error": f"Unknown asset: {asset_id}"}), 404
    return jsonify(data)


@app.route("/api/prices")
def get_all_prices():
    """Prices for all assets."""
    results = {}
    for aid in ASSETS:
        data = fetch_price(aid)
        if data:
            results[aid] = data
    return jsonify({"prices": results, "updated_at": datetime.utcnow().isoformat()})


@app.route("/api/history/<asset_id>")
def get_history(asset_id):
    """Historical OHLCV data."""
    asset_id = asset_id.upper()
    days = request.args.get("days", 7, type=int)
    days = min(max(days, 1), 365)
    candles = fetch_historical(asset_id, days)
    if not candles:
        return jsonify({"error": f"No data for {asset_id}"}), 404
    return jsonify({"asset": asset_id, "days": days, "candles": candles})


@app.route("/api/strategies")
def list_strategies():
    """Available backtest strategies with their default params."""
    return jsonify({
        "strategies": {
            sid: {
                "name": info["name"],
                "description": info["description"],
                "params": info["params"],
            }
            for sid, info in BACKTEST_STRATEGIES.items()
        }
    })


@app.route("/api/backtest", methods=["POST"])
def backtest():
    """Run a backtest with user-supplied parameters."""
    body = request.get_json(force=True) or {}
    asset_id = body.get("asset", "INJ").upper()
    strategy_id = body.get("strategy", "sma_crossover")
    days = min(max(body.get("days", 30), 1), 365)
    params = body.get("params", {})
    capital = float(body.get("capital", 1000))

    if asset_id not in ASSETS:
        return jsonify({"error": f"Unknown asset: {asset_id}"}), 400
    if strategy_id not in BACKTEST_STRATEGIES:
        return jsonify({"error": f"Unknown strategy: {strategy_id}"}), 400

    result = run_backtest(asset_id, strategy_id, days, params, capital)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/stream")
def price_stream():
    """Server-sent events endpoint for real-time price updates."""
    from flask import Response

    def generate():
        while True:
            import time
            for aid in ASSETS:
                data = fetch_price(aid)
                if data:
                    # Cache for chart history
                    if aid not in PRICE_HISTORY_CACHE:
                        PRICE_HISTORY_CACHE[aid] = []
                    PRICE_HISTORY_CACHE[aid].append({
                        "t": datetime.utcnow().isoformat(),
                        "p": data.get("usd"),
                    })
                    if len(PRICE_HISTORY_CACHE[aid]) > MAX_HISTORY_POINTS:
                        PRICE_HISTORY_CACHE[aid] = PRICE_HISTORY_CACHE[aid][-MAX_HISTORY_POINTS:]
                    yield f"data: {json.dumps(data)}\n\n"
            time.sleep(15)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/agent/status")
def agent_status():
    """Check if an on-chain agent is registered for this wallet."""
    private_key = os.environ.get("INJECTIVE_PRIVATE_KEY", "")
    if not private_key:
        return jsonify({
            "registered": False,
            "note": "No INJECTIVE_PRIVATE_KEY set in environment",
        })

    # Derive address from private key (simple check)
    try:
        from eth_account import Account
        acct = Account.from_key(private_key)
        address = acct.address
    except Exception:
        address = "unknown"

    # We can't check the registry directly via REST anymore (API changed),
    # but the registry is at agents.injective.com
    return jsonify({
        "registered": False,
        "address": address,
        "registry_url": "https://agents.injective.com/registry/",
        "setup_guide": "https://agents.injective.com/start",
        "note": "Use `inj-agent` CLI to register on the ERC-8004 registry. Requires ~0.01 INJ gas.",
    })


@app.route("/api/health")
def health():
    """Health check."""
    return jsonify({
        "status": "ok",
        "assets": len(ASSETS),
        "strategies": len(BACKTEST_STRATEGIES),
        "updated_at": datetime.utcnow().isoformat(),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
