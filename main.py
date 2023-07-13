
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
    data.columns = map(str.lower, data.columns)  # convert all column names to lowercase
    
    page_variants = ['address', 'adresse', 'url']
    for variant in page_variants:
        if variant in data.columns:
            data = data.rename(columns={variant: 'page'})
    
    required_columns = ['date', 'clicks', 'page']
    if not set(required_columns).issubset(data.columns):
        raise ValueError(f"The CSV file must contain the following columns: {required_columns}")

    data['date'] = pd.to_datetime(data['date'])
    data['month_year'] = data['date'].dt.to_period('M')

    # Group by page and month_year, and calculate the sum of clicks
    grouped_data = data.groupby(['page', 'month_year'])['clicks'].sum().reset_index()
    grouped_data['clicks'] = grouped_data['clicks'].round(0).astype(int)
    
    # Estimate clicks for the full current month
    last_month = grouped_data['month_year'].max()
    days_passed = (pd.Timestamp.now() - pd.Timestamp(last_month.start_time)).days
    total_days = monthrange(last_month.start_time.year, last_month.start_time.month)[1]
    current_month_real_clicks = grouped_data[grouped_data['month_year'] == last_month].copy()
    current_month_real_clicks.columns = ['page', 'month_year', 'real_clicks_current_month']
    grouped_data.loc[grouped_data['month_year'] == last_month, 'clicks'] = (grouped_data['clicks'] / days_passed * total_days).round(0).astype(int)

    # Create a column with clicks history for each page using projected clicks
    clicks_history = grouped_data.groupby('page')['clicks'].apply(list).reset_index()
    clicks_history.columns = ['page', 'clicks_history']
    
    # Calculate the total clicks for each page
    total_clicks = grouped_data.groupby('page')['clicks'].sum().reset_index()
    total_clicks.columns = ['page', 'total_clicks']
    
    # Calculate the trend for each page as percentage change
    trend = grouped_data.groupby('page').apply(lambda x: LinearRegression().fit(np.arange(len(x)).reshape(-1, 1), x['clicks'].values).coef_[0] / x['clicks'].mean() * 100).reset_index()
    trend.columns = ['page', 'trend_percentage']
    trend['trend_percentage'] = trend['trend_percentage'].round(1)
    
    # Create a pivot table with pages as rows and months as columns
    pivot_data = grouped_data.pivot(index='page', columns='month_year', values='clicks').reset_index()
    numeric_columns = pivot_data.select_dtypes(include=[np.number]).columns
    pivot_data[numeric_columns] = pivot_data[numeric_columns].fillna(0).astype(int)
    
    # Merge the pivot table with clicks history, total clicks, real clicks of current month and trend
    pivot_data = pd.merge(pivot_data, clicks_history, on='page')
    pivot_data = pd.merge(pivot_data, total_clicks, on='page')
    pivot_data = pd.merge(pivot_data, current_month_real_clicks[['page', 'real_clicks_current_month']], on='page', how='left')
    pivot_data = pd.merge(pivot_data, trend, on='page')

    # Rename the last month column
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
        You need to upload a CSV file containing your Google Search Console data. The file should have at 
        least two columns: 'date' and 'clicks'. Other columns will be ignored.
        ''')
        
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            st.write("Processing your data, please wait...")
            data = load_data(uploaded_file)

            st.write('''
            ## Interpreting the results
            URLs with a green trend have seen an increase in clicks over time, 
            while those with a red trend have seen a decrease. URLs with a yellow trend 
            are stable, i.e., their number of clicks has not changed significantly over time.
            ''')
            st.write('''
            The table below shows:
            - The 'page' column indicates the URL.
            - The 'clicks_history' column shows a line chart of clicks over time for each URL.
            - The 'total_clicks' column shows the total number of clicks received by each URL.
            - The 'real_clicks_current_month' column shows the actual number of clicks received in the current month.
            - The 'trend_percentage' column shows the trend of clicks over time for each URL (expressed as a percentage change per period).
            ''')
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
            total_pages = len(data['page'].unique())
            improving_pages = len(data[data['trend_percentage'] > 10])
            stable_pages = len(data[(data['trend_percentage'] >= -10) & (data['trend_percentage'] <= 10)])
            declining_pages = len(data[data['trend_percentage'] < -10])

            st.write(f"We analyzed a total of {total_pages} URLs/pages.")
            st.write(f"From those pages, {declining_pages} see a strong decline, {stable_pages} are stable, and {improving_pages} are showing improvement.")
            average_trend = round(data['trend_percentage'].mean(), 1)
trend_message = "declining" if average_trend < 0 else "increasing" if average_trend > 0 else "stable"
st.write(f"The average trend of all pages is {average_trend}%, which means the overall clicks of all the pages are {trend_message} by {abs(average_trend)}% every month.")
st.write("Here is a histogram of the trends for all pages:")
fig, ax = plt.subplots()
ax.hist(data['trend_percentage'], bins=30, color='skyblue', alpha=0.7)
ax.set_title('Histogram of Trends')
ax.set_xlabel('Trend Percentage')
ax.set_ylabel('Number of Pages')
st.pyplot(fig)

top_10_pages = data.sort_values(by='total_clicks', ascending=False).head(10)
            st.write("The top 10 pages with the highest total clicks are:")
            st.dataframe(top_10_pages[['page', 'total_clicks', 'trend_percentage']].style.applymap(color_gradient, subset=["trend_percentage"]), column_config={ "clicks_history": st.column_config.LineChartColumn("Clicks over time") })

            best_improving_pages = data.sort_values(by='trend_percentage', ascending=False).head(10)
            st.write("The page with the most significant positive trend is:")
            st.dataframe(best_improving_pages[['page', 'total_clicks', 'trend_percentage']].style.applymap(color_gradient, subset=["trend_percentage"]), column_config={ "clicks_history": st.column_config.LineChartColumn("Clicks over time") })

            worst_declining_pages = data.sort_values(by='trend_percentage', ascending=True).head(10)
            st.write("The page with the most significant negative trend is:")
            st.dataframe(worst_declining_pages[['page', 'total_clicks', 'trend_percentage']].style.applymap(color_gradient, subset=["trend_percentage"]), column_config={ "clicks_history": st.column_config.LineChartColumn("Clicks over time") })

         
if __name__ == "__main__":
    main()
