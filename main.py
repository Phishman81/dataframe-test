
import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from calendar import monthrange

def color_gradient(val):
    if val > 10:
        color = '#28a745'  # green
    elif val < -10:
        color = '#dc3545'  # red
    elif -10 <= val <= 10:
        color = '#ffc107'  # yellow
    else:
        color = '#6c757d'  # grey
    return 'background-color: %s' % color

def load_data(file):
    data = pd.read_csv(file)
    data['date'] = pd.to_datetime(data['date'])
    data['month_year'] = data['date'].dt.to_period('M')

    # Group by page and month_year, and calculate the sum of clicks
    grouped_data = data.groupby(['page', 'month_year'])['clicks'].sum().reset_index()
    grouped_data['clicks'] = grouped_data['clicks'].round(0).astype(int)
    
    # Create a column with clicks history for each page
    clicks_history = grouped_data.groupby('page')['clicks'].apply(list).reset_index()
    clicks_history.columns = ['page', 'clicks_history']

    # Calculate the total clicks for each page
    total_clicks = grouped_data.groupby('page')['clicks'].sum().reset_index()
    total_clicks.columns = ['page', 'total_clicks']
    
    # Estimate clicks for the full current month
    last_month = grouped_data['month_year'].max()
    days_passed = (pd.Timestamp.now() - pd.Timestamp(last_month.start_time)).days
    total_days = monthrange(last_month.start_time.year, last_month.start_time.month)[1]
    grouped_data.loc[grouped_data['month_year'] == last_month, 'clicks'] = (grouped_data['clicks'] / days_passed * total_days).round(0).astype(int)

    # Calculate the trend for each page as percentage change
    trend = grouped_data.groupby('page').apply(lambda x: LinearRegression().fit(np.arange(len(x)).reshape(-1, 1), x['clicks'].values).coef_[0] / x['clicks'].mean() * 100).reset_index()
    trend.columns = ['page', 'trend_percentage']
    trend['trend_percentage'] = trend['trend_percentage'].round(1)
    
    # Create a pivot table with pages as rows and months as columns
    pivot_data = grouped_data.pivot(index='page', columns='month_year', values='clicks').reset_index()
    numeric_columns = pivot_data.select_dtypes(include=[np.number]).columns
    pivot_data[numeric_columns] = pivot_data[numeric_columns].fillna(0).astype(int)
    
    # Merge the pivot table with clicks history, total clicks and trend
    pivot_data = pd.merge(pivot_data, clicks_history, on='page')
    pivot_data = pd.merge(pivot_data, total_clicks, on='page')
    pivot_data = pd.merge(pivot_data, trend, on='page')

    # Rename the last month column
    last_month_column = pivot_data.columns[-3]
    pivot_data = pivot_data.rename(columns={last_month_column: last_month_column + ' (current month)'})

    return pivot_data

def main():
    page = st.sidebar.selectbox("Choose a page", ["Main page", "Content Decay Overview"])
    
    if page == "Main page":
        st.title('Main Page')
        # Content of the main page goes here
    else:
        st.title('Content Decay Overview')
        
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            data = load_data(uploaded_file)
            st.dataframe(
                data.style.applymap(color_gradient, subset=["trend_percentage"]),
                column_config={
                    "clicks_history": st.column_config.LineChartColumn(
                        "Clicks over time"
                    ),
                    "trend_percentage": st.column_config.NumberColumn(
                        "Trend (%)",
                        help="Trend of clicks over time (slope of linear regression line expressed as percentage change per period)",
                        format="%d",
                    ),
                },
                hide_index=True,
            )

if __name__ == "__main__":
    main()
