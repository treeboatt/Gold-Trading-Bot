import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import classification_report
from src.preparation_data import ajouter_indicateurs
from src.collect_data import telecharger_donnees

def optimiser_modele():
    print("--- ⚙️ Démarrage de l'Optimisation Avancée (Grid Search) ---")
    print("Cela peut prendre quelques minutes...\n")
    
    df_raw = telecharger_donnees()
    if df_raw is None:
        return

    df = ajouter_indicateurs(df_raw)

    features = [
        'Returns_OR', 'Returns_SP500', 'Returns_BTC', 'Returns_DXY', 'Returns_US10Y', 'Returns_VIX',
        'Dist_SMA_15', 'Dist_SMA_60', 'RSI', 
        'Volatilite', 'Corr_OR_SP500', 'Corr_OR_BTC', 'Corr_OR_DXY', 'Corr_OR_US10Y', 'Corr_OR_VIX'
    ]
    
    X = df[features]
    y = df['Target']

    # On garde les 85% premiers jours pour l'entrainement/optimisation
    # Et les 15% derniers pour la validation finale
    split_index = int(len(df) * 0.85)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    # Définition de la grille de paramètres à tester
    # L'ordinateur va tout essayer pour trouver le combo gagnant
    param_grid = {
        'n_estimators': [100, 200, 300],         # Nombre d'arbres
        'learning_rate': [0.01, 0.05, 0.1],      # Vitesse d'apprentissage
        'max_depth': [3, 5, 7],                  # Complexité des arbres
        'min_samples_split': [2, 5, 10],         # Sécurité anti-surchauffe
        'subsample': [0.8, 1.0]                  # Diversité des données
    }

    model_base = GradientBoostingClassifier(random_state=42)

    # TimeSeriesSplit est crucial : on ne mélange pas le passé et le futur
    tscv = TimeSeriesSplit(n_splits=5)

    grid_search = GridSearchCV(
        estimator=model_base,
        param_grid=param_grid,
        cv=tscv,
        scoring='precision', # ON VISE LA PRÉCISION PURE
        n_jobs=-1,           # Utilise tous les coeurs du processeur
        verbose=1
    )

    grid_search.fit(X_train, y_train)

    print(f"\n✅ Meilleurs paramètres trouvés : {grid_search.best_params_}")
    print(f"🎯 Meilleur score (Validation croisée) : {grid_search.best_score_:.4f}")

    best_model = grid_search.best_estimator_

    print("\n--- Test sur les données inconnues (2025/2026) ---")
    predictions = best_model.predict(X_test)
    print(classification_report(y_test, predictions))
    
    joblib.dump(best_model, 'models/modele_or.pkl')
    print("💾 Le modèle optimisé a été sauvegardé dans 'models/modele_or.pkl'")

if __name__ == "__main__":
    optimiser_modele()