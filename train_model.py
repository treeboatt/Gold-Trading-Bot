import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from preparation_data import ajouter_indicateurs
from collect_data import telecharger_donnees

def entrainer_modele():
    df_raw = telecharger_donnees()
    if df_raw is None:
        return None

    df = ajouter_indicateurs(df_raw)

    features = ['Returns', 'SMA_15', 'SMA_60', 'Volatilite']
    X = df[features]
    y = df['Target']

    split_index = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    model = RandomForestClassifier(n_estimators=100, min_samples_split=10, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    print(f"Précision du modèle : {accuracy:.2f}")
    print("\nRapport de classification :")
    print(classification_report(y_test, predictions))

    return model

if __name__ == "__main__":
    entrainer_modele()