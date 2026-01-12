import MetaTrader5 as mt5
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

# --- COLLE TON CHEMIN ICI (Garde le r devant !) ---
# Exemple : r"C:\Program Files\MetaTrader 5\terminal64.exe"
CHEMIN_MT5 = r"C:\Program Files\MetaTrader 5\terminal64.exe"

print(f"--- DIAGNOSTIC AVANCE ---")
print(f"1. Lancement forcé de : {CHEMIN_MT5}")

# On force le chemin spécifique
if not mt5.initialize(path=CHEMIN_MT5):
    print("❌ ECHEC INITIALISATION")
    print(f"Code Erreur : {mt5.last_error()}")
    quit()
else:
    print("✅ MT5 Initialisé (Logiciel lancé)")

print(f"2. Connexion au compte {MT5_LOGIN} sur {MT5_SERVER}...")

# Connexion
authorized = mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)

if authorized:
    print("✅ SUCCÈS TOTAL ! Connecté.")
    print(f"💰 Balance : {mt5.account_info().balance}")
else:
    print("❌ ECHEC LOGIN")
    print(f"Code Erreur : {mt5.last_error()}")

mt5.shutdown()