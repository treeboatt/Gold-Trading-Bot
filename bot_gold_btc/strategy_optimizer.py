"""
Optimiseur de stratégie pour future optimisation ML (XGBoost/LSTM)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

try:
    from .logger import TradingLogger
except ImportError:
    from logger import TradingLogger

logger = TradingLogger()

class StrategyOptimizer:
    """Classe pour optimiser la stratégie et préparer les données pour ML"""
    
    def __init__(self):
        self.trade_history = []
        self.performance_metrics = {}
    
    def record_trade_entry(self,
                          symbol: str,
                          action: str,
                          entry_price: float,
                          volume: float,
                          stop_loss: float,
                          take_profit: float,
                          indicators: Dict[str, float],
                          market_data: Dict[str, any]):
        """
        Enregistre l'entrée d'un trade avec tous les indicateurs
        
        Args:
            symbol: Symbole tradé
            action: BUY ou SELL
            entry_price: Prix d'entrée
            volume: Volume en lots
            stop_loss: Prix stop loss
            take_profit: Prix take profit
            indicators: Dictionnaire avec tous les indicateurs techniques
            market_data: Données de marché (SP500, VIX, corrélations)
        """
        trade_record = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'action': action,
            'entry_price': entry_price,
            'volume': volume,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            **indicators,
            **market_data,
            'exit_price': None,
            'exit_reason': None,
            'profit': None,
            'profit_pct': None,
            'duration_minutes': None
        }
        
        self.trade_history.append(trade_record)
    
    def record_trade_exit(self,
                         symbol: str,
                         exit_price: float,
                         exit_reason: str,
                         profit: float,
                         entry_timestamp: datetime):
        """
        Enregistre la sortie d'un trade
        
        Args:
            symbol: Symbole tradé
            exit_price: Prix de sortie
            exit_reason: Raison de la sortie (SL, TP, Trailing, etc.)
            profit: Profit réalisé
            entry_timestamp: Timestamp d'entrée pour calculer la durée
        """
        # Trouver le dernier trade ouvert pour ce symbole
        for trade in reversed(self.trade_history):
            if trade['symbol'] == symbol and trade['exit_price'] is None:
                trade['exit_price'] = exit_price
                trade['exit_reason'] = exit_reason
                trade['profit'] = profit
                
                # Calculer le profit en pourcentage
                if trade['entry_price'] > 0:
                    if trade['action'] == 'BUY':
                        trade['profit_pct'] = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
                    else:  # SELL
                        trade['profit_pct'] = ((trade['entry_price'] - exit_price) / trade['entry_price']) * 100
                
                # Calculer la durée
                if entry_timestamp:
                    duration = (datetime.now() - entry_timestamp).total_seconds() / 60
                    trade['duration_minutes'] = duration
                
                break
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """
        Calcule les métriques de performance pour l'optimisation
        
        Returns:
            Dictionnaire avec les métriques
        """
        if not self.trade_history:
            return {}
        
        completed_trades = [t for t in self.trade_history if t['exit_price'] is not None]
        
        if not completed_trades:
            return {}
        
        profits = [t['profit'] for t in completed_trades]
        profits_pct = [t['profit_pct'] for t in completed_trades if t['profit_pct'] is not None]
        
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]
        
        total_profit = sum(profits)
        win_rate = len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0
        
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        profit_factor = abs(sum(winning_trades) / sum(losing_trades)) if losing_trades and sum(losing_trades) != 0 else 0
        
        # Sharpe ratio simplifié
        if profits_pct:
            returns_std = np.std(profits_pct)
            sharpe_ratio = np.mean(profits_pct) / returns_std if returns_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        cumulative = np.cumsum(profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        self.performance_metrics = {
            'total_trades': len(completed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'total_profit': total_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_profit_pct': np.mean(profits_pct) if profits_pct else 0
        }
        
        return self.performance_metrics
    
    def export_to_csv(self, filename: str = "backtest_data.csv"):
        """
        Exporte les données de trading vers CSV pour ML
        
        Args:
            filename: Nom du fichier CSV
        """
        if not self.trade_history:
            logger.log_info("Aucune donnée à exporter")
            return
        
        df = pd.DataFrame(self.trade_history)
        df.to_csv(filename, index=False, sep=';')
        logger.log_info(f"Données exportées vers {filename}: {len(df)} trades")
    
    def analyze_signal_quality(self) -> Dict[str, any]:
        """
        Analyse la qualité des signaux pour identifier les patterns gagnants/perdants
        
        Returns:
            Dictionnaire avec l'analyse
        """
        completed_trades = [t for t in self.trade_history if t['exit_price'] is not None]
        
        if not completed_trades:
            return {}
        
        winning = [t for t in completed_trades if t['profit'] and t['profit'] > 0]
        losing = [t for t in completed_trades if t['profit'] and t['profit'] < 0]
        
        analysis = {
            'winning_patterns': {},
            'losing_patterns': {},
            'recommendations': []
        }
        
        # Analyser les indicateurs des trades gagnants
        if winning:
            avg_rsi_win = np.mean([t.get('rsi', 50) for t in winning if 'rsi' in t])
            avg_atr_pct_win = np.mean([t.get('atr_pct', 0) for t in winning if 'atr_pct' in t])
            
            analysis['winning_patterns'] = {
                'avg_rsi': avg_rsi_win,
                'avg_atr_pct': avg_atr_pct_win
            }
        
        # Analyser les indicateurs des trades perdants
        if losing:
            avg_rsi_loss = np.mean([t.get('rsi', 50) for t in losing if 'rsi' in t])
            avg_atr_pct_loss = np.mean([t.get('atr_pct', 0) for t in losing if 'atr_pct' in t])
            
            analysis['losing_patterns'] = {
                'avg_rsi': avg_rsi_loss,
                'avg_atr_pct': avg_atr_pct_loss
            }
        
        # Recommandations
        if winning and losing:
            if 'winning_patterns' in analysis and 'losing_patterns' in analysis:
                if analysis['winning_patterns'].get('avg_rsi', 50) < analysis['losing_patterns'].get('avg_rsi', 50):
                    analysis['recommendations'].append("Éviter les trades avec RSI trop élevé")
        
        return analysis
