import pandas as pd
from prophet import Prophet
from typing import Tuple

def forecast_usage(df: pd.DataFrame, periods: int = 7) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Forecast future electricity usage using Prophet."""
    df_prophet = df[['date', 'usage_kWh']].rename(columns={'date': 'ds', 'usage_kWh': 'y'})
    model = Prophet()
    model.fit(df_prophet)
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    return future, forecast
