import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Scenario Comparison", page_icon="", layout="wide")

st.title("Scenario Comparison Tool")

API_URL = "http://localhost:8000"

SCENARIOS = {
    "Best Case - Quick Visit": {
        "arrival_time": "2024-03-15 10:00:00",
        "triage_level": 1,
        "age": 35,
        "department": "General",
        "num_doctors_available": 10,
        "queue_length": 5,
        "is_weekend": 0
    },
    "Average - Normal Day": {
        "arrival_time": "2024-03-15 14:30:00",
        "triage_level": 3,
        "age": 45,
        "department": "General",
        "num_doctors_available": 5,
        "queue_length": 12,
        "is_weekend": 0
    },
    "Busy - Weekend Evening": {
        "arrival_time": "2024-03-16 18:30:00",
        "triage_level": 4,
        "age": 65,
        "department": "General",
        "num_doctors_available": 3,
        "queue_length": 30,
        "is_weekend": 1
    },
    "Worst Case - Overcrowded": {
        "arrival_time": "2024-03-16 02:00:00",
        "triage_level": 5,
        "age": 75,
        "department": "General",
        "num_doctors_available": 2,
        "queue_length": 50,
        "is_weekend": 1
    },
    "Rush Hour Peak": {
        "arrival_time": "2024-03-15 18:00:00",
        "triage_level": 4,
        "age": 55,
        "department": "General",
        "num_doctors_available": 4,
        "queue_length": 25,
        "is_weekend": 0
    },
    "Critical - Understaffed": {
        "arrival_time": "2024-03-15 03:00:00",
        "triage_level": 2,
        "age": 70,
        "department": "General",
        "num_doctors_available": 1,
        "queue_length": 40,
        "is_weekend": 1
    }
}

