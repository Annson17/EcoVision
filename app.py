import os
import streamlit as st
from analysis import validate_and_load_csv, aggregate_data, compute_stats
from forecast import forecast_usage
from insights import generate_efficiency_tips
import pandas as pd
import plotly.express as px
import io
import base64

st.set_page_config(
    page_title="EcoVision Dashboard",
    layout="wide",
    page_icon="https://cdn-icons-png.flaticon.com/512/2909/2909763.png",  # Plant bulb icon
    initial_sidebar_state="expanded"
)

# Custom theme and branding

st.markdown("<style>body {background-color: #f6f8fa;} .stApp {font-family: 'Segoe UI', Arial, sans-serif;} .st-emotion-cache-1v0mbdj {color: #228B22;} .st-emotion-cache-1v0mbdj h1 {color: #228B22;} </style>", unsafe_allow_html=True)

st.title("🌱 EcoVision – Smart Energy Analytics Dashboard")
st.markdown("""
Upload your electricity usage CSV, analyze trends, forecast future consumption, and get AI-powered efficiency tips.
""")


st.sidebar.image("https://img.freepik.com/premium-vector/eco-energy-logo-design-concept_761413-5965.jpg", width=64)

st.sidebar.header("Upload & Settings")
with open("data/electricity_usage_2023_2025.csv", "rb") as f:
    st.sidebar.download_button("Download Sample CSV", f, file_name="electricity_usage_2023_2025.csv", mime="text/csv", help="Download a sample CSV to test the dashboard.")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"], help="Upload your electricity usage data in CSV format.")
forecast_range = st.sidebar.selectbox("Forecast Range", [7, 30], index=0, help="Select the number of days to forecast.")
model_choice = st.sidebar.selectbox("Forecast Model", ["Prophet (default)", "ARIMA (coming soon)"], help="Choose the forecasting model.")

# Reset button
if st.sidebar.button("Reset Dashboard", help="Clear uploaded data and reset dashboard state."):
    # Clear all session state keys
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Explicitly clear file uploader state
    st.session_state["file_uploader"] = None
    st.session_state["uploaded_file"] = None
    st.rerun()

gemini_api_key = st.secrets.get("GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY", None)


