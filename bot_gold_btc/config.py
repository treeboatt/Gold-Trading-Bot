"""
Configuration du bot de trading MT5
Contient les identifiants de connexion et les paramètres de risque
"""

# ===== IDENTIFIANTS METATRADER 5 =====
# Remplacez ces valeurs par vos propres identifiants
MT5_LOGIN = 101181033  # Votre numéro de compte MT5
MT5_PASSWORD = "5gW!FgVi"  # Votre mot de passe
MT5_SERVER = "Broker-Server"  # Exemple: "MetaQuotes-Demo", "ICMarkets-Demo", etc.

# ===== SYMBOLES DE TRADING =====
SYMBOL_GOLD = "XAUUSD"  # Or
SYMBOL_BTC = "BTCUSD"   # Bitcoin
SYMBOL_SP500 = "US500"  # S&P 500 (peut être SPX, US500 selon broker)
SYMBOL_VIX = "VIX"      # VIX (peut nécessiter un broker spécifique)

# ===== PARAMÈTRES DE RISQUE INSTITUTIONNEL =====
RISK_PERCENT_MIN = 0.005  # 0.5% de risque minimum par trade
RISK_PERCENT_MAX = 0.01   # 1.0% de risque maximum par trade
RISK_PERCENT_DEFAULT = 0.005  # Risque par défaut (ajustable selon volatilité)
CIRCUIT_BREAKER_PAIR_LOSS = 0.02  # 2% de perte latente sur la paire = arrêt immédiat
MAX_LEVERAGE = 3  # Levier maximum autorisé (1:3 pour pairs trading)
MONTHLY_TARGET = 0.02  # Objectif de rendement mensuel (2%)
ANNUAL_TARGET = 0.24  # Objectif de rendement annuel (24% = 2% x 12 mois)

# ===== PARAMÈTRES PAIRS TRADING (Statistical Arbitrage) =====
RATIO_WINDOW_MIN = 60  # Fenêtre minimum pour calculer le ratio Gold/BTC
RATIO_WINDOW_MAX = 100  # Fenêtre maximum pour calculer le ratio Gold/BTC
RATIO_WINDOW_DEFAULT = 100  # Fenêtre par défaut
Z_SCORE_ENTRY = 2.5  # Z-Score pour entrée (seuil chirurgical > 2.5 écart-types)
Z_SCORE_EXIT = 0.0  # Z-Score pour sortie (retour à la moyenne)
SPREAD_MULTIPLIER = 3.0  # Gain potentiel doit être > 3x le spread pour trader
SPREAD_MAX_PCT = 0.002  # Spread maximum autorisé (0.2% = marché trop large)

# ===== PARAMÈTRES MULTI-TIMEFRAME =====
TIMEFRAME_ENTRY = "M15"  # Timeframe pour les signaux d'entrée
TIMEFRAME_TREND = "H4"   # Timeframe pour la tendance principale
ATR_MIN_THRESHOLD = 0.001  # ATR minimum (0.1%) pour éviter marché "mort"
ATR_PERIOD = 14  # Période pour calcul ATR

# ===== PARAMÈTRES DE TRADING =====
MAGIC_NUMBER = 123456  # Numéro magique pour identifier les ordres du bot
DEVIATION = 20  # Déviation maximale du prix en points
LEVERAGE = 3  # Effet de levier (1:3 maximum pour pairs trading)

# ===== PARAMÈTRES MARKET INTELLIGENCE =====
SP500_WEAKNESS_THRESHOLD = -0.02  # S&P500 doit être en baisse de 2% pour signal refuge
VIX_HIGH_THRESHOLD = 20  # VIX au-dessus de 20 = volatilité élevée
CORRELATION_DECOUPLING = 0.3  # Corrélation < 0.3 = déconnexion (opportunité)

# ===== PARAMÈTRES DE LA BOUCLE =====
CHECK_INTERVAL = 15  # Intervalle de vérification en secondes (pairs trading)
CONNECTION_CHECK_INTERVAL = 15  # Vérification connexion toutes les 15 secondes
MAX_RECONNECTION_ATTEMPTS = 3  # Nombre max de tentatives de reconnexion

# ===== PARAMÈTRES DE CONNEXION =====
TIMEOUT = 10000  # Timeout de connexion en millisecondes

# ===== COÛTS DE TRADING (pour calcul profit net) =====
SPREAD_GOLD_POINTS = 30  # Spread moyen XAUUSD en points (ex: 0.30$)
SPREAD_BTC_POINTS = 50   # Spread moyen BTCUSD en points
COMMISSION_PER_LOT = 0.0  # Commission par lot (ajuster selon broker)
SWAP_LONG_GOLD = -0.5    # Swap pour position LONG sur l'or (par lot/jour)
SWAP_SHORT_GOLD = 0.2    # Swap pour position SHORT sur l'or (par lot/jour)

# ===== PARAMÈTRES DE LOGGING ET PERFORMANCE =====
PERFORMANCE_LOG_FILE = "performance_data.json"  # Fichier JSON pour métriques
PERFORMANCE_LOG_CSV = "performance_data.csv"  # Fichier CSV pour analyse
SESSION_LOG_DIR = "sessions"  # Dossier pour logs par session
ENABLE_DETAILED_LOGGING = True  # Activer logging ultra-détaillé
