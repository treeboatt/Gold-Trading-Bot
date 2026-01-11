"""
Interface MetaTrader 5
Gère la connexion à MT5 et l'exécution des ordres
"""

import MetaTrader5 as mt5
import pandas as pd
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
import time

try:
    from .config import (
        MT5_LOGIN, MT5_PASSWORD, MT5_SERVER,
        SYMBOL_GOLD, SYMBOL_BTC,
        MAGIC_NUMBER, DEVIATION, TIMEOUT
    )
    from .logger import TradingLogger
except ImportError:
    from config import (
        MT5_LOGIN, MT5_PASSWORD, MT5_SERVER,
        SYMBOL_GOLD, SYMBOL_BTC,
        MAGIC_NUMBER, DEVIATION, TIMEOUT
    )
    from logger import TradingLogger

logger = TradingLogger()

class MT5Interface:
    """Interface pour interagir avec MetaTrader 5"""
    
    def __init__(self):
        self.connected = False
    
    def connect(self) -> bool:
        """
        Se connecte à MetaTrader 5
        
        Returns:
            True si la connexion réussit, False sinon
        """
        if not mt5.initialize():
            error = mt5.last_error()
            logger.log_error(f"Échec d'initialisation MT5: {error}")
            return False
        
        # Tentative de connexion au compte
        if MT5_LOGIN and MT5_PASSWORD:
            authorized = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
            if not authorized:
                error = mt5.last_error()
                logger.log_error(f"Échec de connexion au compte MT5: {error}")
                mt5.shutdown()
                return False
            logger.log_info(f"Connecté au compte MT5: {MT5_LOGIN}")
        else:
            logger.log_info("Connexion MT5 en mode démo (pas d'identifiants configurés)")
        
        self.connected = True
        account_info = mt5.account_info()
        if account_info:
            logger.log_info(
                f"Compte: {account_info.login}, Balance: {account_info.balance}, "
                f"Equity: {account_info.equity}",
                balance=account_info.balance,
                equity=account_info.equity
            )
        return True
    
    def disconnect(self):
        """Déconnecte de MetaTrader 5"""
        mt5.shutdown()
        self.connected = False
        logger.log_info("Déconnecté de MT5")
    
    def get_symbol_info(self, symbol: str) -> Optional[mt5.SymbolInfo]:
        """
        Récupère les informations d'un symbole
        
        Args:
            symbol: Symbole à récupérer (ex: "XAUUSD")
        
        Returns:
            SymbolInfo ou None si erreur
        """
        if not self.connected:
            logger.log_error("Non connecté à MT5")
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.log_error(f"Symbole {symbol} non trouvé")
            return None
        
        # S'assurer que le symbole est visible dans Market Watch
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.log_error(f"Impossible d'activer le symbole {symbol}")
                return None
        
        return symbol_info
    
    def get_rates(self, symbol: str, timeframe: int, count: int = 100) -> Optional[pd.DataFrame]:
        """
        Récupère les données de prix historiques
        
        Args:
            symbol: Symbole à récupérer
            timeframe: Timeframe MT5 (mt5.TIMEFRAME_M15, etc.)
            count: Nombre de barres à récupérer
        
        Returns:
            DataFrame avec les données OHLCV ou None si erreur
        """
        if not self.connected:
            logger.log_error("Non connecté à MT5")
            return None
        
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.log_error(f"Impossible de récupérer les données pour {symbol}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    def get_current_price(self, symbol: str) -> Optional[Tuple[float, float]]:
        """
        Récupère le prix actuel (bid et ask)
        
        Args:
            symbol: Symbole à récupérer
        
        Returns:
            Tuple (bid, ask) ou None si erreur
        """
        if not self.connected:
            return None
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        return (tick.bid, tick.ask)
    
    def calculate_lot_size(self, symbol: str, risk_percent: float, stop_loss_pips: float) -> float:
        """
        Calcule la taille de position en lots basée sur le risque
        
        Args:
            symbol: Symbole à trader
            risk_percent: Pourcentage de risque (ex: 0.01 pour 1%)
            stop_loss_pips: Distance du stop loss en pips
        
        Returns:
            Taille de position en lots
        """
        if not self.connected:
            return 0.0
        
        account_info = mt5.account_info()
        if account_info is None:
            return 0.0
        
        balance = account_info.balance
        risk_amount = balance * risk_percent
        
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info is None:
            return 0.0
        
        # Calculer la valeur d'un pip
        tick_size = symbol_info.trade_tick_size
        tick_value = symbol_info.trade_tick_value
        contract_size = symbol_info.trade_contract_size
        
        # Pour XAUUSD, 1 lot = 100 onces, 1 pip = 0.01
        # Pour BTCUSD, cela dépend du broker
        pip_value = (tick_value / tick_size) * contract_size
        
        # Calculer le nombre de lots
        if stop_loss_pips > 0:
            lot_size = risk_amount / (stop_loss_pips * pip_value)
        else:
            lot_size = 0.0
        
        # Normaliser selon les contraintes du broker
        min_lot = symbol_info.volume_min
        max_lot = symbol_info.volume_max
        lot_step = symbol_info.volume_step
        
        lot_size = max(min_lot, min(max_lot, lot_size))
        lot_size = round(lot_size / lot_step) * lot_step
        
        return lot_size
    
    def place_order(self,
                   symbol: str,
                   order_type: int,
                   volume: float,
                   price: Optional[float] = None,
                   sl: Optional[float] = None,
                   tp: Optional[float] = None,
                   comment: str = "Bot Gold/BTC") -> Optional[int]:
        """
        Place un ordre sur MT5
        
        Args:
            symbol: Symbole à trader
            order_type: Type d'ordre (mt5.ORDER_TYPE_BUY ou mt5.ORDER_TYPE_SELL)
            volume: Volume en lots
            price: Prix d'entrée (None pour ordre au marché)
            sl: Stop Loss
            tp: Take Profit
            comment: Commentaire de l'ordre
        
        Returns:
            Ticket de l'ordre ou None si erreur
        """
        if not self.connected:
            logger.log_error("Non connecté à MT5")
            return None
        
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info is None:
            return None
        
        # Récupérer le prix actuel si non spécifié
        if price is None:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.log_error(f"Impossible de récupérer le prix pour {symbol}")
                return None
            if order_type == mt5.ORDER_TYPE_BUY:
                price = tick.ask
            else:
                price = tick.bid
        
        # Préparer la requête
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": DEVIATION,
            "magic": MAGIC_NUMBER,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp
        
        # Envoyer l'ordre
        result = mt5.order_send(request)
        
        if result is None:
            error = mt5.last_error()
            logger.log_error(f"Erreur lors de l'envoi de l'ordre: {error}")
            return None
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.log_error(
                f"Ordre rejeté: {result.retcode} - {result.comment}",
                symbole=symbol,
                action="REJECTED"
            )
            return None
        
        # Log de l'ordre réussi
        action_str = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        logger.log_order(
            symbole=symbol,
            action=action_str,
            prix=result.price,
            volume=volume,
            stop_loss=sl,
            take_profit=tp,
            message=f"Ordre exécuté: Ticket {result.order}"
        )
        
        return result.order
    
    def get_open_positions(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Récupère les positions ouvertes
        
        Args:
            symbol: Filtrer par symbole (None pour tous)
        
        Returns:
            DataFrame avec les positions ouvertes
        """
        if not self.connected:
            return pd.DataFrame()
        
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None or len(positions) == 0:
            return pd.DataFrame()
        
        # Convertir en DataFrame
        positions_dict = []
        for pos in positions:
            positions_dict.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': pos.type,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'comment': pos.comment
            })
        
        return pd.DataFrame(positions_dict)
    
    def close_position(self, ticket: int) -> bool:
        """
        Ferme une position
        
        Args:
            ticket: Ticket de la position à fermer
        
        Returns:
            True si succès, False sinon
        """
        if not self.connected:
            return False
        
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            logger.log_error(f"Position {ticket} non trouvée")
            return False
        
        pos = position[0]
        
        # Déterminer le type d'ordre opposé
        if pos.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(pos.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(pos.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": DEVIATION,
            "magic": MAGIC_NUMBER,
            "comment": "Fermeture position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.log_order(
                symbole=pos.symbol,
                action="CLOSE",
                prix=result.price,
                volume=pos.volume,
                message=f"Position {ticket} fermée"
            )
            return True
        else:
            error = mt5.last_error()
            logger.log_error(f"Erreur lors de la fermeture de la position {ticket}: {error}")
            return False
