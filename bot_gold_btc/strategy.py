"""
Stratégie de Statistical Arbitrage (Pairs Trading) entre XAUUSD et BTCUSD
Basée sur le Z-Score du ratio Gold/BTC
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
import MetaTrader5 as mt5

try:
    from .config import (
        SYMBOL_GOLD, SYMBOL_BTC,
        RATIO_WINDOW_MIN, RATIO_WINDOW_MAX, RATIO_WINDOW_DEFAULT,
        Z_SCORE_ENTRY, Z_SCORE_EXIT,
        SPREAD_MULTIPLIER, SPREAD_MAX_PCT,
        ATR_MIN_THRESHOLD, ATR_PERIOD
    )
    from .mt5_interface import MT5Interface
    from .logger import TradingLogger
except ImportError:
    from config import (
        SYMBOL_GOLD, SYMBOL_BTC,
        RATIO_WINDOW_MIN, RATIO_WINDOW_MAX, RATIO_WINDOW_DEFAULT,
        Z_SCORE_ENTRY, Z_SCORE_EXIT,
        SPREAD_MULTIPLIER, SPREAD_MAX_PCT,
        ATR_MIN_THRESHOLD, ATR_PERIOD
    )
    from mt5_interface import MT5Interface
    from logger import TradingLogger

logger = TradingLogger()

class PairsTradingStrategy:
    """Stratégie de pairs trading basée sur le Z-Score"""
    
    def __init__(self, mt5_interface: MT5Interface):
        self.mt5_interface = mt5_interface
        self.timeframe = mt5.TIMEFRAME_M15  # Timeframe pour le pairs trading
        self.ratio_history = []  # Historique du ratio pour calcul Z-Score
        self.current_window = RATIO_WINDOW_DEFAULT  # Fenêtre dynamique actuelle
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalise les noms de colonnes MT5"""
        if df is None or df.empty:
            return df
        
        column_mapping = {
            'Close': 'close',
            'High': 'high',
            'Low': 'low',
            'Open': 'open',
            'Volume': 'volume'
        }
        
        for old, new in column_mapping.items():
            if old in df.columns and new not in df.columns:
                df.rename(columns={old: new}, inplace=True)
        
        return df
    
    def calculate_ratio(self, df_gold: pd.DataFrame, df_btc: pd.DataFrame) -> pd.Series:
        """
        Calcule le ratio Gold/BTC sur les 100 dernières bougies
        
        Args:
            df_gold: DataFrame avec les prix de l'or
            df_btc: DataFrame avec les prix du Bitcoin
        
        Returns:
            Série avec les ratios
        """
        df_gold = self._normalize_columns(df_gold)
        df_btc = self._normalize_columns(df_btc)
        
        if df_gold.empty or df_btc.empty or 'close' not in df_gold.columns or 'close' not in df_btc.columns:
            return pd.Series()
        
        # Aligner les index
        aligned = pd.DataFrame({
            'gold': df_gold['close'],
            'btc': df_btc['close']
        }).dropna()
        
        if aligned.empty:
            return pd.Series()
        
        # Calculer le ratio
        ratio = aligned['gold'] / aligned['btc']
        
        return ratio
    
    def calculate_dynamic_window(self, ratio: pd.Series) -> int:
        """
        Calcule la fenêtre optimale dynamique (60-100 périodes)
        Ajuste selon la volatilité et la disponibilité des données
        
        Args:
            ratio: Série avec les ratios
        
        Returns:
            Fenêtre optimale entre RATIO_WINDOW_MIN et RATIO_WINDOW_MAX
        """
        available_data = len(ratio)
        
        if available_data < RATIO_WINDOW_MIN:
            return available_data if available_data > 10 else RATIO_WINDOW_MIN
        
        # Si on a assez de données, utiliser la fenêtre max
        if available_data >= RATIO_WINDOW_MAX:
            return RATIO_WINDOW_MAX
        
        # Sinon, utiliser ce qui est disponible
        return min(available_data, RATIO_WINDOW_MAX)
    
    def calculate_z_score(self, ratio: pd.Series, window: Optional[int] = None) -> Tuple[float, float, float, int]:
        """
        Calcule le Z-Score du ratio avec fenêtre dynamique
        
        Args:
            ratio: Série avec les ratios
            window: Fenêtre de calcul (None = calcul dynamique)
        
        Returns:
            Tuple (z_score, ratio_mean, ratio_std, window_used)
        """
        if ratio.empty:
            return 0.0, 0.0, 0.0, RATIO_WINDOW_DEFAULT
        
        # Calculer la fenêtre dynamique
        if window is None:
            window = self.calculate_dynamic_window(ratio)
        
        if len(ratio) < window:
            window = len(ratio)
        
        if window < RATIO_WINDOW_MIN:
            return 0.0, 0.0, 0.0, window
        
        # Prendre les N dernières valeurs
        recent_ratios = ratio.tail(window)
        
        if len(recent_ratios) < 2:
            return 0.0, 0.0, 0.0, window
        
        # Calculer moyenne et écart-type
        ratio_mean = recent_ratios.mean()
        ratio_std = recent_ratios.std()
        
        if ratio_std == 0 or np.isnan(ratio_std):
            return 0.0, ratio_mean, 0.0, window
        
        # Z-Score actuel
        current_ratio = recent_ratios.iloc[-1]
        z_score = (current_ratio - ratio_mean) / ratio_std
        
        # Mettre à jour la fenêtre actuelle
        self.current_window = window
        
        return z_score, ratio_mean, ratio_std, window
    
    def check_atr_filter(self, df_gold: pd.DataFrame, df_btc: pd.DataFrame) -> Tuple[bool, float, float]:
        """
        Vérifie si le marché n'est pas "mort" (filtre ATR)
        
        Args:
            df_gold: DataFrame avec les données Gold
            df_btc: DataFrame avec les données BTC
        
        Returns:
            Tuple (is_sufficient, atr_gold_pct, atr_btc_pct)
        """
        import pandas_ta as ta
        
        df_gold = self._normalize_columns(df_gold)
        df_btc = self._normalize_columns(df_btc)
        
        if df_gold.empty or df_btc.empty:
            return False, 0.0, 0.0
        
        # Calculer ATR pour Gold
        if all(col in df_gold.columns for col in ['high', 'low', 'close']):
            atr_gold = ta.atr(high=df_gold['high'], low=df_gold['low'], close=df_gold['close'], length=ATR_PERIOD)
            gold_price = df_gold['close'].iloc[-1]
            atr_gold_pct = (atr_gold.iloc[-1] / gold_price) if not atr_gold.empty and gold_price > 0 else 0.0
        else:
            atr_gold_pct = 0.0
        
        # Calculer ATR pour BTC
        if all(col in df_btc.columns for col in ['high', 'low', 'close']):
            atr_btc = ta.atr(high=df_btc['high'], low=df_btc['low'], close=df_btc['close'], length=ATR_PERIOD)
            btc_price = df_btc['close'].iloc[-1]
            atr_btc_pct = (atr_btc.iloc[-1] / btc_price) if not atr_btc.empty and btc_price > 0 else 0.0
        else:
            atr_btc_pct = 0.0
        
        # Vérifier si ATR suffisant (moyenne des deux)
        avg_atr_pct = (atr_gold_pct + atr_btc_pct) / 2
        is_sufficient = avg_atr_pct >= ATR_MIN_THRESHOLD
        
        return is_sufficient, atr_gold_pct, atr_btc_pct
    
    def check_spread_cost_filter(self,
                                gold_price: float,
                                btc_price: float,
                                z_score: float,
                                ratio_mean: float,
                                ratio_std: float) -> Tuple[bool, float]:
        """
        Vérifie si le gain potentiel est > 3x le spread ET si le spread n'est pas trop large
        
        Args:
            gold_price: Prix actuel de l'or
            btc_price: Prix actuel du Bitcoin
            z_score: Z-Score actuel
            ratio_mean: Moyenne du ratio
            ratio_std: Écart-type du ratio
        
        Returns:
            Tuple (should_trade, potential_gain_pct)
        """
        # Récupérer les spreads réels
        gold_tick = mt5.symbol_info_tick(SYMBOL_GOLD)
        btc_tick = mt5.symbol_info_tick(SYMBOL_BTC)
        
        if gold_tick is None or btc_tick is None:
            return False, 0.0
        
        # Calculer le spread en pourcentage
        gold_spread_pct = (gold_tick.ask - gold_tick.bid) / gold_price if gold_price > 0 else 0
        btc_spread_pct = (btc_tick.ask - btc_tick.bid) / btc_price if btc_price > 0 else 0
        
        total_spread_pct = gold_spread_pct + btc_spread_pct
        
        # Filtre 1: Spread ne doit pas être trop large
        if total_spread_pct > SPREAD_MAX_PCT:
            logger.log_info(f"Spread trop large: {total_spread_pct*100:.3f}% > {SPREAD_MAX_PCT*100:.3f}%")
            return False, 0.0
        
        # Gain potentiel = retour à la moyenne (Z-Score de 2.5 -> 0.0)
        # Le gain est proportionnel à l'écart du Z-Score
        potential_gain_pct = abs(z_score) * ratio_std / ratio_mean if ratio_mean > 0 else 0
        
        # Filtre 2: Gain doit être > 3x spread
        should_trade = potential_gain_pct > (total_spread_pct * SPREAD_MULTIPLIER)
        
        return should_trade, potential_gain_pct
    
    def analyze_pairs_opportunity(self) -> Optional[Dict]:
        """
        Analyse l'opportunité de pairs trading
        
        Returns:
            Dictionnaire avec le signal ou None
        """
        try:
            # Récupérer les données
            df_gold = self.mt5_interface.get_rates(SYMBOL_GOLD, self.timeframe, count=RATIO_WINDOW_DEFAULT + 10)
            df_btc = self.mt5_interface.get_rates(SYMBOL_BTC, self.timeframe, count=RATIO_WINDOW_DEFAULT + 10)
            
            if df_gold is None or df_btc is None:
                logger.log_error("Impossible de récupérer les données Gold/BTC")
                return None
            
            df_gold = self._normalize_columns(df_gold)
            df_btc = self._normalize_columns(df_btc)
            
            if df_gold.empty or df_btc.empty:
                return None
            
            # Vérifier le filtre ATR (marché pas "mort")
            atr_sufficient, atr_gold_pct, atr_btc_pct = self.check_atr_filter(df_gold, df_btc)
            if not atr_sufficient:
                logger.log_info(
                    f"Marché trop calme: ATR Gold={atr_gold_pct*100:.3f}%, BTC={atr_btc_pct*100:.3f}%"
                )
                return None
            
            # Calculer le ratio
            ratio = self.calculate_ratio(df_gold, df_btc)
            if ratio.empty:
                return None
            
            # Calculer le Z-Score avec fenêtre dynamique
            z_score, ratio_mean, ratio_std, window_used = self.calculate_z_score(ratio)
            
            if ratio_std == 0:
                return None
            
            # Prix actuels
            gold_price = df_gold['close'].iloc[-1]
            btc_price = df_btc['close'].iloc[-1]
            
            # Vérifier le filtre de coûts
            should_trade, potential_gain = self.check_spread_cost_filter(
                gold_price, btc_price, z_score, ratio_mean, ratio_std
            )
            
            if not should_trade:
                logger.log_info(
                    f"Opportunité filtrée: Gain potentiel {potential_gain*100:.2f}% < 3x spread"
                )
                return None
            
            # Générer le signal
            signal = None
            
            # Z-Score > 2.5 : Gold surévalué -> Vendre Gold, Acheter BTC (seuil chirurgical)
            if z_score > Z_SCORE_ENTRY:
                signal = {
                    'action': 'SELL_GOLD_BUY_BTC',
                    'gold_symbol': SYMBOL_GOLD,
                    'btc_symbol': SYMBOL_BTC,
                    'gold_action': 'SELL',
                    'btc_action': 'BUY',
                    'gold_price': gold_price,
                    'btc_price': btc_price,
                    'z_score': z_score,
                    'ratio_mean': ratio_mean,
                    'ratio_std': ratio_std,
                    'current_ratio': gold_price / btc_price,
                    'potential_gain_pct': potential_gain,
                    'window_used': window_used,
                    'atr_gold_pct': atr_gold_pct,
                    'atr_btc_pct': atr_btc_pct,
                    'reason': f'Z-Score {z_score:.2f} > {Z_SCORE_ENTRY} (Gold surévalué, fenêtre: {window_used})'
                }
                
                logger.log_signal(
                    symbole=f"{SYMBOL_GOLD}/{SYMBOL_BTC}",
                    signal="SELL_GOLD_BUY_BTC",
                    prix=gold_price,
                    message=signal['reason']
                )
            
            # Z-Score < -2.5 : Gold sous-évalué -> Acheter Gold, Vendre BTC (seuil chirurgical)
            elif z_score < -Z_SCORE_ENTRY:
                signal = {
                    'action': 'BUY_GOLD_SELL_BTC',
                    'gold_symbol': SYMBOL_GOLD,
                    'btc_symbol': SYMBOL_BTC,
                    'gold_action': 'BUY',
                    'btc_action': 'SELL',
                    'gold_price': gold_price,
                    'btc_price': btc_price,
                    'z_score': z_score,
                    'ratio_mean': ratio_mean,
                    'ratio_std': ratio_std,
                    'current_ratio': gold_price / btc_price,
                    'potential_gain_pct': potential_gain,
                    'window_used': window_used,
                    'atr_gold_pct': atr_btc_pct,
                    'atr_btc_pct': atr_btc_pct,
                    'reason': f'Z-Score {z_score:.2f} < -{Z_SCORE_ENTRY} (Gold sous-évalué, fenêtre: {window_used})'
                }
                
                logger.log_signal(
                    symbole=f"{SYMBOL_GOLD}/{SYMBOL_BTC}",
                    signal="BUY_GOLD_SELL_BTC",
                    prix=gold_price,
                    message=signal['reason']
                )
            
            return signal
        
        except Exception as e:
            logger.log_error(f"Erreur dans analyze_pairs_opportunity: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def should_close_pairs_position(self) -> Tuple[bool, str]:
        """
        Vérifie si les positions de la paire doivent être fermées (Z-Score retour à 0)
        
        Returns:
            Tuple (should_close, reason)
        """
        try:
            # Récupérer les positions ouvertes
            gold_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_GOLD)
            btc_positions = self.mt5_interface.get_open_positions(symbol=SYMBOL_BTC)
            
            # Vérifier qu'on a des positions sur les deux symboles
            if gold_positions.empty or btc_positions.empty:
                return False, "Pas de paire complète"
            
            # Récupérer les données pour calculer le Z-Score actuel
            df_gold = self.mt5_interface.get_rates(SYMBOL_GOLD, self.timeframe, count=RATIO_WINDOW + 10)
            df_btc = self.mt5_interface.get_rates(SYMBOL_BTC, self.timeframe, count=RATIO_WINDOW + 10)
            
            if df_gold is None or df_btc is None:
                return False, "Données indisponibles"
            
            df_gold = self._normalize_columns(df_gold)
            df_btc = self._normalize_columns(df_btc)
            
            # Calculer le ratio et Z-Score
            ratio = self.calculate_ratio(df_gold, df_btc)
            if ratio.empty:
                return False, "Ratio non calculable"
            
            z_score, _, _, _ = self.calculate_z_score(ratio)
            
            # Fermer si Z-Score retour à 0 (dans une bande de tolérance)
            if abs(z_score) <= abs(Z_SCORE_EXIT) + 0.1:  # Tolérance de 0.1
                return True, f"Z-Score retour à la moyenne: {z_score:.2f}"
            
            return False, f"Z-Score encore éloigné: {z_score:.2f}"
        
        except Exception as e:
            logger.log_error(f"Erreur dans should_close_pairs_position: {e}")
            return False, f"Erreur: {e}"
    
    def get_current_z_score(self) -> Optional[float]:
        """Récupère le Z-Score actuel"""
        try:
            df_gold = self.mt5_interface.get_rates(SYMBOL_GOLD, self.timeframe, count=RATIO_WINDOW + 10)
            df_btc = self.mt5_interface.get_rates(SYMBOL_BTC, self.timeframe, count=RATIO_WINDOW + 10)
            
            if df_gold is None or df_btc is None:
                return None
            
            df_gold = self._normalize_columns(df_gold)
            df_btc = self._normalize_columns(df_btc)
            
            ratio = self.calculate_ratio(df_gold, df_btc)
            if ratio.empty:
                return None
            
            z_score, _, _, _ = self.calculate_z_score(ratio)
            return z_score
        
        except Exception as e:
            logger.log_error(f"Erreur dans get_current_z_score: {e}")
            return None
