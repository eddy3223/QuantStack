import sys
sys.path.insert(0, ".")

import pandas as pd

from src.analytics.features import FeatureEngine,compute_features
from src.data.database import get_session, init_database 
from src.data.models import PriceDaily, Instrument 

init_database()

with get_session() as session:
    instrument = session.query(Instrument).filter(Instrument.symbol == 'AAPL').first()
    if not instrument:
        raise ValueError("AAPL not found in database")

    prices = session.query(PriceDaily).filter(PriceDaily.instrument_id == instrument.id).all()
    if not prices:
        raise ValueError("No prices found for AAPL")

    price_df = pd.DataFrame({
        "date": [p.date for p in prices],
        "open": [p.open for p in prices],
        "high": [p.high for p in prices],
        "low": [p.low for p in prices],
        "close": [p.close for p in prices],
        "volume": [p.volume for p in prices],
    })
    price_df.set_index('date', inplace=True)
    price_df.sort_index(inplace=True)

    engine = FeatureEngine()
    features_df = engine.compute_all(price_df)
    feature_cols = engine.get_feature_names()
    print(features_df.head())
    print(feature_cols)
    print(features_df.shape)
    print(features_df[feature_cols].tail(20))
    print(features_df[feature_cols].describe())
    print(features_df[feature_cols].info())
    print(features_df[feature_cols].isnull().sum())
    print(features_df[feature_cols].isnull().sum().sum())
    print(features_df[feature_cols].isnull().sum().sum() / features_df[feature_cols].size)
    print(features_df[feature_cols].isnull().sum().sum() / features_df[feature_cols].size)