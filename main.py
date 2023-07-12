import streamlit as st
import pandas as pd
import numpy as np

def load_data(file):
    data = pd.read_csv(file)
    data['date'] = pd.to_datetime(data['date'])
    data['month_year'] = data['date'].dt.to_period('M')

    # Group by page and month_year, and calculate the sum of clicks
    grouped_data = data.groupby(['page', 'month_year'])['clicks'].sum().reset_index()
    
    # Create a column with clicks history for each page
    clicks_history = grouped_data.groupby('page')['clicks'].apply(list).reset_index()
    clicks_history.columns = ['page', 'clicks_history']
    
    # Create a pivot table with pages as rows and months as columns
    pivot_data = grouped_data.pivot(index='page', columns='month_year', values='clicks').reset_index()
    pivot_data = pivot_data.fillna(0)
    
    # Merge the pivot table with clicks history
    pivot_data = pd.merge(pivot_data, clicks_history, on='page')

    # Calculate the expected clicks for the current month based on the average of the previous months
    pivot_data['Expected Clicks in current month'] = pivot_data.iloc[:, 1:-2].mean(axis=1)
    
    # Calculate the deviation for each month
    months = grouped_data['month_year'].unique()
    for month in months:
        pivot_data[str(month) + ' deviation'] = pivot_data[month] - pivot_data['Expected Clicks in current month']
        pivot_data[str(month) + ' % deviation'] = pivot_data[str(month) + ' deviation'] / pivot_data['Expected Clicks in current month'] * 100

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
                data,
                column_config={
                    "clicks_history": st.column_config.LineChartColumn(
                        "Clicks over time"
                    ),
                },
                hide_index=True,
            )

if __name__ == "__main__":
    main()
