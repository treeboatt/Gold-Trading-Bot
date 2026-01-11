"""
Gestionnaire de risque haute précision
Position sizing dynamique, Trailing Stop, Circuit Breaker
"""

import pandas as pd
from typing import Optional, Dict, Tuple
from datetime import datetime, date
import MetaTrader5 as mt5

try:
    from .config import (
        RISK_PERCENT_MIN, RISK_PERCENT_MAX, RISK_PERCENT_DEFAULT,
        CIRCUIT_BREAKER_PAIR_LOSS, MAX_LEVERAGE,
        SPREAD_GOLD_POINTS, COMMISSION_PER_LOT
    )
    from .mt5_interface import MT5Interface
    from .logger import TradingLogger
except ImportError:
    from config import (
        RISK_PERCENT_MIN, RISK_PERCENT_MAX, RISK_PERCENT_DEFAULT,
        CIRCUIT_BREAKER_PAIR_LOSS, MAX_LEVERAGE,
        SPREAD_GOLD_POINTS, COMMISSION_PER_LOT
    )
    from mt5_interface import MT5Interface
    from logger import TradingLogger

logger = TradingLogger()

class RiskManager:
    """Gestionnaire de risque professionnel"""
    
    def __init__(self, mt5_interface: MT5Interface):
        self.mt5 = mt5_interface
        self.daily_pnl = {}  # P&L journalier par date
        self.initial_balance = None
        self.trailing_stops = {}  # {ticket: {'highest_price': float, 'lowest_price': float}}
        self._initialize_daily_tracking()
    
    def _initialize_daily_tracking(self):
        """Initialise le suivi journalier"""
        account_info = mt5.account_info()
        if account_info:
            self.initial_balance = account_info.balance
            today = date.today().isoformat()
            self.daily_pnl[today] = 0.0
    
    def calculate_adaptive_risk_percent(self,
                                       z_score: float,
                                       volatility: Optional[float] = None) -> float:
        """
        Calcule le pourcentage de risque adaptatif (0.5% à 1%)
        Plus le Z-Score est élevé et la volatilité faible, plus on peut risquer
        
        Args:
            z_score: Z-Score actuel (plus élevé = opportunité plus sûre)
            volatility: Volatilité (ATR en pourcentage, optionnel)
        
        Returns:
            Pourcentage de risque entre RISK_PERCENT_MIN et RISK_PERCENT_MAX
        """
        # Base: risque par défaut
        risk_pct = RISK_PERCENT_DEFAULT
        
        # Ajuster selon le Z-Score (plus élevé = opportunité plus sûre)
        # Z-Score > 2.5 = opportunité très claire, on peut risquer plus
        if abs(z_score) > 2.5:
            risk_pct = RISK_PERCENT_MAX  # 1%
        elif abs(z_score) > 2.0:
            risk_pct = (RISK_PERCENT_MIN + RISK_PERCENT_MAX) / 2  # 0.75%
        else:
            risk_pct = RISK_PERCENT_MIN  # 0.5%
        
        # Ajuster selon la volatilité si disponible
        if volatility is not None:
            # Volatilité faible = marché stable = on peut risquer plus
            if volatility < 0.001:  # Très faible volatilité
                risk_pct = min(risk_pct * 1.2, RISK_PERCENT_MAX)
            elif volatility > 0.005:  # Volatilité élevée
                risk_pct = max(risk_pct * 0.8, RISK_PERCENT_MIN)
        
        # S'assurer que c'est dans les limites
        risk_pct = max(RISK_PERCENT_MIN, min(RISK_PERCENT_MAX, risk_pct))
        
        return risk_pct
    
    def calculate_dynamic_position_size(self,
                                      symbol: str,
                                      entry_price: float,
                                      stop_loss_price: float,
                                      account_balance: Optional[float] = None,
                                      risk_percent: Optional[float] = None,
                                      z_score: Optional[float] = None,
                                      volatility: Optional[float] = None) -> Tuple[float, float]:
        """
        Calcule la taille de position avec risque adaptatif (0.5% à 1%)
        
        Args:
            symbol: Symbole à trader
            entry_price: Prix d'entrée
            stop_loss_price: Prix du stop loss
            account_balance: Balance du compte (None = récupérer automatiquement)
            risk_percent: Pourcentage de risque (None = calcul adaptatif)
            z_score: Z-Score pour ajustement adaptatif
            volatility: Volatilité pour ajustement adaptatif
        
        Returns:
            Tuple (volume_en_lots, risk_percent_used)
        """
        if account_balance is None:
            account_info = mt5.account_info()
            if account_info is None:
                return 0.0, 0.0
            account_balance = account_info.balance
        
        # Calculer le risque adaptatif si non fourni
        if risk_percent is None:
            if z_score is not None:
                risk_percent = self.calculate_adaptive_risk_percent(z_score, volatility)
            else:
                risk_percent = RISK_PERCENT_DEFAULT
        
        # Montant à risquer
        risk_amount = account_balance * risk_percent
        
        # Distance du stop loss en points
        stop_distance = abs(entry_price - stop_loss_price)
        
        if stop_distance == 0:
            logger.log_error("Stop loss = Prix d'entrée, impossible de calculer la position")
            return 0.0
        
        # Récupérer les infos du symbole
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            return 0.0
        
        # Calculer la valeur d'un point
        point = symbol_info.point
        tick_size = symbol_info.trade_tick_size
        tick_value = symbol_info.trade_tick_value
        contract_size = symbol_info.trade_contract_size
        
        # Valeur d'un point par lot
        # Pour XAUUSD: 1 lot = 100 onces, 1 point = 0.01, valeur = 0.01 * 100 = 1$ par point
        point_value = (tick_value / tick_size) * contract_size
        
        # Calculer le nombre de lots
        lots = risk_amount / (stop_distance / point * point_value)
        
        # Normaliser selon les contraintes du broker
        min_lot = symbol_info.volume_min
        max_lot = symbol_info.volume_max
        lot_step = symbol_info.volume_step
        
        lots = max(min_lot, min(max_lot, lots))
        lots = round(lots / lot_step) * lot_step
        
        logger.log_info(
            f"Position sizing: Balance={account_balance:.2f}, Risk={risk_percent*100:.2f}% ({risk_amount:.2f}), "
            f"Stop={stop_distance:.2f}, Lots={lots:.2f}"
        )
        
        return lots, risk_percent
    
    def calculate_trading_costs(self,
                               symbol: str,
                               volume: float,
                               entry_price: float,
                               is_buy: bool = True) -> Dict[str, float]:
        """
        Calcule les coûts de trading (spread + commission)
        
        Args:
            symbol: Symbole tradé
            volume: Volume en lots
            entry_price: Prix d'entrée
            is_buy: True pour achat, False pour vente
        
        Returns:
            Dictionnaire avec les coûts détaillés
        """
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            return {'spread_cost': 0.0, 'commission': 0.0, 'total_cost': 0.0}
        
        # Récupérer le spread actuel
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            spread_points = (tick.ask - tick.bid) / symbol_info.point
        else:
            # Utiliser les valeurs par défaut du config
            spread_points = SPREAD_GOLD_POINTS if symbol == "XAUUSD" else 50
        
        # Coût du spread
        point_value = (symbol_info.trade_tick_value / symbol_info.trade_tick_size) * symbol_info.trade_contract_size
        spread_cost = spread_points * point_value * volume
        
        # Commission
        commission = COMMISSION_PER_LOT * volume
        
        total_cost = spread_cost + commission
        
        return {
            'spread_cost': spread_cost,
            'commission': commission,
            'total_cost': total_cost,
            'spread_points': spread_points
        }
    
    def update_trailing_stop(self, ticket: int, current_price: float, atr: float) -> Optional[float]:
        """
        Met à jour le trailing stop pour une position
        
        Args:
            ticket: Ticket de la position
            current_price: Prix actuel du marché
            atr: Valeur actuelle de l'ATR
        
        Returns:
            Nouveau prix de stop loss ou None si pas de changement
        """
        # Récupérer la position
        positions = self.mt5.get_open_positions(ticket=ticket)
        if positions.empty:
            return None
        
        pos = positions.iloc[0]
        
        # Initialiser le trailing stop si nécessaire
        if ticket not in self.trailing_stops:
            if pos['type'] == 0:  # BUY
                self.trailing_stops[ticket] = {'highest_price': pos['price_open']}
            else:  # SELL
                self.trailing_stops[ticket] = {'lowest_price': pos['price_open']}
        
        trailing_data = self.trailing_stops[ticket]
        
        # Calculer le nouveau stop loss
        if pos['type'] == 0:  # Position LONG
            # Mettre à jour le plus haut prix atteint
            if current_price > trailing_data.get('highest_price', pos['price_open']):
                trailing_data['highest_price'] = current_price
            
            # Calculer le nouveau stop loss (2x ATR sous le plus haut)
            new_sl = trailing_data['highest_price'] - (atr * ATR_MULTIPLIER_TRAILING)
            
            # Ne mettre à jour que si le nouveau SL est plus haut que l'ancien
            if new_sl > pos['sl']:
                return new_sl
        
        else:  # Position SHORT
            # Mettre à jour le plus bas prix atteint
            if current_price < trailing_data.get('lowest_price', pos['price_open']):
                trailing_data['lowest_price'] = current_price
            
            # Calculer le nouveau stop loss (2x ATR au-dessus du plus bas)
            new_sl = trailing_data['lowest_price'] + (atr * ATR_MULTIPLIER_TRAILING)
            
            # Ne mettre à jour que si le nouveau SL est plus bas que l'ancien
            if new_sl < pos['sl'] or pos['sl'] == 0:
                return new_sl
        
        return None
    
    def check_circuit_breaker_pair(self) -> Tuple[bool, str]:
        """
        Vérifie si le circuit breaker doit être activé (2% de perte latente sur la paire)
        
        Returns:
            Tuple (should_stop, reason)
        """
        account_info = mt5.account_info()
        if account_info is None:
            return False, "Impossible de récupérer les infos du compte"
        
        # Récupérer les positions de la paire
        gold_positions = self.mt5.get_open_positions(symbol="XAUUSD")
        btc_positions = self.mt5.get_open_positions(symbol="BTCUSD")
        
        # Calculer le P&L total de la paire
        pair_pnl = 0.0
        if not gold_positions.empty:
            pair_pnl += gold_positions['profit'].sum()
        if not btc_positions.empty:
            pair_pnl += btc_positions['profit'].sum()
        
        # Calculer la perte en pourcentage de la balance
        if self.initial_balance and self.initial_balance > 0:
            loss_pct = abs(pair_pnl) / self.initial_balance if pair_pnl < 0 else 0.0
            
            if loss_pct >= CIRCUIT_BREAKER_PAIR_LOSS:
                reason = f"Circuit breaker PAIR activé: Perte latente de {loss_pct*100:.2f}% ({pair_pnl:.2f})"
                logger.log_error(reason)
                return True, reason
        
        return False, f"P&L paire: {pair_pnl:.2f}"
    
    def check_leverage_limit(self) -> Tuple[bool, str]:
        """
        Vérifie si le levier dépasse la limite (1:3)
        
        Returns:
            Tuple (exceeds_limit, reason)
        """
        account_info = mt5.account_info()
        if account_info is None:
            return True, "Impossible de récupérer les infos du compte"
        
        # Récupérer le levier actuel
        current_leverage = account_info.leverage
        
        if current_leverage > MAX_LEVERAGE:
            reason = f"Levier {current_leverage}:1 dépasse la limite {MAX_LEVERAGE}:1"
            logger.log_error(reason)
            return True, reason
        
        return False, f"Levier OK: {current_leverage}:1"
    
    
    def calculate_net_profit_after_costs(self,
                                        entry_price: float,
                                        exit_price: float,
                                        volume: float,
                                        symbol: str,
                                        is_buy: bool = True) -> Dict[str, float]:
        """
        Calcule le profit net après déduction des coûts (spread + commission)
        
        Args:
            entry_price: Prix d'entrée
            exit_price: Prix de sortie
            volume: Volume en lots
            symbol: Symbole tradé
            is_buy: True pour achat, False pour vente
        
        Returns:
            Dictionnaire avec profit brut, coûts et profit net
        """
        # Coûts à l'entrée
        entry_costs = self.calculate_trading_costs(symbol, volume, entry_price, is_buy)
        
        # Coûts à la sortie
        exit_costs = self.calculate_trading_costs(symbol, volume, exit_price, not is_buy)
        
        # Profit brut
        if is_buy:
            gross_profit = (exit_price - entry_price) * volume * 100  # Pour XAUUSD: 1 lot = 100 onces
        else:
            gross_profit = (entry_price - exit_price) * volume * 100
        
        # Profit net
        total_costs = entry_costs['total_cost'] + exit_costs['total_cost']
        net_profit = gross_profit - total_costs
        
        return {
            'gross_profit': gross_profit,
            'entry_costs': entry_costs['total_cost'],
            'exit_costs': exit_costs['total_cost'],
            'total_costs': total_costs,
            'net_profit': net_profit,
            'cost_percentage': (total_costs / abs(gross_profit) * 100) if gross_profit != 0 else 0
        }
    
    def should_allow_trade(self) -> Tuple[bool, str]:
        """
        Vérifie si le trading est autorisé (circuit breaker paire, levier)
        
        Returns:
            Tuple (allowed, reason)
        """
        # Vérifier le circuit breaker sur la paire
        circuit_breaker, reason_cb = self.check_circuit_breaker_pair()
        if circuit_breaker:
            return False, reason_cb
        
        # Vérifier le levier
        leverage_exceeded, reason_lev = self.check_leverage_limit()
        if leverage_exceeded:
            return False, reason_lev
        
        return True, "Trading autorisé"
    
    def get_risk_metrics(self) -> Dict[str, float]:
        """
        Récupère les métriques de risque actuelles
        
        Returns:
            Dictionnaire avec les métriques
        """
        account_info = mt5.account_info()
        if account_info is None:
            return {}
        
        positions = self.mt5.get_open_positions()
        open_pnl = positions['profit'].sum() if not positions.empty else 0.0
        
        equity = account_info.equity
        balance = account_info.balance
        margin_used = account_info.margin
        margin_free = account_info.margin_free
        
        drawdown = 0.0
        if self.initial_balance and self.initial_balance > 0:
            drawdown = (self.initial_balance - equity) / self.initial_balance
        
        return {
            'balance': balance,
            'equity': equity,
            'open_pnl': open_pnl,
            'margin_used': margin_used,
            'margin_free': margin_free,
            'drawdown_pct': drawdown * 100,
            'open_positions': len(positions)
        }
