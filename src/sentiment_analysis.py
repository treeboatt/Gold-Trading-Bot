import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd

def telecharger_lexique():
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)

def recuperer_news_sentiment():
    telecharger_lexique()
    analyzer = SentimentIntensityAnalyzer()
    
    rss_urls = [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069",
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://www.investing.com/rss/news_25.rss" 
    ]
    
    news_items = []
    
    for url in rss_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            titre = entry.title
            score = analyzer.polarity_scores(titre)
            news_items.append({
                'Titre': titre,
                'Score': score['compound']
            })
    
    df = pd.DataFrame(news_items)
    
    if df.empty:
        return 0.0
    
    sentiment_moyen = df['Score'].mean()
    
    return sentiment_moyen

if __name__ == "__main__":
    score = recuperer_news_sentiment()
    print(f"\nSCORE DE SENTIMENT GLOBAL : {score:.4f}")
    print("(-1 = Extrême Peur, +1 = Extrême Optimisme)")
    
    if score < -0.05:
        print("Ambiance : NÉGATIVE (Risque de hausse de l'Or - valeur refuge)")
    elif score > 0.05:
        print("Ambiance : POSITIVE (Risque de baisse de l'Or)")
    else:
        print("Ambiance : NEUTRE")