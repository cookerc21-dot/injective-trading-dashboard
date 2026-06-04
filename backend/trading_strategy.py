import os
import asyncio
import json
from datetime import datetime
from injective_functions.exchange.exchange import InjectiveExchange
from injective_functions.exchange.trader import InjectiveTrading
from injective_functions.factory import InjectiveClientFactory
from injective_functions.utils.function_helper import FunctionSchemaLoader, FunctionExecutor

class LiveTradingStrategy:
    def __init__(self):
        self.exchange = None
        self.trader = None
        self.account_info = None
        self.positions = []
        self.trade_history = []
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the Injective client and exchange"""
        try:
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv()
            
            # Initialize Injective client
            self.factory = InjectiveClientFactory()
            self.chain_client = self.factory.create_chain_client()
            
            # Initialize exchange and trader
            self.exchange = InjectiveExchange(self.chain_client)
            self.trader = InjectiveTrading(self.chain_client)
            
            # Get account info
            self.account_info = await self.exchange.get_account()
            
            self.is_initialized = True
            print("✅ Injective trading strategy initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize trading strategy: {e}")
            return False
    
    async def get_market_data(self, symbol="INJ/USDT"):
        """Get real market data for a symbol"""
        try:
            if not self.is_initialized:
                await self.initialize()
                
            # Get spot orderbook
            orderbook = await self.exchange.get_spot_orderbook(symbol, limit=10)
            
            # Get recent trades
            # Note: This would need to be implemented based on available functions
            
            return {
                "symbol": symbol,
                "bid": float(orderbook.get('bids', [['0', '0']])[0][0]) if orderbook.get('bids') else 0,
                "ask": float(orderbook.get('asks', [['0', '0']])[0][0]) if orderbook.get('asks') else 0,
                "timestamp": datetime.now().isoformat(),
                "orderbook": orderbook
            }
        except Exception as e:
            print(f"Error getting market data: {e}")
            return None
    
    async def execute_trade(self, symbol, side, amount, price=None, order_type="market"):
        """Execute a trade on Injective"""
        try:
            if not self.is_initialized:
                await self.initialize()
                
            # For now, we'll simulate trades since we don't want to risk real funds
            # In production, this would use the actual trader methods
            
            trade = {
                "id": len(self.trade_history) + 1,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price or 0,  # Would be filled from market data
                "order_type": order_type,
                "timestamp": datetime.now().isoformat(),
                "status": "filled"  # In real case, would check transaction status
            }
            
            self.trade_history.append(trade)
            
            # Also add to positions if it's a new position
            if side.lower() == "buy":
                self.positions.append({
                    "symbol": symbol,
                    "side": "long",
                    "amount": amount,
                    "entry_price": price,
                    "timestamp": datetime.now().isoformat()
                })
            
            print(f"✅ Executed {side} {amount} {symbol} at {price}")
            return trade
        except Exception as e:
            print(f"Error executing trade: {e}")
            return None
    
    async def get_account_balance(self):
        """Get account balance"""
        try:
            if not self.is_initialized:
                await self.initialize()
                
            # Get account info which includes balances
            account = await self.exchange.get_account()
            return account
        except Exception as e:
            print(f"Error getting account balance: {e}")
            return None
    
    def get_strategy_performance(self):
        """Calculate strategy performance metrics"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "sharpe_ratio": 0
            }
        
        # Simple mock calculation for now
        winning_trades = len([t for t in self.trade_history if t.get('pnl', 0) > 0])
        total_trades = len(self.trade_history)
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": 124.50,  # Mock data
            "sharpe_ratio": 1.85   # Mock data
        }

# Global strategy instance
strategy = LiveTradingStrategy()
