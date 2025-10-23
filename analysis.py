import pandas as pd
from typing import Tuple, Dict

def validate_and_load_csv(file_path: str) -> pd.DataFrame:
    """Load and validate the uploaded CSV file."""
    df = pd.read_csv(file_path)
    if 'date' not in df.columns or 'usage_kWh' not in df.columns:
        raise ValueError("CSV must contain 'date' and 'usage_kWh' columns.")
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date', 'usage_kWh'])
    df['usage_kWh'] = pd.to_numeric(df['usage_kWh'], errors='coerce')
    df = df.dropna(subset=['usage_kWh'])
    return df

def aggregate_data(df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
    """Aggregate data to daily, weekly, or monthly."""
    df = df.set_index('date')
    agg = df.resample(freq)['usage_kWh'].sum().reset_index()
    return agg

def compute_stats(df: pd.DataFrame) -> Dict[str, float]:
    """Compute total, average, and peak usage, plus weekly, monthly, yearly averages."""
    total = df['usage_kWh'].sum()
    average = df['usage_kWh'].mean()
    peak = df['usage_kWh'].max()
    stats = {'total': total, 'average': average, 'peak': peak}
    # Daily average
    stats['average_daily'] = average
    if not df.empty:
        # Weekly average
        df_week = df.copy()
        df_week['week'] = pd.to_datetime(df_week['date']).dt.isocalendar().week
        df_week['year'] = pd.to_datetime(df_week['date']).dt.year
        week_groups = df_week.groupby(['year', 'week'])['usage_kWh'].sum()
        stats['average_weekly'] = week_groups.mean() if not week_groups.empty else 0
        # Monthly average
        df_month = df.copy()
        df_month['month'] = pd.to_datetime(df_month['date']).dt.month
        df_month['year'] = pd.to_datetime(df_month['date']).dt.year
        month_groups = df_month.groupby(['year', 'month'])['usage_kWh'].sum()
        stats['average_monthly'] = month_groups.mean() if not month_groups.empty else 0
        # Yearly average
        df_year = df.copy()
        df_year['year'] = pd.to_datetime(df_year['date']).dt.year
        year_groups = df_year.groupby(['year'])['usage_kWh'].sum()
        stats['average_yearly'] = year_groups.mean() if not year_groups.empty else 0
        # Robust: also provide averages based on actual counts
        stats['average_daily_actual'] = total / df['date'].nunique() if df['date'].nunique() > 0 else 0
        stats['average_weekly_actual'] = total / week_groups.shape[0] if week_groups.shape[0] > 0 else 0
        stats['average_monthly_actual'] = total / month_groups.shape[0] if month_groups.shape[0] > 0 else 0
        stats['average_yearly_actual'] = total / year_groups.shape[0] if year_groups.shape[0] > 0 else 0
    else:
        stats['average_weekly'] = 0
        stats['average_monthly'] = 0
        stats['average_yearly'] = 0
        stats['average_daily_actual'] = 0
        stats['average_weekly_actual'] = 0
        stats['average_monthly_actual'] = 0
        stats['average_yearly_actual'] = 0
    return stats
