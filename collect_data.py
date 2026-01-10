import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# 1. DÉFINITION DES PARAMÈTRES
# GC=F est le symbole pour les Futures sur l'Or. 
# ^GSPC est le S&P 500 (pour comparer).
TICKER_OR = "GC=F" 

def telecharger_donnees():
    print(f"--- Récupération des données pour {TICKER_OR} ---")
    
    # On télécharge : période de 5 ans, bougies d'1 jour
    data = yf.download(TICKER_OR, period="5y", interval="1d")
    
    if len(data) > 0:
        print(f"Succès ! {len(data)} jours de données récupérés.")
        return data
    else:
        print("Erreur : Aucune donnée trouvée.")
        return None

def afficher_graphique(data):
    # Création de la fenêtre
    plt.figure(figsize=(12, 6))
    
    # Dessiner la courbe avec le prix de fermeture ('Close')
    plt.plot(data.index, data['Close'], label='Prix Or (USD)', color='gold', linewidth=2)
    
    # Ajouter des titres
    plt.title("Prix de l'Or (5 ans)", fontsize=16)
    plt.xlabel("Date")
    plt.ylabel("Prix en $")
    plt.legend()
    plt.grid(True)
    
    # Afficher le graphique
    print("Affichage du graphique...")
    plt.show()

# Cette partie lance le script
if __name__ == "__main__":
    df = telecharger_donnees()
    
    # Si on a des données, on affiche d'abord les 5 dernières lignes puis le graphique
    if df is not None:
        print("\n--- Aperçu des dernières données ---")
        print(df.tail()) 
        afficher_graphique(df)