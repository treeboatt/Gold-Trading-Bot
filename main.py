import joblib
import pandas as pd
import os
from src.collect_data import telecharger_donnees
from src.preparation_data import ajouter_indicateurs
from src.sentiment_analysis import recuperer_news_sentiment

def sauvegarder_ordre(date, prix, tendance, prediction, confiance, sentiment, decision):
    fichier = "journal_trading.csv"
    fichier_existe = os.path.isfile(fichier)
    
    donnees = {
        'Date': [date],
        'Prix_Or': [prix],
        'Tendance_SMA50': [tendance],
        'Prediction_IA': [prediction],
        'Confiance_IA': [f"{confiance*100:.2f}%"],
        'Sentiment_News': [sentiment],
        'Decision_Finale': [decision]
    }
    
    df_new = pd.DataFrame(donnees)
    
    if not fichier_existe:
        df_new.to_csv(fichier, index=False, sep=';')
    else:
        df_new.to_csv(fichier, mode='a', header=False, index=False, sep=';')
    
    print(f"\n💾 Ordre enregistré dans '{fichier}'")

def predire_demain():
    print("--- 🤖 INITIALISATION DU ROBOT (Version VIX + 65% Précision) ---")
    
    df_raw = telecharger_donnees()
    if df_raw is None:
        return

    df = ajouter_indicateurs(df_raw)
    
    df['Trend_SMA_50'] = df['Close_OR'].rolling(window=50).mean()

    # LISTE FEATURES MISE À JOUR (AVEC VIX)
    features = [
        'Returns_OR', 'Returns_SP500', 'Returns_BTC', 'Returns_DXY', 'Returns_US10Y', 'Returns_VIX',
        'Dist_SMA_15', 'Dist_SMA_60', 'RSI', 
        'Volatilite', 'Corr_OR_SP500', 'Corr_OR_BTC', 'Corr_OR_DXY', 'Corr_OR_US10Y', 'Corr_OR_VIX'
    ]
    
    # Vérification anti-crash
    missing = [col for col in features if col not in df.columns]
    if missing:
        print(f"Erreur technique : Il manque ces colonnes dans les données : {missing}")
        print("Vérifie que src/collect_data.py et src/preparation_data.py sont bien à jour avec le VIX.")
        return
    
    last_row = df.iloc[[-1]][features]
    current_price = df['Close_OR'].iloc[-1]
    current_trend = df['Trend_SMA_50'].iloc[-1]
    current_atr = df['ATR'].iloc[-1]
    date_jour = df.index[-1].strftime('%Y-%m-%d')

    print(f"\n📊 DATE : {date_jour}")
    print(f"💰 PRIX ACTUEL OR : {current_price:.2f} $")
    print(f"📈 TENDANCE (SMA50): {current_trend:.2f} $")
    
    if current_price > current_trend:
        tendance_msg = "HAUSSIÈRE (Bullish) 🟢"
        can_short = False
    else:
        tendance_msg = "BAISSIÈRE (Bearish) 🔴"
        can_short = True
        
    print(f"   État du marché : {tendance_msg}")

    try:
        model = joblib.load('models/modele_or.pkl')
    except FileNotFoundError:
        print("Erreur : Modèle introuvable.")
        return

    prediction = model.predict(last_row)[0]
    proba = model.predict_proba(last_row)[0]
    confiance = max(proba)

    force_signal = "FAIBLE"
    taille_position = "0.5%" 
    
    if confiance >= 0.65:
        force_signal = "TRÈS FORTE 🔥🔥"
        taille_position = "3.0%"
    elif confiance >= 0.60:
        force_signal = "FORTE 🔥"
        taille_position = "2.0%"
    elif confiance >= 0.55:
        force_signal = "MOYENNE ⚡"
        taille_position = "1.0%"
    else:
        force_signal = "FAIBLE ⚠️"
        taille_position = "0.5% (Position réduite)"

    print(f"\n🧠 AVIS DE L'IA : {'ACHAT' if prediction == 1 else 'VENTE'}")
    print(f"   Confiance   : {confiance*100:.2f}%")
    print(f"   Intensité   : {force_signal}")

    print("\n📰 ANALYSE DES NEWS...")
    sentiment_score = recuperer_news_sentiment()
    print(f"   Score Sentiment : {sentiment_score:.4f}")

    decision = "ATTENTE"
    icon = "⏳"
    conseil_mise = "0$"
    stop_loss = 0
    take_profit = 0
    
    if prediction == 1:
        decision = "ACHETER (LONG)"
        icon = "🚀"
        conseil_mise = taille_position
        
        stop_loss = current_price - (1.5 * current_atr)
        take_profit = current_price + (2.0 * current_atr)

        if sentiment_score < -0.10:
            decision += " + CONFIRMATION NEWS (Peur)"
            
    else:
        if can_short:
            decision = "VENDRE (SHORT)"
            icon = "📉"
            conseil_mise = taille_position
            
            stop_loss = current_price + (1.5 * current_atr)
            take_profit = current_price - (2.0 * current_atr)
        else:
            decision = "RESTER CASH (Sécurité)"
            icon = "🛡️"
            conseil_mise = "0% (Ne rien faire)"
            print("   (Raison : Signal Vente mais Tendance Haussière)")

    print(f"\n{'='*45}")
    print(f" {icon} ORDRE DU JOUR : {decision}")
    print(f" 💰 Mise conseillée : {conseil_mise}")
    
    if stop_loss > 0:
        print(f" 🛑 STOP LOSS     : {stop_loss:.2f} $")
        print(f" 🎯 TAKE PROFIT   : {take_profit:.2f} $")
    
    print(f"{'='*45}")

    sauvegarder_ordre(date_jour, current_price, current_trend, "ACHAT" if prediction == 1 else "VENTE", confiance, sentiment_score, decision)

if __name__ == "__main__":
    predire_demain()