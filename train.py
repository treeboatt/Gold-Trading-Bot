import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from src.preparation_data import ajouter_indicateurs
from src.collect_data import telecharger_donnees

def entrainer_modele():
    df_raw = telecharger_donnees()
    if df_raw is None:
        return None

    df = ajouter_indicateurs(df_raw)

    features = [
        'Returns_OR', 'Returns_SP500', 'Returns_BTC',
        'Dist_SMA_15', 'Dist_SMA_60', 'RSI', 
        'Volatilite', 'Corr_OR_SP500', 'Corr_OR_BTC'
    ]
    
    X = df[features]
    y = df['Target']

    split_index = int(len(df) * 0.85)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    model = RandomForestClassifier(n_estimators=300, min_samples_split=10, max_depth=15, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    print(f"Précision du modèle : {accuracy:.2f}")
    print("\nRapport de classification :")
    print(classification_report(y_test, predictions))

    joblib.dump(model, 'models/modele_or.pkl')
    print("Modèle sauvegardé sous 'models/modele_or.pkl'")

    return model

if __name__ == "__main__":
    entrainer_modele()