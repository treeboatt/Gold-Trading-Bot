import pandas as pd
import numpy as np

def calculer_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculer_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    return true_range.rolling(window=period).mean()

def ajouter_indicateurs(df):
    df = df.copy()
    
    if 'High_OR' in df.columns:
        df['High'] = df['High_OR']
        df['Low'] = df['Low_OR']
        df['Close'] = df['Close_OR']
        col_or = 'Close_OR'
    else:
        col_or = 'Close'

    if col_or == 'Close_OR':
        df['Returns_OR'] = df['Close_OR'].pct_change()
        df['Returns_SP500'] = df['Close_SP500'].pct_change()
        df['Returns_BTC'] = df['Close_BITCOIN'].pct_change()
        df['Returns_DXY'] = df['Close_DXY'].pct_change()
        df['Returns_US10Y'] = df['Close_US10Y'].pct_change()
        df['Returns_VIX'] = df['Close_VIX'].pct_change()
        
        df['Corr_OR_SP500'] = df['Close_OR'].rolling(30).corr(df['Close_SP500'])
        df['Corr_OR_BTC'] = df['Close_OR'].rolling(30).corr(df['Close_BITCOIN'])
        df['Corr_OR_DXY'] = df['Close_OR'].rolling(30).corr(df['Close_DXY'])
        df['Corr_OR_US10Y'] = df['Close_OR'].rolling(30).corr(df['Close_US10Y'])
        df['Corr_OR_VIX'] = df['Close_OR'].rolling(30).corr(df['Close_VIX'])
    else:
        df['Returns'] = df['Close'].pct_change()
    
    df['SMA_15'] = df[col_or].rolling(window=15).mean()
    df['SMA_60'] = df[col_or].rolling(window=60).mean()
    
    df['Dist_SMA_15'] = df[col_or] / df['SMA_15']
    df['Dist_SMA_60'] = df[col_or] / df['SMA_60']
    
    df['RSI'] = calculer_rsi(df[col_or])
    df['Volatilite'] = df[col_or].pct_change().rolling(window=15).std()
    
    df['ATR'] = calculer_atr(df)
    
    df['Target'] = (df[col_or].shift(-1) > df[col_or]).astype(int)
    
    df.dropna(inplace=True)
    
    return df