def get_prediction(data):
    try:
        response = requests.post(f"{API_URL}/predict", json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

st.sidebar.header("Select Scenarios to Compare")
selected_scenarios = st.sidebar.multiselect("Choose scenarios", list(SCENARIOS.keys()), default=list(SCENARIOS.keys())[:3])

if st.sidebar.button("Run Comparison", type="primary"):
    if not selected_scenarios:
        st.warning("Please select at least one scenario")
    else:
        results = []
        with st.spinner("Running predictions..."):
            for scenario_name in selected_scenarios:
                scenario_data = SCENARIOS[scenario_name]
                result = get_prediction(scenario_data)
                if result:
                    results.append({
                        'Scenario': scenario_name,
                        'Wait Time (min)': result['predicted_wait_time'],
                        'Risk Level': result['risk_level'],
                        'Long Wait Prob (%)': round(result['long_wait_probability'] * 100, 1),
                        'Lower Bound': result['prediction_interval']['lower_bound_25th'],
                        'Median': result['prediction_interval']['median_50th'],
                        'Upper Bound': result['prediction_interval']['upper_bound_75th'],
                        'Triage': scenario_data['triage_level'],
                        'Queue': scenario_data['queue_length'],
                        'Doctors': scenario_data['num_doctors_available'],
                        'Time': scenario_data['arrival_time'].split()[1][:5]
                    })
        if results:
            df = pd.DataFrame(results)
            st.subheader("Comparison Summary")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Min Wait Time", f"{df['Wait Time (min)'].min():.1f} min")
            with col2:
                st.metric("Max Wait Time", f"{df['Wait Time (min)'].max():.1f} min")
            with col3:
                st.metric("Average", f"{df['Wait Time (min)'].mean():.1f} min")
            with col4:
                variance = df['Wait Time (min)'].max() - df['Wait Time (min)'].min()
                st.metric("Range", f"{variance:.1f} min")
            if variance < 5:
                st.warning("Low Prediction Variance Detected!")
                st.info("The model is showing very similar predictions across different scenarios.")
            st.markdown("---")
            st.subheader("Detailed Comparison")
            def color_risk(val):
                if val == 'LOW':
                    return 'background-color: #d4edda'
                elif val == 'MEDIUM':
                    return 'background-color: #fff3cd'
                else:
                    return 'background-color: #f8d7da'
            styled_df = df.style.applymap(color_risk, subset=['Risk Level'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            st.markdown("---")
            st.subheader("Visual Comparisons")
            col1, col2 = st.columns(2)
            with col1:
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(x=df['Scenario'], y=df['Wait Time (min)'], name='Predicted Wait Time', marker_color='rgb(55, 83, 109)', text=df['Wait Time (min)'].round(1), textposition='auto'))
                fig1.update_layout(title="Wait Time Comparison", xaxis_title="Scenario", yaxis_title="Wait Time (minutes)", height=400)
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = go.Figure()
                for idx, row in df.iterrows():
                    fig2.add_trace(go.Box(y=[row['Lower Bound'], row['Median'], row['Upper Bound']], name=row['Scenario'][:20], boxmean='sd'))
                fig2.update_layout(title="Prediction Intervals (25th-75th percentile)", yaxis_title="Wait Time (minutes)", showlegend=False, height=400)
                st.plotly_chart(fig2, use_container_width=True)
            st.markdown("---")
            st.subheader("Feature Impact Analysis")
            col1, col2 = st.columns(2)
            with col1:
                fig3 = px.scatter(df, x='Queue', y='Wait Time (min)', size='Doctors', color='Risk Level', hover_data=['Scenario'], title="Queue Length vs Wait Time", labels={'Queue': 'Queue Length', 'Wait Time (min)': 'Wait Time (minutes)'})
                st.plotly_chart(fig3, use_container_width=True)
            with col2:
                fig4 = px.scatter(df, x='Triage', y='Wait Time (min)', size='Queue', color='Risk Level', hover_data=['Scenario'], title="Triage Level vs Wait Time", labels={'Triage': 'Triage Level', 'Wait Time (min)': 'Wait Time (minutes)'})
                st.plotly_chart(fig4, use_container_width=True)
            st.markdown("---")
            st.subheader("Risk Distribution")
            risk_counts = df['Risk Level'].value_counts()
            fig5 = go.Figure(data=[go.Pie(labels=risk_counts.index, values=risk_counts.values, marker_colors=['#28a745', '#ffc107', '#dc3545'])])
            fig5.update_layout(title="Risk Level Distribution", height=400)
            st.plotly_chart(fig5, use_container_width=True)
            st.markdown("---")
            csv = df.to_csv(index=False)
            st.download_button(label="Download Comparison as CSV", data=csv, file_name=f"scenario_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
            st.markdown("---")
            st.subheader("Insights and Recommendations")
            best_idx = df['Wait Time (min)'].idxmin()
            worst_idx = df['Wait Time (min)'].idxmax()
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"**Best Scenario:** {df.loc[best_idx, 'Scenario']}")
                st.write(f"- Wait Time: {df.loc[best_idx, 'Wait Time (min)']:.1f} minutes")
                st.write(f"- Queue: {df.loc[best_idx, 'Queue']} patients")
                st.write(f"- Doctors: {df.loc[best_idx, 'Doctors']}")
            with col2:
                st.error(f"**Worst Scenario:** {df.loc[worst_idx, 'Scenario']}")
                st.write(f"- Wait Time: {df.loc[worst_idx, 'Wait Time (min)']:.1f} minutes")
                st.write(f"- Queue: {df.loc[worst_idx, 'Queue']} patients")
                st.write(f"- Doctors: {df.loc[worst_idx, 'Doctors']}")
        else:
            st.error("Failed to get predictions from API")
else:
    st.info("Select scenarios from the sidebar and click 'Run Comparison' to start")
    st.subheader("Available Test Scenarios")
    for name, data in SCENARIOS.items():
        with st.expander(f"{name}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Triage:** {data['triage_level']}")
                st.write(f"**Age:** {data['age']}")
                st.write(f"**Time:** {data['arrival_time'].split()[1]}")
            with col2:
                st.write(f"**Queue:** {data['queue_length']}")
                st.write(f"**Doctors:** {data['num_doctors_available']}")
                st.write(f"**Weekend:** {'Yes' if data['is_weekend'] else 'No'}")
            with col3:
                st.write(f"**Department:** {data['department']}")
