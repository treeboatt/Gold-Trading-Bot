import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, precision_score
from src.preparation_data import ajouter_indicateurs
from src.collect_data import telecharger_donnees

def comparer_modeles():
    print("--- ⚔️ Tournoi des Modèles (Critère : PRÉCISION) ⚔️ ---")
    
    df_raw = telecharger_donnees()
    if df_raw is None:
        return

    df = ajouter_indicateurs(df_raw)

    features = [
        'Returns_OR', 'Returns_SP500', 'Returns_BTC', 'Returns_DXY',
        'Dist_SMA_15', 'Dist_SMA_60', 'RSI', 
        'Volatilite', 'Corr_OR_SP500', 'Corr_OR_BTC', 'Corr_OR_DXY'
    ]
    
    X = df[features]
    y = df['Target']

    split_index = int(len(df) * 0.85)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    modeles = {
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
        "GradientBoosting": GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42),
        "LogisticRegression": LogisticRegression(random_state=42, max_iter=1000),
        "SVM (Support Vector)": SVC(probability=True, random_state=42),
        "KNN (Voisins)": KNeighborsClassifier(n_neighbors=15)
    }

    meilleur_score = 0
    meilleur_modele = None
    nom_vainqueur = ""

    print(f"\n{'='*65}")
    print(f"{'MODÈLE':<25} | {'PRÉCISION (ACHAT)':<18} | {'ACCURACY':<10}")
    print(f"{'='*65}")

    for nom, modele in modeles.items():
        modele.fit(X_train, y_train)
        preds = modele.predict(X_test)
        
        # On calcule la précision pour la classe 1 (Achat)
        # zero_division=0 évite les erreurs si le modèle ne prédit jamais 1
        prec = precision_score(y_test, preds, pos_label=1, zero_division=0)
        acc = accuracy_score(y_test, preds)
        
        print(f"{nom:<25} | {prec:.4f}             | {acc:.4f}")
        
        # CRITÈRE DE SÉLECTION : On veut la meilleure PRÉCISION
        # (Mais on exige quand même une accuracy > 50% pour ne pas avoir un modèle absurde)
        if prec > meilleur_score and acc > 0.50:
            meilleur_score = prec
            meilleur_modele = modele
            nom_vainqueur = nom

    print(f"{'='*65}")
    print(f"🏆 NOUVEAU VAINQUEUR : {nom_vainqueur}")
    print(f"   Précision Achat : {meilleur_score:.2%}")
    
    joblib.dump(meilleur_modele, 'models/modele_or.pkl')
    print(f"✅ Cerveau sauvegardé dans 'models/modele_or.pkl'")

if __name__ == "__main__":
    comparer_modeles()