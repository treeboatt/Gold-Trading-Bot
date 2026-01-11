"""
Système de logging avancé pour enregistrer tous les événements et données ML
"""

import csv
import os
from datetime import datetime
from typing import Optional, Dict

class TradingLogger:
    """Logger pour enregistrer les événements de trading dans un fichier CSV"""
    
    def __init__(self, log_file: str = "trading_log.csv", backtest_file: str = "backtest_data.csv"):
        self.log_file = log_file
        self.backtest_file = backtest_file
        self._initialize_log_file()
        self._initialize_backtest_file()
    
    def _initialize_log_file(self):
        """Initialise le fichier de log avec les en-têtes si nécessaire"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    'Timestamp',
                    'Type',
                    'Symbole',
                    'Action',
                    'Prix',
                    'Volume',
                    'Stop_Loss',
                    'Take_Profit',
                    'Message',
                    'Balance',
                    'Equity'
                ])
    
    def _initialize_backtest_file(self):
        """Initialise le fichier backtest_data.csv pour ML"""
        if not os.path.exists(self.backtest_file):
            with open(self.backtest_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    'timestamp',
                    'symbol',
                    'action',
                    'entry_price',
                    'exit_price',
                    'volume',
                    'stop_loss',
                    'take_profit',
                    'profit',
                    'profit_pct',
                    'exit_reason',
                    'duration_minutes',
                    # Indicateurs techniques
                    'price',
                    'ema_short',
                    'ema_long',
                    'atr',
                    'atr_pct',
                    'rsi',
                    # Market Intelligence
                    'sp500_price',
                    'sp500_change_1d_pct',
                    'sp500_weak',
                    'vix_value',
                    'vix_high',
                    'gold_btc_corr',
                    'gold_sp500_corr',
                    'correlation_decoupled',
                    # Risk metrics
                    'balance',
                    'equity',
                    'margin_used',
                    'drawdown_pct',
                    # Trading costs
                    'spread_cost',
                    'commission',
                    'total_costs',
                    'net_profit'
                ])
    
    def log(self, 
            event_type: str,
            symbole: Optional[str] = None,
            action: Optional[str] = None,
            prix: Optional[float] = None,
            volume: Optional[float] = None,
            stop_loss: Optional[float] = None,
            take_profit: Optional[float] = None,
            message: str = "",
            balance: Optional[float] = None,
            equity: Optional[float] = None):
        """
        Enregistre un événement dans le fichier de log
        
        Args:
            event_type: Type d'événement (INFO, ORDER, ERROR, SIGNAL, etc.)
            symbole: Symbole tradé (XAUUSD, BTCUSD)
            action: Action effectuée (BUY, SELL, CLOSE, etc.)
            prix: Prix d'exécution
            volume: Volume en lots
            stop_loss: Prix du stop loss
            take_profit: Prix du take profit
            message: Message descriptif
            balance: Balance du compte
            equity: Equity du compte
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                timestamp,
                event_type,
                symbole or "",
                action or "",
                prix or "",
                volume or "",
                stop_loss or "",
                take_profit or "",
                message,
                balance or "",
                equity or ""
            ])
    
    def log_info(self, message: str, balance: Optional[float] = None, equity: Optional[float] = None):
        """Log un message informatif"""
        self.log("INFO", message=message, balance=balance, equity=equity)
    
    def log_error(self, message: str):
        """Log une erreur"""
        self.log("ERROR", message=message)
    
    def log_signal(self, symbole: str, signal: str, prix: float, message: str = ""):
        """Log un signal de trading"""
        self.log("SIGNAL", symbole=symbole, action=signal, prix=prix, message=message)
    
    def log_order(self, 
                  symbole: str,
                  action: str,
                  prix: float,
                  volume: float,
                  stop_loss: Optional[float] = None,
                  take_profit: Optional[float] = None,
                  message: str = ""):
        """Log un ordre exécuté"""
        self.log("ORDER", 
                symbole=symbole,
                action=action,
                prix=prix,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                message=message)
    
    def log_backtest_data(self, trade_data: Dict):
        """
        Enregistre les données complètes d'un trade pour ML
        
        Args:
            trade_data: Dictionnaire avec toutes les données du trade
        """
        timestamp = trade_data.get('timestamp', datetime.now())
        if isinstance(timestamp, datetime):
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.backtest_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                timestamp,
                trade_data.get('symbol', ''),
                trade_data.get('action', ''),
                trade_data.get('entry_price', ''),
                trade_data.get('exit_price', ''),
                trade_data.get('volume', ''),
                trade_data.get('stop_loss', ''),
                trade_data.get('take_profit', ''),
                trade_data.get('profit', ''),
                trade_data.get('profit_pct', ''),
                trade_data.get('exit_reason', ''),
                trade_data.get('duration_minutes', ''),
                # Indicateurs techniques
                trade_data.get('price', ''),
                trade_data.get('ema_short', ''),
                trade_data.get('ema_long', ''),
                trade_data.get('atr', ''),
                trade_data.get('atr_pct', ''),
                trade_data.get('rsi', ''),
                # Market Intelligence
                trade_data.get('sp500_price', ''),
                trade_data.get('sp500_change_1d_pct', ''),
                trade_data.get('sp500_weak', ''),
                trade_data.get('vix_value', ''),
                trade_data.get('vix_high', ''),
                trade_data.get('gold_btc_corr', ''),
                trade_data.get('gold_sp500_corr', ''),
                trade_data.get('correlation_decoupled', ''),
                # Risk metrics
                trade_data.get('balance', ''),
                trade_data.get('equity', ''),
                trade_data.get('margin_used', ''),
                trade_data.get('drawdown_pct', ''),
                # Trading costs
                trade_data.get('spread_cost', ''),
                trade_data.get('commission', ''),
                trade_data.get('total_costs', ''),
                trade_data.get('net_profit', '')
            ])
