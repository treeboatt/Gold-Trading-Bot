"""
Bot de Statistical Arbitrage (Pairs Trading) automatisé
Système robuste pour VPS avec reconnexion automatique
"""

import time
import sys
import signal
from datetime import datetime
import traceback

import MetaTrader5 as mt5

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
    """Bot de pairs trading avec reconnexion automatique"""
    
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
    
    def signal_handler(self, signum, frame):
        """Gère l'arrêt propre du bot (Ctrl+C)"""
        print("\n🛑 Arrêt du bot demandé...")
        self.running = False
        logger.log_info("Arrêt du bot demandé par l'utilisateur")
    
    def check_connection(self) -> bool:
        """
        Vérifie la connexion à MT5
        
        Returns:
            True si connecté, False sinon
        """
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
        """
        Tente de se reconnecter à MT5
        
        Returns:
            True si reconnexion réussie, False sinon
        """
        self.reconnection_attempts += 1
        
        if self.reconnection_attempts > MAX_RECONNECTION_ATTEMPTS:
            logger.log_error(f"Nombre maximum de tentatives de reconnexion atteint ({MAX_RECONNECTION_ATTEMPTS})")
            return False
        
        print(f"🔄 Tentative de reconnexion {self.reconnection_attempts}/{MAX_RECONNECTION_ATTEMPTS}...")
        logger.log_info(f"Tentative de reconnexion {self.reconnection_attempts}/{MAX_RECONNECTION_ATTEMPTS}")
        
        # Déconnecter proprement
        try:
            self.mt5_interface.disconnect()
        except:
            pass
        
        # Attendre un peu avant de reconnecter
        time.sleep(5)
        
        # Reconnecter
        if self.mt5_interface.connect():
            print("✅ Reconnexion réussie")
            logger.log_info("Reconnexion réussie")
            self.reconnection_attempts = 0
            self.consecutive_errors = 0
            return True
        else:
            print(f"❌ Échec de la reconnexion")
            return False
    
    def initialize(self) -> bool:
        """Initialise le bot et se connecte à MT5"""
        print("=" * 70)
        print("📊 BOT DE STATISTICAL ARBITRAGE (PAIRS TRADING)")
        print("   XAUUSD / BTCUSD - Z-Score Strategy")
        print("=" * 70)
        print(f"📅 Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Vérifier la configuration
        if not MT5_LOGIN or MT5_PASSWORD == "votre_mot_de_passe":
            print("⚠️  ATTENTION: Identifiants MT5 non configurés dans config.py")
            print("   Le bot fonctionnera en mode démo uniquement")
            print()
        
        # Connexion à MT5
        print("🔌 Connexion à MetaTrader 5...")
        if not self.mt5_interface.connect():
            print("❌ Échec de la connexion à MT5")
            return False
        
        print("✅ Connecté à MT5")
        print()
        
        # Vérifier que les symboles sont disponibles
        print("🔍 Vérification des symboles...")
        symbols_to_check = [SYMBOL_GOLD, SYMBOL_BTC]
        for symbol in symbols_to_check:
            info = self.mt5_interface.get_symbol_info(symbol)
            if info:
                print(f"   ✅ {symbol} disponible")
            else:
                print(f"   ❌ {symbol} non disponible - ARRÊT")
                return False
        print()
        
        # Afficher les informations du compte
        account_info = mt5.account_info()
        if account_info:
            print("📊 INFORMATIONS DU COMPTE:")
            print(f"   Login: {account_info.login}")
            print(f"   Balance: {account_info.balance:.2f} {account_info.currency}")
            print(f"   Equity: {account_info.equity:.2f} {account_info.currency}")
            print(f"   Marge libre: {account_info.margin_free:.2f} {account_info.currency}")
            print(f"   Levier: 1:{account_info.leverage}")
            print()
            
            # Vérifier le levier
            if account_info.leverage > 3:
                print(f"⚠️  ATTENTION: Levier {account_info.leverage}:1 dépasse la limite 1:3")
                print("   Le bot peut refuser de trader pour sécurité")
            print()
            
            # Démarrer le tracking de performance
            self.performance_tracker.start_session(
                account_info.balance,
                account_info.equity
            )
        
        logger.log_info("Bot initialisé avec succès", 
                       balance=account_info.balance if account_info else None,
                       equity=account_info.equity if account_info else None)
        
        return True
    
    def close_pairs_positions(self):
        """Ferme toutes les positions de la paire"""
        try:
            gold_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_GOLD)
            btc_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_BTC)
            
            for _, pos in gold_positions.iterrows():
                print(f"🔄 Fermeture position Gold {pos['ticket']}...")
                self.mt5_interface.close_position(pos['ticket'])
            
            for _, pos in btc_positions.iterrows():
                print(f"🔄 Fermeture position BTC {pos['ticket']}...")
                self.mt5_interface.close_position(pos['ticket'])
        except Exception as e:
            logger.log_error(f"Erreur lors de la fermeture des positions: {e}")
    
    def execute_pairs_trade(self, signal: dict):
        """
        Exécute un trade de paire (Gold + BTC simultanément)
        
        Args:
            signal: Dictionnaire avec les informations du signal
        """
        try:
            # Vérifier le circuit breaker et le levier
            allowed, reason = self.risk_manager.should_allow_trade()
            if not allowed:
                print(f"⛔ Trading bloqué: {reason}")
                logger.log_error(f"Trading bloqué: {reason}")
                return
            
            # Vérifier qu'il n'y a pas déjà de positions
            gold_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_GOLD)
            btc_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_BTC)
            
            if not gold_positions.empty or not btc_positions.empty:
                print(f"⏸️  Positions déjà ouvertes, signal ignoré")
                logger.log_info("Signal ignoré: positions déjà ouvertes")
                return
            
            # Calculer la taille de position pour Gold
            # Pour le pairs trading, on risque 0.5% sur chaque position
            # Le stop loss est basé sur le Z-Score (retour à la moyenne)
            gold_price = signal['gold_price']
            btc_price = signal['btc_price']
            
            # Estimation du stop loss basé sur le Z-Score
            # Si Z-Score = 2.5, on s'attend à un retour à 0, soit ~2.5 écarts-types
            z_score = abs(signal['z_score'])
            estimated_stop_pct = z_score * 0.01  # 1% par écart-type
            
            # Volatilité moyenne pour ajustement adaptatif
            volatility = (signal.get('atr_gold_pct', 0) + signal.get('atr_btc_pct', 0)) / 2
            
            # Calculer les lots avec risque adaptatif (0.5% à 1%)
            gold_lots, risk_pct_gold = self.risk_manager.calculate_dynamic_position_size(
                SYMBOL_GOLD, gold_price, gold_price * (1 - estimated_stop_pct),
                risk_percent=None,  # Calcul adaptatif
                z_score=signal['z_score'],
                volatility=volatility
            )
            
            btc_lots, risk_pct_btc = self.risk_manager.calculate_dynamic_position_size(
                SYMBOL_BTC, btc_price, btc_price * (1 - estimated_stop_pct),
                risk_percent=None,  # Calcul adaptatif
                z_score=signal['z_score'],
                volatility=volatility
            )
            
            if gold_lots <= 0 or btc_lots <= 0:
                print(f"⚠️  Taille de position invalide: Gold={gold_lots}, BTC={btc_lots}")
                logger.log_error(f"Taille de position invalide")
                return
            
            # Récupérer les prix actuels
            gold_prices = self.mt5_interface.get_current_price(SYMBOL_GOLD)
            btc_prices = self.mt5_interface.get_current_price(SYMBOL_BTC)
            
            if gold_prices is None or btc_prices is None:
                logger.log_error("Impossible de récupérer les prix")
                return
            
            gold_bid, gold_ask = gold_prices
            btc_bid, btc_ask = btc_prices
            
            # Afficher les informations
            print()
            print("=" * 70)
            print(f"📊 SIGNAL PAIRS TRADING DÉTECTÉ")
            print("=" * 70)
            print(f"Action: {signal['action']}")
            print(f"Z-Score: {signal['z_score']:.2f}")
            print(f"Gold: {signal['gold_price']:.2f} | BTC: {signal['btc_price']:.2f}")
            print(f"Ratio actuel: {signal['current_ratio']:.6f}")
            print(f"Ratio moyen: {signal['ratio_mean']:.6f}")
            print(f"Gain potentiel: {signal['potential_gain_pct']*100:.2f}%")
            print(f"Lots Gold: {gold_lots:.2f} (Risque: {risk_pct_gold*100:.2f}%) | Lots BTC: {btc_lots:.2f} (Risque: {risk_pct_btc*100:.2f}%)")
            print(f"Fenêtre Z-Score: {signal.get('window_used', 'N/A')} | ATR Gold: {signal.get('atr_gold_pct', 0)*100:.3f}%")
            print(f"Raison: {signal['reason']}")
            print("=" * 70)
            print()
            
            # Exécuter les ordres
            gold_order_type = mt5.ORDER_TYPE_SELL if signal['gold_action'] == 'SELL' else mt5.ORDER_TYPE_BUY
            btc_order_type = mt5.ORDER_TYPE_SELL if signal['btc_action'] == 'SELL' else mt5.ORDER_TYPE_BUY
            
            gold_price_entry = gold_ask if signal['gold_action'] == 'BUY' else gold_bid
            btc_price_entry = btc_ask if signal['btc_action'] == 'BUY' else btc_bid
            
            # Placer les ordres
            gold_ticket = self.mt5_interface.place_order(
                symbol=SYMBOL_GOLD,
                order_type=gold_order_type,
                volume=gold_lots,
                price=gold_price_entry,
                comment="Pairs Trading - Gold"
            )
            
            btc_ticket = self.mt5_interface.place_order(
                symbol=SYMBOL_BTC,
                order_type=btc_order_type,
                volume=btc_lots,
                price=btc_price_entry,
                comment="Pairs Trading - BTC"
            )
            
            if gold_ticket and btc_ticket:
                print(f"✅ Paire exécutée: Gold Ticket {gold_ticket}, BTC Ticket {btc_ticket}")
                logger.log_info(f"Paire exécutée: Gold {gold_ticket}, BTC {btc_ticket}")
                
                # Enregistrer les trades dans le performance tracker
                import uuid
                trade_id = str(uuid.uuid4())
                
                # Récupérer les coûts de spread
                gold_costs = self.risk_manager.calculate_trading_costs(
                    SYMBOL_GOLD, gold_lots, gold_price_entry, signal['gold_action'] == 'BUY'
                )
                btc_costs = self.risk_manager.calculate_trading_costs(
                    SYMBOL_BTC, btc_lots, btc_price_entry, signal['btc_action'] == 'BUY'
                )
                
                # Enregistrer Gold
                self.performance_tracker.record_trade(
                    f"{trade_id}_gold",
                    SYMBOL_GOLD,
                    signal['gold_action'],
                    gold_price_entry,
                    None,  # Exit price (sera mis à jour à la sortie)
                    gold_lots,
                    None,  # Profit (sera calculé à la sortie)
                    datetime.now(),
                    None,
                    signal['z_score'],
                    gold_costs['total_cost']
                )
                
                # Enregistrer BTC
                self.performance_tracker.record_trade(
                    f"{trade_id}_btc",
                    SYMBOL_BTC,
                    signal['btc_action'],
                    btc_price_entry,
                    None,
                    btc_lots,
                    None,
                    datetime.now(),
                    None,
                    signal['z_score'],
                    btc_costs['total_cost']
                )
            else:
                print(f"❌ Échec partiel: Gold {gold_ticket}, BTC {btc_ticket}")
                # Si un seul ordre a réussi, fermer l'autre
                if gold_ticket and not btc_ticket:
                    self.mt5_interface.close_position(gold_ticket)
                elif btc_ticket and not gold_ticket:
                    self.mt5_interface.close_position(btc_ticket)
        
        except Exception as e:
            logger.log_error(f"Erreur lors de l'exécution du trade de paire: {e}")
            traceback.print_exc()
            self.consecutive_errors += 1
    
    def run(self):
        """Boucle principale du bot avec reconnexion automatique"""
        if not self.initialize():
            print("❌ Échec de l'initialisation. Arrêt du bot.")
            return
        
        # Configurer le gestionnaire de signaux
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        print("🚀 Bot démarré! Appuyez sur Ctrl+C pour arrêter.")
        print(f"🔄 Vérification connexion toutes les {CONNECTION_CHECK_INTERVAL} secondes")
        print()
        
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                current_time = time.time()
                
                # Vérifier la connexion toutes les 15 secondes
                if current_time - self.last_connection_check >= CONNECTION_CHECK_INTERVAL:
                    self.last_connection_check = current_time
                    
                    if not self.check_connection():
                        print(f"⚠️  Connexion perdue à {datetime.now().strftime('%H:%M:%S')}")
                        logger.log_error("Connexion MT5 perdue")
                        
                        if not self.reconnect():
                            print("❌ Impossible de se reconnecter. Arrêt du bot.")
                            break
                
                # Vérifier le circuit breaker
                circuit_breaker, reason_cb = self.risk_manager.check_circuit_breaker_pair()
                if circuit_breaker:
                    print(f"🛑 CIRCUIT BREAKER ACTIVÉ: {reason_cb}")
                    logger.log_error(f"CIRCUIT BREAKER: {reason_cb}")
                    self.close_pairs_positions()
                    break
                
                # Vérifier le levier
                leverage_exceeded, reason_lev = self.risk_manager.check_leverage_limit()
                if leverage_exceeded:
                    print(f"⛔ LEVIER DÉPASSÉ: {reason_lev}")
                    logger.log_error(f"LEVIER: {reason_lev}")
                    # Ne pas trader mais continuer à surveiller
                
                try:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Itération #{iteration}")
                    
                    # Vérifier si on doit fermer les positions (Z-Score retour à 0)
                    should_close, close_reason = self.strategy.should_close_pairs_position()
                    if should_close:
                        print(f"🔄 Fermeture de la paire: {close_reason}")
                        self.close_pairs_positions()
                    
                    # Analyser l'opportunité de pairs trading
                    signal = self.strategy.analyze_pairs_opportunity()
                    
                    if signal:
                        self.execute_pairs_trade(signal)
                    else:
                        # Afficher le Z-Score actuel
                        z_score = self.strategy.get_current_z_score()
                        if z_score is not None:
                            print(f"   Z-Score actuel: {z_score:.2f} (pas de signal)")
                    
                    # Afficher le statut des positions
                    gold_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_GOLD)
                    btc_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_BTC)
                    
                    if not gold_positions.empty or not btc_positions.empty:
                        print(f"   📈 Positions ouvertes:")
                        total_pnl = 0.0
                        
                        if not gold_positions.empty:
                            for _, pos in gold_positions.iterrows():
                                pos_type = "LONG" if pos['type'] == 0 else "SHORT"
                                print(f"      Gold {pos_type}: {pos['volume']} lots @ {pos['price_open']:.2f} (P&L: {pos['profit']:.2f})")
                                total_pnl += pos['profit']
                        
                        if not btc_positions.empty:
                            for _, pos in btc_positions.iterrows():
                                pos_type = "LONG" if pos['type'] == 0 else "SHORT"
                                print(f"      BTC {pos_type}: {pos['volume']} lots @ {pos['price_open']:.2f} (P&L: {pos['profit']:.2f})")
                                total_pnl += pos['profit']
                        
                        print(f"      Total P&L paire: {total_pnl:.2f}")
                    
                    # Mettre à jour l'equity dans le tracker
                    risk_metrics = self.risk_manager.get_risk_metrics()
                    current_equity = risk_metrics.get('equity', 0)
                    self.performance_tracker.update_equity(current_equity)
                    
                    # Afficher les métriques
                    perf_metrics = self.performance_tracker.get_latest_metrics()
                    print(f"   💰 Equity: {current_equity:.2f}")
                    if perf_metrics.get('total_trades', 0) > 0:
                        print(f"   📊 Session: {perf_metrics.get('total_trades', 0)} trades | "
                              f"Win Rate: {perf_metrics.get('win_rate', 0):.1f}% | "
                              f"Sharpe: {perf_metrics.get('sharpe_ratio', 0):.2f} | "
                              f"P&L: {perf_metrics.get('total_net_profit', 0):.2f}")
                    
                    # Réinitialiser le compteur d'erreurs en cas de succès
                    self.consecutive_errors = 0
                
                except Exception as e:
                    self.consecutive_errors += 1
                    logger.log_error(f"Erreur dans la boucle principale: {e}")
                    traceback.print_exc()
                    
                    # Arrêter si trop d'erreurs consécutives
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        print(f"❌ Trop d'erreurs consécutives ({self.consecutive_errors}). Arrêt du bot.")
                        logger.log_error(f"Arrêt: {self.consecutive_errors} erreurs consécutives")
                        break
                
                print()
                
                # Attendre avant la prochaine itération
                time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n🛑 Interruption clavier détectée")
        except Exception as e:
            print(f"\n❌ Erreur fatale: {e}")
            logger.log_error(f"Erreur fatale: {e}")
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Arrêt propre du bot"""
        print()
        print("=" * 70)
        print("🛑 ARRÊT DU BOT")
        print("=" * 70)
        
        # Afficher les positions restantes
        positions = self.mt5_interface.get_open_positions()
        if not positions.empty:
            print(f"⚠️  {len(positions)} position(s) encore ouverte(s)")
            print("   Les positions resteront actives sur MT5")
        
        # Terminer la session de performance
        account_info = mt5.account_info()
        if account_info:
            self.performance_tracker.end_session(
                account_info.balance,
                account_info.equity
            )
            
            # Afficher les métriques finales
            final_metrics = self.performance_tracker.get_latest_metrics()
            if final_metrics:
                print()
                print("📊 MÉTRIQUES FINALES DE LA SESSION:")
                print(f"   Trades: {final_metrics.get('total_trades', 0)}")
                print(f"   Win Rate: {final_metrics.get('win_rate', 0):.2f}%")
                print(f"   Profit Net: {final_metrics.get('total_net_profit', 0):.2f}")
                print(f"   Sharpe Ratio: {final_metrics.get('sharpe_ratio', 0):.2f}")
                print(f"   Drawdown Max: {final_metrics.get('max_drawdown_pct', 0):.2f}%")
                print(f"   Rendement: {final_metrics.get('return_pct', 0):.2f}%")
                print(f"   Rendement Mensuel Estimé: {final_metrics.get('monthly_return_pct', 0):.2f}%")
        
        # Déconnexion
        self.mt5_interface.disconnect()
        
        print("✅ Bot arrêté proprement")
        logger.log_info("Bot arrêté")

def main():
    """Point d'entrée principal"""
    bot = PairsTradingBot()
    bot.run()

if __name__ == "__main__":
    main()
