"""
Script de démarrage du bot de trading
Gère le chemin d'exécution pour les imports
"""

import sys
import os

# Ajouter le dossier bot_gold_btc au path Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_gold_btc'))

# Importer et lancer le bot
from bot_gold_btc.main import main

if __name__ == "__main__":
    main()
