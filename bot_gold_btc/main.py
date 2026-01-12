import time
import sys
import signal
from datetime import datetime
import traceback
import requests
import MetaTrader5 as mt5

TELEGRAM_TOKEN = "8390637051:AAH03kUKFrNrRWeH7GCGLpk_AL8CI7TXVr4"
TELEGRAM_CHAT_ID = "7617748614"

try:
    from .config import (
        SYMBOL_GOLD, SYMBOL_BTC, CHECK_INTERVAL, CONNECTION_CHECK_INTERVAL,
        MAX_RECONNECTION_ATTEMPTS, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
    )
    from .mt5_interface import MT5Interface
    from .strategy import PairsTradingStrategy
    from .risk_manager import RiskManager
    from .performance_tracker import PerformanceTracker
    from .logger import TradingLogger
except ImportError:
    from config import (
        SYMBOL_GOLD, SYMBOL_BTC, CHECK_INTERVAL, CONNECTION_CHECK_INTERVAL,
        MAX_RECONNECTION_ATTEMPTS, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
    )
    from mt5_interface import MT5Interface
    from strategy import PairsTradingStrategy
    from risk_manager import RiskManager
    from performance_tracker import PerformanceTracker
    from logger import TradingLogger

logger = TradingLogger()

class PairsTradingBot:
    
    def __init__(self):
        self.mt5_interface = MT5Interface()
        self.strategy = PairsTradingStrategy(self.mt5_interface)
        self.risk_manager = RiskManager(self.mt5_interface)
        self.performance_tracker = PerformanceTracker()
        self.running = False
        self.reconnection_attempts = 0
        self.last_connection_check = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10

    def send_telegram(self, message):
        if "COLLE_TON" in TELEGRAM_TOKEN:
            return
            
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.log_error(f"Erreur envoi Telegram : {e}")

    def signal_handler(self, signum, frame):
        print("\n🛑 Arrêt du bot demandé...")
        self.send_telegram("🛑 **Bot Arbitrage Arrêté manuellement**")
        self.running = False
        logger.log_info("Arrêt du bot demandé par l'utilisateur")
    
    def check_connection(self) -> bool:
        try:
            if not mt5.initialize():
                return False
            
            account_info = mt5.account_info()
            if account_info is None:
                return False
            
            return True
        except Exception as e:
            logger.log_error(f"Erreur lors de la vérification de connexion: {e}")
            return False
    
    def reconnect(self) -> bool:
        self.reconnection_attempts += 1
        
        if self.reconnection_attempts > MAX_RECONNECTION_ATTEMPTS:
            msg = f"❌ **ERREUR CRITIQUE** : Échec reconnexion MT5 après {MAX_RECONNECTION_ATTEMPTS} tentatives."
            logger.log_error(msg)
            self.send_telegram(msg)
            return False
        
        print(f"🔄 Tentative de reconnexion {self.reconnection_attempts}/{MAX_RECONNECTION_ATTEMPTS}...")
        
        try:
            self.mt5_interface.disconnect()
        except:
            pass
        
        time.sleep(5)
        
        if self.mt5_interface.connect():
            print("✅ Reconnexion réussie")
            self.send_telegram("✅ **Reconnexion MT5 réussie**")
            logger.log_info("Reconnexion réussie")
            self.reconnection_attempts = 0
            self.consecutive_errors = 0
            return True
        else:
            print(f"❌ Échec de la reconnexion")
            return False
    
    def initialize(self) -> bool:
        print("=" * 70)
        print("📊 BOT DE STATISTICAL ARBITRAGE (PAIRS TRADING)")
        print("   XAUUSD / BTCUSD - Z-Score Strategy")
        print("=" * 70)
        
        print("🔌 Connexion à MetaTrader 5...")
        if not self.mt5_interface.connect():
            print("❌ Échec de la connexion à MT5")
            return False
        
        print("✅ Connecté à MT5")
        
        print("🔍 Vérification des symboles...")
        symbols_to_check = [SYMBOL_GOLD, SYMBOL_BTC]
        for symbol in symbols_to_check:
            info = self.mt5_interface.get_symbol_info(symbol)
            if not info:
                print(f"   ❌ {symbol} non disponible - ARRÊT")
                return False
        
        account_info = mt5.account_info()
        if account_info:
            start_msg = f"""
🚀 **BOT ARBITRAGE DÉMARRÉ** 🚀
💰 Balance : {account_info.balance:.2f} {account_info.currency}
📊 Equity : {account_info.equity:.2f} {account_info.currency}
LEV : 1:{account_info.leverage}
            """
            self.send_telegram(start_msg)
            
            self.performance_tracker.start_session(
                account_info.balance,
                account_info.equity
            )
        
        return True
    
    def close_pairs_positions(self):
        try:
            gold_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_GOLD)
            btc_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_BTC)
            
            pnl_total = 0
            
            for _, pos in gold_positions.iterrows():
                pnl_total += pos['profit']
                self.mt5_interface.close_position(pos['ticket'])
            
            for _, pos in btc_positions.iterrows():
                pnl_total += pos['profit']
                self.mt5_interface.close_position(pos['ticket'])
                
            if not gold_positions.empty or not btc_positions.empty:
                self.send_telegram(f"🏁 **POSITIONS FERMÉES**\nP&L Total : {pnl_total:.2f} $")

        except Exception as e:
            logger.log_error(f"Erreur lors de la fermeture des positions: {e}")
    
    def execute_pairs_trade(self, signal: dict):
        try:
            allowed, reason = self.risk_manager.should_allow_trade()
            if not allowed:
                logger.log_error(f"Trading bloqué: {reason}")
                return
            
            gold_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_GOLD)
            btc_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_BTC)
            
            if not gold_positions.empty or not btc_positions.empty:
                return
            
            gold_price = signal['gold_price']
            btc_price = signal['btc_price']
            z_score = abs(signal['z_score'])
            estimated_stop_pct = z_score * 0.01
            volatility = (signal.get('atr_gold_pct', 0) + signal.get('atr_btc_pct', 0)) / 2
            
            gold_lots, risk_pct_gold = self.risk_manager.calculate_dynamic_position_size(
                SYMBOL_GOLD, gold_price, gold_price * (1 - estimated_stop_pct),
                risk_percent=None, z_score=signal['z_score'], volatility=volatility
            )
            
            btc_lots, risk_pct_btc = self.risk_manager.calculate_dynamic_position_size(
                SYMBOL_BTC, btc_price, btc_price * (1 - estimated_stop_pct),
                risk_percent=None, z_score=signal['z_score'], volatility=volatility
            )
            
            if gold_lots <= 0 or btc_lots <= 0:
                return
            
            gold_prices = self.mt5_interface.get_current_price(SYMBOL_GOLD)
            btc_prices = self.mt5_interface.get_current_price(SYMBOL_BTC)
            
            if not gold_prices or not btc_prices:
                return

            gold_bid, gold_ask = gold_prices
            btc_bid, btc_ask = btc_prices
            
            gold_order_type = mt5.ORDER_TYPE_SELL if signal['gold_action'] == 'SELL' else mt5.ORDER_TYPE_BUY
            btc_order_type = mt5.ORDER_TYPE_SELL if signal['btc_action'] == 'SELL' else mt5.ORDER_TYPE_BUY
            
            gold_price_entry = gold_ask if signal['gold_action'] == 'BUY' else gold_bid
            btc_price_entry = btc_ask if signal['btc_action'] == 'BUY' else btc_bid
            
            gold_ticket = self.mt5_interface.place_order(
                symbol=SYMBOL_GOLD, order_type=gold_order_type, volume=gold_lots,
                price=gold_price_entry, comment="Pairs Trading - Gold"
            )
            
            btc_ticket = self.mt5_interface.place_order(
                symbol=SYMBOL_BTC, order_type=btc_order_type, volume=btc_lots,
                price=btc_price_entry, comment="Pairs Trading - BTC"
            )
            
            if gold_ticket and btc_ticket:
                msg = f"""
⚡ **EXECUTION ARBITRAGE** ⚡
📈 Z-Score : {signal['z_score']:.2f}

🟡 **GOLD** ({signal['gold_action']})
Prix : {gold_price_entry:.2f}
Lots : {gold_lots:.2f}

🟠 **BTC** ({signal['btc_action']})
Prix : {btc_price_entry:.2f}
Lots : {btc_lots:.2f}

🎯 Gain Potentiel : {signal['potential_gain_pct']*100:.2f}%
                """
                self.send_telegram(msg)
                print(f"✅ Paire exécutée: Gold Ticket {gold_ticket}, BTC Ticket {btc_ticket}")

            else:
                if gold_ticket and not btc_ticket:
                    self.mt5_interface.close_position(gold_ticket)
                    self.send_telegram("⚠️ **ERREUR EXECUTION** : Ordre BTC échoué, fermeture Gold.")
                elif btc_ticket and not gold_ticket:
                    self.mt5_interface.close_position(btc_ticket)
                    self.send_telegram("⚠️ **ERREUR EXECUTION** : Ordre Gold échoué, fermeture BTC.")
        
        except Exception as e:
            logger.log_error(f"Erreur lors de l'exécution du trade de paire: {e}")
            traceback.print_exc()
            self.consecutive_errors += 1
    
    def run(self):
        if not self.initialize():
            return
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        print("🚀 Bot démarré! Appuyez sur Ctrl+C pour arrêter.")
        
        iteration = 0
        
        try:
            while self.running:
                heure = datetime.now().strftime('%H:%M:%S')
                current_z = getattr(self.strategy, 'last_zscore', 0.0)
                print(f"[{heure}] 🔍 Scan... Z-Score: {current_z:.2f}", flush=True)

                iteration += 1
                current_time = time.time()
                
                if current_time - self.last_connection_check >= CONNECTION_CHECK_INTERVAL:
                    self.last_connection_check = current_time
                    if not self.check_connection():
                        self.send_telegram("⚠️ **Alerte** : Connexion MT5 perdue")
                        if not self.reconnect():
                            break
                
                circuit_breaker, reason_cb = self.risk_manager.check_circuit_breaker_pair()
                if circuit_breaker:
                    msg = f"🛑 **CIRCUIT BREAKER ACTIVÉ** : {reason_cb}"
                    print(msg)
                    self.send_telegram(msg)
                    self.close_pairs_positions()
                    break
                
                try:
                    should_close, close_reason = self.strategy.should_close_pairs_position()
                    if should_close:
                        print(f"🔄 Fermeture de la paire: {close_reason}")
                        self.send_telegram(f"🔄 **Signal de Fermeture** : {close_reason}")
                        self.close_pairs_positions()
                    
                    signal_data = self.strategy.analyze_pairs_opportunity()
                    if signal_data:
                        self.execute_pairs_trade(signal_data)
                    
                    risk_metrics = self.risk_manager.get_risk_metrics()
                    self.performance_tracker.update_equity(risk_metrics.get('equity', 0))
                    
                    self.consecutive_errors = 0
                
                except Exception as e:
                    self.consecutive_errors += 1
                    logger.log_error(f"Erreur boucle: {e}")
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        self.send_telegram(f"❌ **CRASH BOT** : {self.consecutive_errors} erreurs consécutives.")
                        break
                
                time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n🛑 Interruption clavier détectée")
        except Exception as e:
            self.send_telegram(f"❌ **ERREUR FATALE** : {e}")
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def shutdown(self):
        print("🛑 ARRÊT DU BOT")
        self.mt5_interface.disconnect()
        logger.log_info("Bot arrêté")

def main():
    bot = PairsTradingBot()
    bot.run()

if __name__ == "__main__":
    main()