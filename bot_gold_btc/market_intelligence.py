"""
Intelligence de marché : Filtres S&P500, VIX et corrélations dynamiques
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
import MetaTrader5 as mt5

try:
    from .config import (
        SYMBOL_SP500, SYMBOL_VIX,
        SP500_WEAKNESS_THRESHOLD, VIX_HIGH_THRESHOLD,
        CORRELATION_WINDOW, CORRELATION_DECOUPLING
    )
    from .mt5_interface import MT5Interface
    from .logger import TradingLogger
except ImportError:
    from config import (
        SYMBOL_SP500, SYMBOL_VIX,
        SP500_WEAKNESS_THRESHOLD, VIX_HIGH_THRESHOLD,
        CORRELATION_WINDOW, CORRELATION_DECOUPLING
    )
    from mt5_interface import MT5Interface
    from logger import TradingLogger

logger = TradingLogger()

class MarketIntelligence:
    """Analyse de marché avancée pour identifier les opportunités"""
    
    def __init__(self, mt5_interface: MT5Interface):
        self.mt5 = mt5_interface
        self.cache = {}  # Cache pour éviter trop de requêtes
    
    def get_sp500_data(self, timeframe: int = mt5.TIMEFRAME_H1, count: int = 100) -> Optional[pd.DataFrame]:
        """
        Récupère les données du S&P 500
        
        Args:
            timeframe: Timeframe MT5
            count: Nombre de barres
        
        Returns:
            DataFrame avec les données ou None
        """
        try:
            df = self.mt5.get_rates(SYMBOL_SP500, timeframe, count)
            if df is not None and not df.empty:
                if 'close' not in df.columns:
                    df.rename(columns={'Close': 'close'}, inplace=True)
            return df
        except Exception as e:
            logger.log_error(f"Erreur récupération SP500: {e}")
            return None
    
    def get_vix_data(self, timeframe: int = mt5.TIMEFRAME_H1, count: int = 100) -> Optional[pd.DataFrame]:
        """
        Récupère les données du VIX
        
        Args:
            timeframe: Timeframe MT5
            count: Nombre de barres
        
        Returns:
            DataFrame avec les données ou None
        """
        try:
            df = self.mt5.get_rates(SYMBOL_VIX, timeframe, count)
            if df is not None and not df.empty:
                if 'close' not in df.columns:
                    df.rename(columns={'Close': 'close'}, inplace=True)
            return df
        except Exception as e:
            # VIX peut ne pas être disponible sur tous les brokers
            logger.log_info(f"VIX non disponible: {e}")
            return None
    
    def check_sp500_weakness(self) -> Dict[str, any]:
        """
        Vérifie si le S&P 500 montre des signes de faiblesse
        
        Returns:
            Dictionnaire avec l'analyse de faiblesse
        """
        df_sp500 = self.get_sp500_data()
        if df_sp500 is None or df_sp500.empty:
            return {
                'is_weak': False,
                'reason': 'Données SP500 indisponibles',
                'change_pct': 0.0,
                'current_price': 0.0
            }
        
        current_price = df_sp500['close'].iloc[-1]
        
        # Calculer la variation sur différentes périodes
        change_1d = (current_price - df_sp500['close'].iloc[-2]) / df_sp500['close'].iloc[-2] if len(df_sp500) > 1 else 0
        change_5d = (current_price - df_sp500['close'].iloc[-6]) / df_sp500['close'].iloc[-6] if len(df_sp500) > 5 else 0
        
        # Vérifier la tendance (SMA 20 vs prix actuel)
        sma_20 = df_sp500['close'].rolling(20).mean().iloc[-1]
        below_sma = current_price < sma_20
        
        # Signes de faiblesse
        is_weak = (
            change_1d < SP500_WEAKNESS_THRESHOLD or
            change_5d < -0.05 or  # Baisse de 5% sur 5 jours
            below_sma
        )
        
        reason = []
        if change_1d < SP500_WEAKNESS_THRESHOLD:
            reason.append(f"Baisse journalière: {change_1d*100:.2f}%")
        if change_5d < -0.05:
            reason.append(f"Baisse 5j: {change_5d*100:.2f}%")
        if below_sma:
            reason.append("Prix sous SMA20")
        
        return {
            'is_weak': is_weak,
            'reason': ' | '.join(reason) if reason else 'Pas de faiblesse détectée',
            'change_1d_pct': change_1d * 100,
            'change_5d_pct': change_5d * 100,
            'current_price': current_price,
            'below_sma20': below_sma
        }
    
    def check_vix_volatility(self) -> Dict[str, any]:
        """
        Vérifie le niveau de volatilité via le VIX
        
        Returns:
            Dictionnaire avec l'analyse du VIX
        """
        df_vix = self.get_vix_data()
        if df_vix is None or df_vix.empty:
            return {
                'is_high': False,
                'reason': 'VIX non disponible',
                'current_value': 0.0
            }
        
        current_vix = df_vix['close'].iloc[-1]
        is_high = current_vix > VIX_HIGH_THRESHOLD
        
        return {
            'is_high': is_high,
            'reason': f'VIX élevé ({current_vix:.2f})' if is_high else f'VIX normal ({current_vix:.2f})',
            'current_value': current_vix
        }
    
    def calculate_rolling_correlation(self,
                                     df1: pd.DataFrame,
                                     df2: pd.DataFrame,
                                     window: int = CORRELATION_WINDOW) -> pd.Series:
        """
        Calcule la corrélation glissante de Pearson entre deux séries
        
        Args:
            df1: Première série (doit avoir une colonne 'close')
            df2: Deuxième série (doit avoir une colonne 'close')
            window: Fenêtre de corrélation
        
        Returns:
            Série avec les corrélations
        """
        if df1.empty or df2.empty:
            return pd.Series()
        
        # Aligner les index
        aligned = pd.DataFrame({
            'series1': df1['close'],
            'series2': df2['close']
        }).dropna()
        
        if len(aligned) < window:
            return pd.Series()
        
        # Calculer la corrélation glissante
        correlations = aligned['series1'].rolling(window=window).corr(aligned['series2'])
        
        return correlations
    
    def analyze_correlation_decoupling(self) -> Dict[str, any]:
        """
        Analyse la déconnexion de corrélation entre Gold, BTC et SP500
        
        Returns:
            Dictionnaire avec l'analyse de corrélation
        """
        # Récupérer les données
        df_gold = self.mt5.get_rates("XAUUSD", mt5.TIMEFRAME_D1, count=100)
        df_btc = self.mt5.get_rates("BTCUSD", mt5.TIMEFRAME_D1, count=100)
        df_sp500 = self.get_sp500_data(mt5.TIMEFRAME_D1, count=100)
        
        if df_gold is None or df_btc is None:
            return {
                'gold_btc_corr': 0.0,
                'gold_sp500_corr': 0.0,
                'is_decoupled': False,
                'reason': 'Données insuffisantes'
            }
        
        # Normaliser les colonnes
        for df in [df_gold, df_btc, df_sp500]:
            if df is not None and 'close' not in df.columns:
                df.rename(columns={'Close': 'close'}, inplace=True)
        
        results = {}
        
        # Corrélation Gold/BTC
        if df_gold is not None and df_btc is not None:
            corr_gold_btc = self.calculate_rolling_correlation(df_gold, df_btc, CORRELATION_WINDOW)
            if not corr_gold_btc.empty:
                current_corr_gold_btc = corr_gold_btc.iloc[-1]
                results['gold_btc_corr'] = current_corr_gold_btc if not np.isnan(current_corr_gold_btc) else 0.0
            else:
                results['gold_btc_corr'] = 0.0
        
        # Corrélation Gold/SP500
        if df_gold is not None and df_sp500 is not None:
            corr_gold_sp500 = self.calculate_rolling_correlation(df_gold, df_sp500, CORRELATION_WINDOW)
            if not corr_gold_sp500.empty:
                current_corr_gold_sp500 = corr_gold_sp500.iloc[-1]
                results['gold_sp500_corr'] = current_corr_gold_sp500 if not np.isnan(current_corr_gold_sp500) else 0.0
            else:
                results['gold_sp500_corr'] = 0.0
        
        # Détecter la déconnexion
        # Si Gold se déconnecte de SP500 (corrélation faible) = opportunité refuge
        is_decoupled = (
            abs(results.get('gold_sp500_corr', 1.0)) < CORRELATION_DECOUPLING or
            abs(results.get('gold_btc_corr', 1.0)) < CORRELATION_DECOUPLING
        )
        
        reason = []
        if abs(results.get('gold_sp500_corr', 1.0)) < CORRELATION_DECOUPLING:
            reason.append(f"Gold/SP500 déconnectés (corr: {results.get('gold_sp500_corr', 0):.2f})")
        if abs(results.get('gold_btc_corr', 1.0)) < CORRELATION_DECOUPLING:
            reason.append(f"Gold/BTC déconnectés (corr: {results.get('gold_btc_corr', 0):.2f})")
        
        results['is_decoupled'] = is_decoupled
        results['reason'] = ' | '.join(reason) if reason else 'Corrélations normales'
        
        return results
    
    def should_trade_refuge_asset(self) -> Tuple[bool, str]:
        """
        Détermine si les conditions sont favorables pour trader l'or comme valeur refuge
        
        Returns:
            Tuple (should_trade, reason)
        """
        sp500_analysis = self.check_sp500_weakness()
        vix_analysis = self.check_vix_volatility()
        correlation_analysis = self.analyze_correlation_decoupling()
        
        reasons = []
        should_trade = False
        
        # Condition 1: S&P 500 en faiblesse
        if sp500_analysis['is_weak']:
            should_trade = True
            reasons.append(f"SP500 faible: {sp500_analysis['reason']}")
        
        # Condition 2: VIX élevé (volatilité)
        if vix_analysis['is_high']:
            should_trade = True
            reasons.append(f"VIX élevé: {vix_analysis['reason']}")
        
        # Condition 3: Déconnexion de corrélation
        if correlation_analysis['is_decoupled']:
            should_trade = True
            reasons.append(f"Déconnexion: {correlation_analysis['reason']}")
        
        # Au moins une condition doit être remplie
        reason_str = ' | '.join(reasons) if reasons else 'Conditions normales (pas de signal refuge)'
        
        return should_trade, reason_str
    
    def get_market_sentiment(self) -> Dict[str, any]:
        """
        Récupère un résumé complet du sentiment de marché
        
        Returns:
            Dictionnaire avec toutes les métriques
        """
        sp500 = self.check_sp500_weakness()
        vix = self.check_vix_volatility()
        correlation = self.analyze_correlation_decoupling()
        should_trade, reason = self.should_trade_refuge_asset()
        
        return {
            'sp500_analysis': sp500,
            'vix_analysis': vix,
            'correlation_analysis': correlation,
            'should_trade_refuge': should_trade,
            'trade_reason': reason,
            'timestamp': pd.Timestamp.now()
        }
