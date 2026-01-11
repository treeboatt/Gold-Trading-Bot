# Bot de Trading Haute Fréquence - Gold/BTC pour MetaTrader 5

**Système professionnel de trading haute fréquence conçu pour surperformer le S&P 500**

## 🎯 Objectif

Ce bot exploite la corrélation dynamique entre l'Or (XAUUSD) et le Bitcoin (BTCUSD) avec une intelligence de marché avancée pour générer des rendements supérieurs à un investissement passif sur le S&P 500 (SPY).

## 🚀 Fonctionnalités Principales

### 1. Intelligence de Marché (Alpha)
- ✅ **Filtre S&P 500** : Trade uniquement quand le S&P 500 montre des signes de faiblesse (valeur refuge)
- ✅ **Analyse VIX** : Détecte les périodes de volatilité élevée (opportunités)
- ✅ **Corrélation Glissante** : Calcule la corrélation de Pearson sur 30 jours entre Gold, BTC et SP500
- ✅ **Déconnexion de Corrélation** : Identifie les moments où l'or se déconnecte des actions

### 2. Optimisation des Signaux
- ✅ **Multi-Timeframe** : Valide les signaux M15 uniquement si la tendance H4 est alignée
- ✅ **Filtrage ATR** : Évite les trades en période de faible volatilité (minimise les coûts)
- ✅ **RSI** : Confirme la force du mouvement (évite les surachats/surventes)
- ✅ **Golden Cross** : Détecte les croisements de moyennes mobiles (EMA20/EMA50)

### 3. Gestion du Risque Haute Précision
- ✅ **Position Sizing Dynamique** : Calcule automatiquement les lots pour risquer exactement 1.5% du capital
- ✅ **Trailing Stop Intelligent** : Protège les profits avec un stop loss dynamique basé sur 2x l'ATR
- ✅ **Circuit Breaker** : Arrêt automatique si perte journalière > 5%
- ✅ **Drawdown Maximum** : Protection à 15% de drawdown

### 4. Gestion des Coûts
- ✅ **Calcul Précis des Spreads** : Enregistre tous les coûts (spread + commission)
- ✅ **Profit Net** : Calcule le profit après déduction de tous les coûts
- ✅ **Optimisation Continue** : Enregistre toutes les données pour ML futur

## 📁 Structure du Projet

```
bot_gold_btc/
├── __init__.py              # Module Python
├── main.py                  # Point d'entrée principal (orchestration)
├── mt5_interface.py         # Interface MetaTrader 5 (connexion, ordres)
├── strategy.py              # Stratégie multi-timeframe avec RSI, Golden Cross
├── market_intelligence.py   # Intelligence de marché (SP500, VIX, corrélations)
├── risk_manager.py          # Gestion du risque (position sizing, trailing stop, circuit breaker)
├── strategy_optimizer.py     # Optimiseur pour ML futur
├── logger.py                 # Système de logging avancé
├── config.py                # Configuration complète
├── README.md                 # Ce fichier
└── COSTS_AND_PERFORMANCE.md # Documentation sur les coûts et performance
```

## 🚀 Installation

1. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

2. **Installer MetaTrader 5** :
   - Téléchargez et installez MetaTrader 5 depuis le site de votre broker
   - Assurez-vous que MT5 est installé et fonctionnel

3. **Configurer les identifiants** :
   - Ouvrez `bot_gold_btc/config.py`
   - Remplissez vos identifiants MT5 :
     ```python
     MT5_LOGIN = 12345678
     MT5_PASSWORD = "votre_mot_de_passe"
     MT5_SERVER = "Broker-Server"
     ```

## ⚙️ Configuration Avancée

Tous les paramètres sont dans `config.py` :

### Paramètres de Risque
- **RISK_PERCENT** : 1.5% de risque par trade (augmenté pour performance)
- **CIRCUIT_BREAKER_DAILY_LOSS** : 5% de perte journalière max
- **MAX_DRAWDOWN** : 15% de drawdown maximum

### Paramètres Techniques
- **EMA_PERIOD_SHORT** : 20 (Golden Cross)
- **EMA_PERIOD_LONG** : 50 (Golden Cross)
- **RSI_PERIOD** : 14
- **ATR_MIN_THRESHOLD** : 0.1% (évite les trades en faible volatilité)

### Paramètres Market Intelligence
- **SP500_WEAKNESS_THRESHOLD** : -2% (seuil de faiblesse S&P500)
- **VIX_HIGH_THRESHOLD** : 20 (volatilité élevée)
- **CORRELATION_DECOUPLING** : 0.3 (corrélation faible = opportunité)

### Coûts de Trading
- **SPREAD_GOLD_POINTS** : 30 points (ajuster selon votre broker)
- **COMMISSION_PER_LOT** : 0$ (ajuster si votre broker facture)

## 🏃 Utilisation

### Lancer le bot

```bash
cd bot_gold_btc
python main.py
```

Ou depuis la racine :
```bash
python run_bot.py
```

### Arrêter le bot

Appuyez sur `Ctrl+C` pour un arrêt propre. Les positions ouvertes resteront actives sur MT5.

## 📊 Logging et Données ML

### Fichiers générés

