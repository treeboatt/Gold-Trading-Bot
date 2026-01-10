import yfinance as yf
import pandas as pd

def telecharger_donnees():
    tickers = {
        'OR': 'GC=F',
        'SP500': '^GSPC',
        'BITCOIN': 'BTC-USD',
        'DXY': 'DX-Y.NYB',
        'US10Y': '^TNX',
        'VIX': '^VIX'
    }
    
    dfs = []
    
    for nom, symbole in tickers.items():
        try:
            data = yf.download(symbole, period="5y", interval="1d", auto_adjust=True, progress=False)
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            if nom == 'OR':
                data = data[['Close', 'High', 'Low']].rename(columns={
                    'Close': f'Close_{nom}',
                    'High': f'High_{nom}',
                    'Low': f'Low_{nom}'
                })
            else:
                data = data[['Close']].rename(columns={'Close': f'Close_{nom}'})
                
            dfs.append(data)
        except Exception as e:
            print(f"Erreur téléchargement {nom}: {e}")
    
    if not dfs:
        return None

    df_final = pd.concat(dfs, axis=1)
    df_final.dropna(inplace=True)
    
    return df_final

if __name__ == "__main__":
    df = telecharger_donnees()
    if df is not None:
        print(df.tail())