# Main
if uploaded_file:
    try:
        df = validate_and_load_csv(uploaded_file)
        st.success("CSV loaded and validated.")
        # --- Large Dataset Optimization ---
        if df.shape[0] > 10000:
            st.warning(f"Large dataset detected ({df.shape[0]} rows). Displaying first 10,000 rows for performance.")
            df = df.head(10000)
        # Caching Gemini calls for repeated questions
        @st.cache_data(show_spinner=False)
        def cached_gemini_insight(question, context, gemini_api_key):
            from insights import get_gemini_insight
            return get_gemini_insight(question, context, gemini_api_key)
        # Data summary
        stats = compute_stats(df)
        from insights import generate_efficiency_tips, get_gemini_insight
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total Usage (kWh)", value=f"{stats['total']:.2f}", help="Sum of all electricity usage in the selected period.")
        with col2:
            st.metric(label="Daily Avg (kWh)", value=f"{stats.get('average_daily_actual', stats.get('average_daily', stats['average'])):.2f}", help="Average daily usage (actual, based on unique days in data).")
        with col3:
            st.metric(label="Weekly Avg (kWh)", value=f"{stats.get('average_weekly_actual', stats.get('average_weekly', 0)):.2f}", help="Average weekly usage (actual, based on unique weeks in data).")
        with col4:
            st.metric(label="Monthly Avg (kWh)", value=f"{stats.get('average_monthly_actual', stats.get('average_monthly', 0)):.2f}", help="Average monthly usage (actual, based on unique months in data).")
        if 'average_yearly_actual' in stats:
            st.metric(label="Yearly Avg (kWh)", value=f"{stats['average_yearly_actual']:.2f}", help="Average yearly usage (actual, based on unique years in data).")
        with st.expander("📊 Usage Analysis & Trends", expanded=True):
            agg_freq = st.radio("Aggregate by", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True, help="Choose how to group your usage data for analysis.")
            freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Yearly": "Y"}
            # Date range filter
            min_date, max_date = df['date'].min(), df['date'].max()
            date_range = st.date_input("Filter by date range", [min_date, max_date], min_value=min_date, max_value=max_date, help="Select the date range to analyze.")
            filtered_df = df[(df['date'] >= pd.to_datetime(date_range[0])) & (df['date'] <= pd.to_datetime(date_range[1]))]
            agg_df = aggregate_data(filtered_df, freq=freq_map[agg_freq])
            fig = px.line(
                agg_df,
                x='date',
                y='usage_kWh',
                title=f"Electricity Usage ({agg_freq})",
                color_discrete_sequence=["#64ffda"],
                labels={"date": "Date", "usage_kWh": "Usage (kWh)"},
                markers=True
            )
            fig.update_layout(xaxis_title='Date', yaxis_title='Usage (kWh)', legend_title_text='Legend')
            st.plotly_chart(fig, use_container_width=True, key="usage_analysis_chart_main")
            # Comparison chart
            st.markdown("#### Comparison Chart")
            # Dynamically determine available comparison options
            compare_options = []
            n_years = pd.to_datetime(filtered_df['date']).dt.year.nunique()
            n_months = pd.to_datetime(filtered_df['date']).dt.month.nunique()
            n_weeks = pd.to_datetime(filtered_df['date']).dt.isocalendar().week.nunique()
            n_days = filtered_df['date'].nunique()
            if n_years > 1:
                compare_options.append("Year-over-Year")
            if n_months > 1:
                compare_options.append("Month-over-Month")
            if n_weeks > 1:
                compare_options.append("Week-over-Week")
            if n_days > 1:
                compare_options.append("Day-over-Day")
            if not compare_options:
                st.info("Not enough data for comparison charts.")
            else:
                compare_type = st.selectbox("Compare", compare_options, help="Select comparison type.")
                if compare_type == "Year-over-Year":
                    filtered_df['year'] = pd.to_datetime(filtered_df['date']).dt.year
                    yoy_df = filtered_df.groupby(['year'])['usage_kWh'].sum().reset_index().sort_values('year')
                    if yoy_df.shape[0] > 1:
                        yoy_fig = px.bar(yoy_df, x='year', y='usage_kWh', title="Year-over-Year Comparison", labels={"year": "Year", "usage_kWh": "Usage (kWh)"})
                        st.plotly_chart(yoy_fig, use_container_width=True, key="yoy_chart")
                    else:
                        st.info("Not enough years for year-over-year comparison.")
                # --- AI Chat & Reporting Sidebar ---
                st.sidebar.markdown("---")
                st.sidebar.subheader("AI Chat & Reporting")
                chat_history = st.session_state.get("chat_history", [])
                user_question = st.sidebar.text_area("Ask Gemini about your data:", "", key="ai_chat_input")
                if st.sidebar.button("Send", key="ai_chat_send"):
                    if user_question.strip():
                        with st.spinner("Gemini is thinking..."):
                            # Pass the current dataframe if available
                            if isinstance(df, pd.DataFrame) and not df.empty:
                                context = df.head(100).to_csv(index=False)  # Limit context for performance
                            else:
                                context = "No data uploaded."
                            try:
                                ai_response = get_gemini_insight(user_question, context, gemini_api_key)
                            except Exception as e:
                                ai_response = f"Error: {e}"
                            chat_history.append((user_question, ai_response))
                            st.session_state["chat_history"] = chat_history
                if chat_history:
                    st.sidebar.markdown("#### Chat History")
                    for q, a in reversed(chat_history[-5:]):
                        st.sidebar.markdown(f"**You:** {q}")
                        st.sidebar.markdown(f"**Gemini:** {a}")
                elif compare_type == "Month-over-Month":
                    filtered_df['month'] = pd.to_datetime(filtered_df['date']).dt.month
                    mom_df = filtered_df.groupby(['month'])['usage_kWh'].sum().reset_index().sort_values('month')
                    if mom_df.shape[0] > 1:
                        mom_fig = px.bar(mom_df, x='month', y='usage_kWh', title="Month-over-Month Comparison", labels={"month": "Month", "usage_kWh": "Usage (kWh)"})
                        st.plotly_chart(mom_fig, use_container_width=True, key="mom_chart")
                    else:
                        st.info("Not enough months for month-over-month comparison.")
                elif compare_type == "Week-over-Week":
                    filtered_df['week'] = pd.to_datetime(filtered_df['date']).dt.isocalendar().week
                    wow_df = filtered_df.groupby(['week'])['usage_kWh'].sum().reset_index().sort_values('week')
                    if wow_df.shape[0] > 1:
                        wow_fig = px.bar(wow_df, x='week', y='usage_kWh', title="Week-over-Week Comparison", labels={"week": "Week", "usage_kWh": "Usage (kWh)"})
                        st.plotly_chart(wow_fig, use_container_width=True, key="wow_chart")
                    else:
                        st.info("Not enough weeks for week-over-week comparison.")
                elif compare_type == "Day-over-Day":
                    dod_df = filtered_df.groupby(['date'])['usage_kWh'].sum().reset_index().sort_values('date')
                    if dod_df.shape[0] > 1:
                        dod_fig = px.line(dod_df, x='date', y='usage_kWh', title="Day-over-Day Comparison", labels={"date": "Date", "usage_kWh": "Usage (kWh)"})
                        st.plotly_chart(dod_fig, use_container_width=True, key="dod_chart")
                    else:
                        st.info("Not enough days for day-over-day comparison.")
            # ...existing code...

        # Forecast in expander
        with st.expander("📈 Forecast", expanded=True):
            future, forecast = forecast_usage(df, periods=forecast_range)
            forecast_fig = px.line(
                forecast,
                x='ds',
                y='yhat',
                title=f"Forecasted Usage ({forecast_range} days)",
                color_discrete_sequence=["#64ffda"],
                labels={"ds": "Date", "yhat": "Forecasted Usage (kWh)"}
            )
            forecast_fig.add_scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', name='Lower Bound', line=dict(dash='dot', color='#87CEEB'))
            forecast_fig.add_scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', name='Upper Bound', line=dict(dash='dot', color='#87CEEB'))
            forecast_fig.update_layout(legend_title_text='Legend', xaxis_title='Date', yaxis_title='Usage (kWh)')
            st.plotly_chart(forecast_fig, use_container_width=True, key="forecast_chart")
            overlay_fig = px.line(
                df,
                x='date',
                y='usage_kWh',
                title="Actual vs Forecasted Usage",
                color_discrete_sequence=["#64ffda"],
                labels={"date": "Date", "usage_kWh": "Actual Usage (kWh)"}
            )
            overlay_fig.add_scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Forecast', line=dict(color='#1E90FF'))
            overlay_fig.update_layout(xaxis_title='Date', yaxis_title='Usage (kWh)', legend_title_text='Legend')
            st.plotly_chart(overlay_fig, use_container_width=True, key="actual_vs_forecast_chart")

        # AI Insights in expander with spinner
        with st.expander("🤖 AI Efficiency Insights & Recommendations (Gemini)", expanded=True):
            activate_ai = st.checkbox("Activate AI Recommendations (uses API call)", value=False, help="Enable to generate personalized tips using Gemini AI.")
            if activate_ai:
                with st.spinner("Generating personalized recommendations..."):
                    tips = generate_efficiency_tips(df, gemini_api_key)
                if tips and all("unavailable" not in tip.lower() for tip in tips):
                    st.markdown("**Personalized Recommendations:**")
                    for tip in tips:
                        st.markdown(f"- {tip}")
                else:
                    st.info(tips[0] if tips else "AI insights unavailable.")
            else:
                st.info("AI recommendations are disabled. Check the box above to activate.")
            # --- Export and Sharing Features ---
            st.markdown("---")
            st.subheader("Export & Share")
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                if st.button("Export Dashboard as PDF", key="export_pdf_btn"):
                    st.info("PDF export coming soon. For now, use browser print to PDF.")
                if st.button("Export Chart as Image", key="export_img_btn"):
                    st.info("Image export coming soon. For now, right-click chart to save as image.")
            with export_col2:
                email = st.text_input("Share via Email", "", help="Enter email to send report.")
                if st.button("Send Report", key="send_email_btn"):
                    st.info(f"Report sharing to {email} coming soon.")
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload a CSV file to begin.")

st.markdown("---")
st.markdown("© 2025 EcoVision – Smart Energy Analytics Dashboard")