1. **trading_log.csv** : Tous les événements (signaux, ordres, erreurs)
2. **backtest_data.csv** : Données complètes pour Machine Learning
   - Indicateurs techniques (EMA, RSI, ATR)
   - Données de marché (SP500, VIX, corrélations)
   - Métriques de risque (balance, equity, drawdown)
   - Coûts de trading (spread, commission, profit net)

### Utilisation pour ML

Les données dans `backtest_data.csv` peuvent être utilisées pour :
- Entraîner un modèle XGBoost pour prédire les trades gagnants
- Entraîner un LSTM pour prédire les mouvements de prix
- Optimiser les paramètres de la stratégie
- Identifier les patterns gagnants/perdants

## 🎯 Stratégie de Trading

### Signal d'ACHAT (Or)

Le bot achète de l'or quand **TOUTES** ces conditions sont remplies :

1. ✅ **Intelligence de Marché** :
   - S&P 500 en faiblesse OU VIX élevé OU corrélation déconnectée

2. ✅ **Signal Technique M15** :
   - BTCUSD croise son EMA20 à la hausse
   - XAUUSD est sous son EMA20
   - RSI < 70 (pas de surachat)

3. ✅ **Validation H4** :
   - Tendance H4 alignée (haussière ou baissière)

4. ✅ **Filtrage ATR** :
   - ATR > 0.1% (volatilité suffisante)

### Gestion des Positions

- **Stop Loss** : 2x ATR sous le prix d'entrée
- **Take Profit** : 3x ATR au-dessus du prix d'entrée (ratio 1.5:1)
- **Trailing Stop** : Mis à jour toutes les 5 minutes (2x ATR sous le plus haut)
- **Fermeture Automatique** : Si le prix croise l'EMA dans le sens opposé

## 💰 Gestion des Coûts

Le bot calcule **précisément** tous les coûts :

- **Spread** : Récupéré en temps réel du broker
- **Commission** : Configurable dans `config.py`
- **Profit Net** : Profit brut - (Spread + Commission)

**Voir** `COSTS_AND_PERFORMANCE.md` pour les détails complets.

## 📈 Performance vs S&P 500

### Objectifs de Performance

- **Rendement annuel** : 12-15%+ (vs 8-10% pour SPY)
- **Win Rate** : > 55%
- **Profit Factor** : > 1.5
- **Sharpe Ratio** : > 1.5
- **Drawdown Maximum** : < 15%

### Avantages vs SPY

| Critère | SPY (ETF) | Bot de Trading |
|---------|-----------|----------------|
| Rendement | 8-10% annuel | 12-15%+ annuel (cible) |
| Contrôle | Aucun | Total (SL/TP) |
| Flexibilité | Long seulement | Long + Short |
| Leverage | Aucun | Modéré (1:5) |

## ⚠️ Avertissements

1. **Trading à risque** : Le trading comporte des risques de perte en capital
2. **Testez d'abord** : Testez le bot en mode démo avant d'utiliser de l'argent réel
3. **Surveillance** : Surveillez régulièrement le bot et vos positions
4. **Broker** : Assurez-vous que votre broker supporte XAUUSD, BTCUSD et US500
5. **Circuit Breaker** : Le bot s'arrête automatiquement si perte > 5% en une journée

## 🔧 Dépannage

### Erreur de connexion MT5
- Vérifiez que MT5 est installé et ouvert
- Vérifiez vos identifiants dans `config.py`
- Vérifiez que le serveur est correct

### Symboles non disponibles
- Vérifiez que XAUUSD, BTCUSD et US500 sont disponibles sur votre broker
- Certains brokers utilisent des noms différents (ex: GOLD au lieu de XAUUSD, SPX au lieu de US500)
- Ajustez `SYMBOL_SP500` dans `config.py` si nécessaire

### VIX non disponible
- Le VIX n'est pas disponible sur tous les brokers
- Le bot fonctionnera sans VIX (utilisera uniquement S&P500 et corrélations)

### Circuit Breaker activé
- Le bot s'arrête si perte journalière > 5%
- Vérifiez `trading_log.csv` pour comprendre la raison
- Réinitialisez le bot le jour suivant (le circuit breaker est journalier)

## 📝 Notes Techniques

- **Timeframe Entrée** : M15 (signaux)
- **Timeframe Tendance** : H4 (validation)
- **Leverage** : 1:5 par défaut (modéré, configurable)
- **Position Sizing** : Automatique basé sur 1.5% de risque
- **Trailing Stop** : Mis à jour toutes les 5 minutes

## 🚀 Optimisation Future

Le bot enregistre toutes les données nécessaires pour :

1. **Machine Learning** : Entraîner XGBoost/LSTM sur `backtest_data.csv`
2. **Optimisation de Paramètres** : Tester différentes combinaisons d'EMA, RSI, ATR
3. **Analyse de Patterns** : Identifier les conditions gagnantes/perdantes

## 📄 Licence

Ce projet est fourni tel quel, sans garantie. Utilisez à vos propres risques.

---

**💡 Le secret pour battre les ETF** : Minimiser le drawdown, profiter de l'effet de levier modéré, et ne trader que quand les conditions sont optimales (intelligence de marché + validation multi-timeframe).
