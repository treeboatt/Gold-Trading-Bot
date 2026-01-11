"""
Système de tracking de performance ultra-détaillé
Enregistre Profit, Drawdown, Sharpe Ratio pour chaque session
Format JSON et CSV pour analyse et preuve de performance SaaS
"""

import json
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

try:
    from .config import (
        PERFORMANCE_LOG_FILE, PERFORMANCE_LOG_CSV,
        SESSION_LOG_DIR, ENABLE_DETAILED_LOGGING
    )
    from .logger import TradingLogger
except ImportError:
    from config import (
        PERFORMANCE_LOG_FILE, PERFORMANCE_LOG_CSV,
        SESSION_LOG_DIR, ENABLE_DETAILED_LOGGING
    )
    from logger import TradingLogger

logger = TradingLogger()

class PerformanceTracker:
    """Tracker de performance institutionnel pour preuve SaaS"""
    
    def __init__(self):
        self.session_id = None
        self.session_start_time = None
        self.session_data = {
            'session_id': None,
            'start_time': None,
            'end_time': None,
            'initial_balance': 0.0,
            'final_balance': 0.0,
            'initial_equity': 0.0,
            'final_equity': 0.0,
            'trades': [],
            'metrics': {}
        }
        self.equity_history = []  # Historique de l'equity pour calcul drawdown
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Crée les dossiers nécessaires"""
        if not os.path.exists(SESSION_LOG_DIR):
            os.makedirs(SESSION_LOG_DIR)
    
    def start_session(self, initial_balance: float, initial_equity: float):
        """
        Démarre une nouvelle session de trading
        
        Args:
            initial_balance: Balance initiale du compte
            initial_equity: Equity initiale du compte
        """
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_start_time = datetime.now()
        
        self.session_data = {
            'session_id': self.session_id,
            'start_time': self.session_start_time.isoformat(),
            'end_time': None,
            'initial_balance': initial_balance,
            'final_balance': initial_balance,
            'initial_equity': initial_equity,
            'final_equity': initial_equity,
            'trades': [],
            'metrics': {}
        }
        
        self.equity_history = [(self.session_start_time, initial_equity)]
        
        logger.log_info(f"Session démarrée: {self.session_id}")
    
    def record_trade(self,
                    trade_id: str,
                    symbol: str,
                    action: str,
                    entry_price: float,
                    exit_price: Optional[float],
                    volume: float,
                    profit: Optional[float],
                    entry_time: datetime,
                    exit_time: Optional[datetime] = None,
                    z_score: Optional[float] = None,
                    spread_cost: Optional[float] = None):
        """
        Enregistre un trade dans la session
        
        Args:
            trade_id: Identifiant unique du trade
            symbol: Symbole tradé
            action: Action (BUY/SELL)
            entry_price: Prix d'entrée
            exit_price: Prix de sortie (None si encore ouvert)
            volume: Volume en lots
            profit: Profit réalisé (None si encore ouvert)
            entry_time: Timestamp d'entrée
            exit_time: Timestamp de sortie
            z_score: Z-Score au moment de l'entrée
            spread_cost: Coût du spread
        """
        if not ENABLE_DETAILED_LOGGING:
            return
        
        trade_record = {
            'trade_id': trade_id,
            'symbol': symbol,
            'action': action,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'volume': volume,
            'profit': profit,
            'profit_pct': None,
            'entry_time': entry_time.isoformat() if isinstance(entry_time, datetime) else entry_time,
            'exit_time': exit_time.isoformat() if exit_time and isinstance(exit_time, datetime) else exit_time,
            'duration_seconds': None,
            'z_score': z_score,
            'spread_cost': spread_cost,
            'net_profit': None
        }
        
        # Calculer le profit en pourcentage
        if profit is not None and entry_price > 0:
            if action == 'BUY':
                trade_record['profit_pct'] = ((exit_price - entry_price) / entry_price) * 100 if exit_price else None
            else:  # SELL
                trade_record['profit_pct'] = ((entry_price - exit_price) / entry_price) * 100 if exit_price else None
        
        # Calculer la durée
        if exit_time:
            duration = (exit_time - entry_time).total_seconds() if isinstance(exit_time, datetime) else None
            trade_record['duration_seconds'] = duration
        
        # Profit net (après coûts)
        if profit is not None and spread_cost is not None:
            trade_record['net_profit'] = profit - spread_cost
        
        self.session_data['trades'].append(trade_record)
    
    def update_equity(self, equity: float):
        """
        Met à jour l'historique de l'equity pour calcul du drawdown
        
        Args:
            equity: Equity actuelle
        """
        self.equity_history.append((datetime.now(), equity))
        self.session_data['final_equity'] = equity
    
    def calculate_metrics(self) -> Dict:
        """
        Calcule toutes les métriques de performance de la session
        
        Returns:
            Dictionnaire avec toutes les métriques
        """
        completed_trades = [t for t in self.session_data['trades'] if t['profit'] is not None]
        
        if not completed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'total_net_profit': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'return_pct': 0.0,
                'monthly_return_pct': 0.0
            }
        
        # Métriques de base
        total_trades = len(completed_trades)
        profits = [t['profit'] for t in completed_trades]
        net_profits = [t.get('net_profit', t['profit']) for t in completed_trades]
        
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]
        
        total_profit = sum(profits)
        total_net_profit = sum(net_profits)
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
        
        avg_win = np.mean(winning_trades) if winning_trades else 0.0
        avg_loss = np.mean(losing_trades) if losing_trades else 0.0
        
        profit_factor = abs(sum(winning_trades) / sum(losing_trades)) if losing_trades and sum(losing_trades) != 0 else 0.0
        
        # Sharpe Ratio
        if len(profits) > 1:
            returns = [p / self.session_data['initial_equity'] for p in profits]
            returns_std = np.std(returns)
            sharpe_ratio = (np.mean(returns) / returns_std * np.sqrt(252)) if returns_std > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Drawdown
        max_drawdown, max_drawdown_pct = self._calculate_drawdown()
        
        # Rendement
        initial_equity = self.session_data['initial_equity']
        final_equity = self.session_data['final_equity']
        return_pct = ((final_equity - initial_equity) / initial_equity * 100) if initial_equity > 0 else 0.0
        
        # Rendement mensuel estimé (basé sur la durée de la session)
        session_duration = datetime.now() - self.session_start_time
        days_in_session = session_duration.total_seconds() / 86400
        monthly_return_pct = (return_pct / days_in_session * 30) if days_in_session > 0 else 0.0
        
        metrics = {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'total_net_profit': round(total_net_profit, 2),
            'avg_profit': round(np.mean(profits), 2) if profits else 0.0,
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'return_pct': round(return_pct, 2),
            'monthly_return_pct': round(monthly_return_pct, 2),
            'session_duration_hours': round(days_in_session * 24, 2)
        }
        
        self.session_data['metrics'] = metrics
        return metrics
    
    def _calculate_drawdown(self) -> tuple:
        """
        Calcule le drawdown maximum
        
        Returns:
            Tuple (max_drawdown, max_drawdown_pct)
        """
        if len(self.equity_history) < 2:
            return 0.0, 0.0
        
        equity_values = [e[1] for e in self.equity_history]
        peak = equity_values[0]
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0.0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        return max_drawdown, max_drawdown_pct
    
    def end_session(self, final_balance: float, final_equity: float):
        """
        Termine la session et sauvegarde les données
        
        Args:
            final_balance: Balance finale
            final_equity: Equity finale
        """
        self.session_data['end_time'] = datetime.now().isoformat()
        self.session_data['final_balance'] = final_balance
        self.session_data['final_equity'] = final_equity
        
        # Calculer les métriques finales
        metrics = self.calculate_metrics()
        
        # Sauvegarder en JSON
        self._save_json()
        
        # Sauvegarder en CSV
        self._save_csv()
        
        logger.log_info(f"Session terminée: {self.session_id} - Profit: {metrics['total_net_profit']:.2f}, Sharpe: {metrics['sharpe_ratio']:.2f}")
    
    def _save_json(self):
        """Sauvegarde les données de session en JSON"""
        session_file = os.path.join(SESSION_LOG_DIR, f"{self.session_id}.json")
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)
        
        # Ajouter à la liste globale des sessions
        self._append_to_global_json()
    
    def _append_to_global_json(self):
        """Ajoute cette session au fichier JSON global"""
        if os.path.exists(PERFORMANCE_LOG_FILE):
            with open(PERFORMANCE_LOG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'sessions': []}
        
        # Ajouter seulement les métriques résumées
        session_summary = {
            'session_id': self.session_data['session_id'],
            'start_time': self.session_data['start_time'],
            'end_time': self.session_data['end_time'],
            'metrics': self.session_data['metrics']
        }
        
        data['sessions'].append(session_summary)
        
        # Garder seulement les 100 dernières sessions
        if len(data['sessions']) > 100:
            data['sessions'] = data['sessions'][-100:]
        
        with open(PERFORMANCE_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_csv(self):
        """Sauvegarde les métriques en CSV pour analyse"""
        file_exists = os.path.exists(PERFORMANCE_LOG_CSV)
        
        with open(PERFORMANCE_LOG_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            
            if not file_exists:
                # En-têtes
                writer.writerow([
                    'session_id',
                    'start_time',
                    'end_time',
                    'duration_hours',
                    'initial_equity',
                    'final_equity',
                    'return_pct',
                    'monthly_return_pct',
                    'total_trades',
                    'winning_trades',
                    'losing_trades',
                    'win_rate',
                    'total_profit',
                    'total_net_profit',
                    'avg_profit',
                    'avg_win',
                    'avg_loss',
                    'profit_factor',
                    'sharpe_ratio',
                    'max_drawdown',
                    'max_drawdown_pct'
                ])
            
            # Données
            metrics = self.session_data['metrics']
            writer.writerow([
                self.session_data['session_id'],
                self.session_data['start_time'],
                self.session_data['end_time'],
                metrics.get('session_duration_hours', 0),
                self.session_data['initial_equity'],
                self.session_data['final_equity'],
                metrics.get('return_pct', 0),
                metrics.get('monthly_return_pct', 0),
                metrics.get('total_trades', 0),
                metrics.get('winning_trades', 0),
                metrics.get('losing_trades', 0),
                metrics.get('win_rate', 0),
                metrics.get('total_profit', 0),
                metrics.get('total_net_profit', 0),
                metrics.get('avg_profit', 0),
                metrics.get('avg_win', 0),
                metrics.get('avg_loss', 0),
                metrics.get('profit_factor', 0),
                metrics.get('sharpe_ratio', 0),
                metrics.get('max_drawdown', 0),
                metrics.get('max_drawdown_pct', 0)
            ])
    
    def get_latest_metrics(self) -> Dict:
        """Récupère les métriques de la session actuelle"""
        return self.calculate_metrics()
