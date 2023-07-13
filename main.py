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
    data.columns = map(str.lower, data.columns)  

    page_variants = ['address', 'adresse', 'url']
    for variant in page_variants:
        if variant in data.columns:
            data = data.rename(columns={variant: 'page'})

    required_columns = ['date', 'clicks', 'page']
    if not set(required_columns).issubset(data.columns):
        raise ValueError(f"The CSV file must contain the following columns: {required_columns}")

    data['date'] = pd.to_datetime(data['date'])
    data['month_year'] = data['date'].dt.to_period('M')

    grouped_data = data.groupby(['page', 'month_year'])['clicks'].sum().reset_index()
    grouped_data['clicks'] = grouped_data['clicks'].round(0).astype(int)

    last_month = grouped_data['month_year'].max()
    days_passed = (pd.Timestamp.now() - pd.Timestamp(last_month.start_time)).days
    total_days = monthrange(last_month.start_time.year, last_month.start_time.month)[1]
    current_month_real_clicks = grouped_data[grouped_data['month_year'] == last_month].copy()
    current_month_real_clicks.columns = ['page', 'month_year', 'real_clicks_current_month']
    grouped_data.loc[grouped_data['month_year'] == last_month, 'clicks'] = (grouped_data['clicks'] / days_passed * total_days).round(0).astype(int)

    clicks_history = grouped_data.groupby('page')['clicks'].apply(list).reset_index()
    clicks_history.columns = ['page', 'clicks_history']

    total_clicks = grouped_data.groupby('page')['clicks'].sum().reset_index()
    total_clicks.columns = ['page', 'total_clicks']

    trend = grouped_data.groupby('page').apply(lambda x: LinearRegression().fit(np.arange(len(x)).reshape(-1, 1), x['clicks'].values).coef_[0] / x['clicks'].mean() * 100).reset_index()
    trend.columns = ['page', 'trend_percentage']
    trend['trend_percentage'] = trend['trend_percentage'].round(1)

    pivot_data = grouped_data.pivot(index='page', columns='month_year', values='clicks').reset_index()
    numeric_columns = pivot_data.select_dtypes(include=[np.number]).columns
    pivot_data[numeric_columns] = pivot_data[numeric_columns].fillna(0).astype(int)

    pivot_data = pd.merge(pivot_data, clicks_history, on='page')
    pivot_data = pd.merge(pivot_data, total_clicks, on='page')
    pivot_data = pd.merge(pivot_data, current_month_real_clicks[['page', 'real_clicks_current_month']], on='page', how='left')
    pivot_data = pd.merge(pivot_data, trend, on='page')

    last_month_column = str(pivot_data.columns[-6])
    pivot_data = pivot_data.rename(columns={last_month_column: last_month_column + ' (projected clicks)'})
    return pivot_data

def main():
    page = st.sidebar.selectbox("Choose a page", ["Main page", "Content Decay Overview"])
    if page == "Main page":
        st.title('Main Page')
        st.write('''
        This is the main page of the application. Please select 'Content Decay Overview' from the sidebar
        to upload your Google Search Console data and get insights about the performance of different URLs.
        ''')
    else:
        st.title('Content Decay Overview')
        st.write('''
        ## Welcome to the Content Decay Overview!
        This page helps you understand how the URLs of your website have been performing over time.
        You need to upload a CSV file containing your Google Search Console data. The file must have at
        least three columns: 'page','date' and 'clicks'. Other columns will be ignored.
        ''')

        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            st.write("Processing your data, please wait...")
            data = load_data(uploaded_file)
            st.write("""
            ## Interpreting the results
            The file contains {} URLs/pages.
            From those pages, {} see a strong decline, {} are stable, and {} are showing improvement.
            """.format(len(data['page'].unique()),len(data[data['trend_percentage'] < -10]),len(data[(data['trend_percentage'] >= -10) & (data['trend_percentage'] <= 10)]),len(data[data['trend_percentage'] > 10])))

            st.write("## Trend Overview")
            st.write("This pie chart shows the proportion of pages with declining, stable, and improving trends.")
            st.pyplot(pd.DataFrame([len(data[data['trend_percentage'] < -10]), len(data[(data['trend_percentage'] >= -10) & (data['trend_percentage'] <= 10)]), len(data[data['trend_percentage'] > 10])],index=['Declining', 'Stable', 'Improving'],columns=['count']).plot(kind='pie', y='count', autopct='%1.1f%%', figsize=(5, 5)))

            st.write(f"The average trend of all pages is {data['trend_percentage'].mean()}.")
            st.write('''
            The table below shows:
            - The 'page' column indicates the URL.
            - The clicks accumulated per months in the dataset
            - The last month in the dataset contains the forecasted clicks by the end of it for an ongoing month (based on previous url performance)
            - The 'real_clicks_current_month' column shows the actual number of clicks received in the current month so far.
            - The 'total_clicks' column shows the total number of clicks received by each URL, including forecasted clicks for the ongoing month.
            - The 'trend_percentage' column shows the trend of clicks over time for each URL (expressed as a percentage change per month).
            ''')
            st.dataframe(data.style.applymap(color_gradient, subset=["trend_percentage"]),hide_index=True)

            top_10_pages = data.sort_values(by='total_clicks', ascending=False).head(10)
            st.write("The top 10 pages with the highest total clicks are:")
            st.dataframe(top_10_pages[['page', 'total_clicks', 'trend_percentage']].style.applymap(color_gradient, subset=["trend_percentage"]))

            best_improving_pages = data.sort_values(by='trend_percentage', ascending=False).head(10)
            st.write("The page with the most significant positive trend is:")
            st.dataframe(best_improving_pages[['page', 'total_clicks', 'trend_percentage']].style.applymap(color_gradient, subset=["trend_percentage"]))

            worst_declining_pages = data.sort_values(by='trend_percentage', ascending=True).head(10)
            st.write("The page with the most significant negative trend is:")
            st.dataframe(worst_declining_pages[['page', 'total_clicks', 'trend_percentage']].style.applymap(color_gradient, subset=["trend_percentage"]))

if __name__ == "__main__":
    main()
