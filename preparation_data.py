import pandas as pd
import numpy as np

def ajouter_indicateurs(df):
    """
    Cette fonction prend les données brutes et ajoute des indicateurs techniques.
    """
    # On fait une copie pour ne pas modifier l'original par erreur
    df = df.copy()
    
    # 1. Rendement journalier (En pourcentage)
    # Si l'or prend 1%, la valeur sera 0.01
    df['Returns'] = df['Close'].pct_change()
    
    # 2. Moyennes Mobiles (SMA)
    # SMA_15 : Tendance court terme
    # SMA_60 : Tendance moyen terme
    df['SMA_15'] = df['Close'].rolling(window=15).mean()
    df['SMA_60'] = df['Close'].rolling(window=60).mean()
    
    # 3. Volatilité (Est-ce que ça bouge beaucoup ?)
    df['Volatilite'] = df['Returns'].rolling(window=15).std()
    
    # 4. CRÉATION DE LA CIBLE (Ce qu'on veut prédire)
    # On crée une colonne 'Target'.
    # On décale les données de -1 jour. Pourquoi ?
    # Parce qu'on veut savoir aujourd'hui si le prix de DEMAIN sera plus haut.
    # (Close de demain > Close d'aujourd'hui)
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    # Nettoyage : Les calculs de moyennes créent des trous (NaN) au début. On les supprime.
    df.dropna(inplace=True)
    
    return df

if __name__ == "__main__":
    # Petit test rapide pour voir si ça marche
    # On simule un petit tableau de données
    print("--- Test du calcul des indicateurs ---")
    
    # On importe ton script précédent pour récupérer les vraies données
    try:
        from collect_data import telecharger_donnees
        df_brut = telecharger_donnees()
        
        if df_brut is not None:
            df_complet = ajouter_indicateurs(df_brut)
            
            print("\n--- Résultat : Tableau prêt pour l'IA ---")
            print(df_complet[['Close', 'Returns', 'SMA_15', 'Target']].tail(10))
            print("\nExplication Target : 1 = Le prix monte le lendemain, 0 = Le prix baisse.")
            
    except ImportError:
        print("Assure-toi que le fichier collect_data.py est bien dans le même dossier !")