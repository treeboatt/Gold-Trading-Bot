import pandas as pd
import matplotlib.pyplot as plt
import joblib
from src.preparation_data import ajouter_indicateurs
from src.collect_data import telecharger_donnees

def lancer_backtest():
    print("--- 🎬 Simulation Finale (VIX + US10Y + Smart Trend) ---")
    
    df_raw = telecharger_donnees()
    if df_raw is None:
        return

    df = ajouter_indicateurs(df_raw)

    df['Trend_SMA_50'] = df['Close_OR'].rolling(window=50).mean()

    # LISTE EXACTE AVEC VIX
    features = [
        'Returns_OR', 'Returns_SP500', 'Returns_BTC', 'Returns_DXY', 'Returns_US10Y', 'Returns_VIX',
        'Dist_SMA_15', 'Dist_SMA_60', 'RSI', 
        'Volatilite', 'Corr_OR_SP500', 'Corr_OR_BTC', 'Corr_OR_DXY', 'Corr_OR_US10Y', 'Corr_OR_VIX'
    ]
    
    missing_cols = [col for col in features if col not in df.columns]
    if missing_cols:
        print(f"Erreur : Colonnes manquantes : {missing_cols}")
        return

    X = df[features]
    
    # Test sur les 6 derniers mois
    split_index = int(len(df) * 0.85)
    df_test = df.iloc[split_index:].copy()
    X_test = X.iloc[split_index:]
    
    try:
        model = joblib.load('models/modele_or.pkl')
    except FileNotFoundError:
        print("Erreur : Modèle introuvable.")
        return

    print("🔮 Calcul des prédictions...")
    predictions = model.predict(X_test)
    probs = model.predict_proba(X_test)
    
    positions = []
    
    for i in range(len(df_test)):
        pred = predictions[i]
        
        prix_actuel = df_test['Close_OR'].iloc[i]
        trend_ma = df_test['Trend_SMA_50'].iloc[i]
        
        if pred == 1:
            positions.append(1) # ACHAT
        else:
            if prix_actuel < trend_ma:
                positions.append(-1) # SHORT
            else:
                positions.append(0) # CASH
    
    df_test['Position'] = positions
    df_test['Strategy_Return'] = df_test['Position'].shift(1) * df_test['Returns_OR']
    
    # Frais simulés
    frais = 0.0002 
    df_test['Cout_Frais'] = abs(df_test['Position'].diff()) * frais
    df_test['Strategy_Return'] = df_test['Strategy_Return'] - df_test['Cout_Frais'].fillna(0)

    capital_depart = 10000
    df_test['Cumul_Hold'] = capital_depart * (1 + df_test['Returns_OR']).cumprod()
    df_test['Cumul_Strategy'] = capital_depart * (1 + df_test['Strategy_Return']).cumprod()
    
    perf_hold = df_test['Cumul_Hold'].iloc[-1]
    perf_bot = df_test['Cumul_Strategy'].iloc[-1]
    
    print(f"\n{'='*40}")
    print(f" 📊 RÉSULTATS DUEL (Avec VIX)")
    print(f"{'='*40}")
    print(f"💰 Capital Départ    : {capital_depart} $")
    print(f"📈 Buy & Hold (Or)   : {perf_hold:.2f} $")
    print(f"🤖 Robot (VIX)       : {perf_bot:.2f} $")
    print(f"{'='*40}")
    
    diff = perf_bot - perf_hold
    print(f"Différence : {diff:+.2f} $")

    plt.figure(figsize=(12, 6))
    plt.plot(df_test.index, df_test['Cumul_Hold'], label='Marché', color='gray', alpha=0.5)
    plt.plot(df_test.index, df_test['Cumul_Strategy'], label='Robot VIX + Trend', color='#00d2be', linewidth=2)
    plt.title("Robot vs Marché (Modèle VIX 65%)")
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    lancer_backtest()