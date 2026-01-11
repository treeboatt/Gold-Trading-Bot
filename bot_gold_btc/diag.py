import MetaTrader5 as mt5
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

print(f"--- DIAGNOSTIC DE CONNEXION ---")
print(f"1. Tentative de lancement de MT5...")

# On essaie d'initialiser
if not mt5.initialize():
    print("❌ ECHEC INITIALISATION")
    print(f"Code Erreur : {mt5.last_error()}")
    quit()
else:
    print("✅ MT5 Initialisé (Le logiciel est trouvé)")

print(f"2. Tentative de connexion au compte {MT5_LOGIN}...")

# On essaie de se connecter
authorized = mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)

if authorized:
    print("✅ SUCCÈS TOTAL ! Connecté au serveur.")
    print(mt5.account_info())
else:
    print("❌ ECHEC LOGIN")
    print(f"Code Erreur : {mt5.last_error()}")
    print("-> Vérifie ton mot de passe ou le nom du serveur.")

mt5.shutdown()