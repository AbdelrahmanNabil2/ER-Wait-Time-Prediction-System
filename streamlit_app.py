import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="ER Wait Time Predictor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .risk-low {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #28a745;
    }
    .risk-medium {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #ffc107;
    }
    .risk-high {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #dc3545;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

API_URL = "http://localhost:8000"

def check_api_status():
    try:
        response = requests.get(f"{API_URL}/healthz", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_prediction(patient_data):
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=patient_data,
            timeout=10
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"API Error: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API. Make sure the FastAPI server is running on port 8000."
    except Exception as e:
        return None, f"Error: {str(e)}"

def create_gauge_chart(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=250)
    return fig

def create_wait_time_chart(lower, median, upper):
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Lower Bound (25%)', 'Median (50%)', 'Upper Bound (75%)'],
        y=[lower, median, upper],
        marker_color=['#28a745', '#ffc107', '#dc3545'],
        text=[f"{lower:.0f} min", f"{median:.0f} min", f"{upper:.0f} min"],
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Wait Time Prediction Interval",
        yaxis_title="Wait Time (minutes)",
        showlegend=False,
        height=400
    )
    
    return fig

def main():
    st.markdown('<div class="main-header">ER Wait Time Predictor</div>', unsafe_allow_html=True)
    
    api_status = check_api_status()
    
    if not api_status:
        st.error("API Server is not running!")
        st.info("Please start the FastAPI server first by running:\n```bash\npython main.py\n```")
        st.stop()
    else:
        st.success("API Server is running")
    
    st.sidebar.header("Patient Information")
    
    col1, col2 = st.sidebar.columns(2)
    
    if 'default_date' not in st.session_state:
        st.session_state.default_date = datetime.now().date()
    if 'default_time' not in st.session_state:
        st.session_state.default_time = datetime.now().time()
    
    with col1:
        arrival_date = st.date_input(
            "Arrival Date",
            value=st.session_state.default_date,
            key="arrival_date_input",
            help="Date of patient arrival"
        )
    
    with col2:
        arrival_time = st.time_input(
            "Arrival Time",
            value=st.session_state.default_time,
            key="arrival_time_input",
            help="Time of patient arrival"
        )
    
    arrival_datetime = datetime.combine(arrival_date, arrival_time)
    arrival_str = arrival_datetime.strftime("%Y-%m-%d %H:%M:%S")
    
    triage_level = st.sidebar.slider(
        "Triage Level",
        min_value=1,
        max_value=5,
        value=3,
        help="1 = Most Urgent, 5 = Least Urgent"
    )
    
    age = st.sidebar.number_input(
        "Patient Age",
        min_value=0,
        max_value=120,
        value=45,
        help="Age of the patient"
    )
    
    department = st.sidebar.selectbox(
        "Department",
        options=["General", "Cardiac", "Pediatric", "Trauma"],
        help="Emergency department type"
    )
    
    num_doctors = st.sidebar.slider(
        "Doctors Available",
        min_value=1,
        max_value=20,
        value=5,
        help="Number of doctors currently on duty"
    )
    
    queue_length = st.sidebar.slider(
        "Queue Length",
        min_value=0,
        max_value=100,
        value=12,
        help="Number of patients in queue"
    )
    
    is_weekend = st.sidebar.checkbox(
        "Weekend",
        value=arrival_date.weekday() >= 5,
        help="Is it a weekend?"
    )
    
    predict_button = st.sidebar.button("Predict Wait Time", use_container_width=True)
    
    if predict_button:
        patient_data = {
            "arrival_time": arrival_str,
            "triage_level": triage_level,
            "age": age,
            "department": department,
            "num_doctors_available": num_doctors,
            "queue_length": queue_length,
            "is_weekend": 1 if is_weekend else 0
        }
        
        with st.expander("Input Summary", expanded=False):
            st.json(patient_data)
        
        with st.spinner("Analyzing patient data..."):
            result, error = get_prediction(patient_data)
        
        if error:
            st.error(f"{error}")
        elif result:
            st.markdown("---")
            st.subheader("Prediction Results")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Predicted Wait Time",
                    value=f"{result['predicted_wait_time']:.0f} min",
                    delta=None
                )
            
            with col2:
                prob_percent = result['long_wait_probability'] * 100
                st.metric(
                    label="Long Wait Probability",
                    value=f"{prob_percent:.1f}%",
                    delta=None
                )
            
            with col3:
                st.metric(
                    label="Risk Level",
                    value=result['risk_level'],
                    delta=None
                )
            
            with col4:
                long_wait_text = "Yes" if result['is_long_wait'] else "No"
                st.metric(
                    label="Long Wait (>60 min)",
                    value=long_wait_text,
                    delta=None
                )
            
            st.markdown("---")
            risk_level = result['risk_level']
            
            if risk_level == "LOW":
                st.markdown(f"""
                <div class="risk-low">
                    <h3>LOW RISK</h3>
                    <p>Expected wait time is relatively short. Patient should be seen soon.</p>
                </div>
                """, unsafe_allow_html=True)
            elif risk_level == "MEDIUM":
                st.markdown(f"""
                <div class="risk-medium">
                    <h3>MEDIUM RISK</h3>
                    <p>Moderate wait expected. Monitor patient condition and queue status.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="risk-high">
                    <h3>HIGH RISK</h3>
                    <p>Long wait time expected. Consider resource allocation or patient management.</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                interval = result['prediction_interval']
                fig_wait = create_wait_time_chart(
                    interval['lower_bound_25th'],
                    interval['median_50th'],
                    interval['upper_bound_75th']
                )
                st.plotly_chart(fig_wait, use_container_width=True)
            
            with col2:
                prob_percent = result['long_wait_probability'] * 100
                fig_gauge = create_gauge_chart(
                    prob_percent,
                    "Long Wait Probability (%)"
                )
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Prediction Interval Analysis")
            
            interval_data = {
                "Percentile": ["25th (Lower Bound)", "50th (Median)", "75th (Upper Bound)"],
                "Wait Time (minutes)": [
                    interval['lower_bound_25th'],
                    interval['median_50th'],
                    interval['upper_bound_75th']
                ],
                "Interpretation": [
                    "25% of similar cases wait less than this",
                    "Median wait time for similar cases",
                    "75% of similar cases wait less than this"
                ]
            }
            
            df_interval = pd.DataFrame(interval_data)
            st.dataframe(df_interval, use_container_width=True, hide_index=True)
            
            st.info(f"{interval['interpretation']}")
            
            if not interval['using_quantile_models']:
                st.warning("Using estimated intervals (quantile models not loaded)")
            
            st.markdown("---")
            st.subheader("Patient Context")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Triage Level:** {result['patient_info']['triage_level']}")
            with col2:
                st.write(f"**Department:** {result['patient_info']['department']}")
            with col3:
                st.write(f"**Queue Position:** #{result['patient_info']['queue_position']}")
            
            with st.expander("View Full API Response", expanded=False):
                st.json(result)
    
    else:
        st.info("Please fill in the patient information in the sidebar and click 'Predict Wait Time'")
        
        st.markdown("---")
        st.subheader("Example Use Case")
        
        st.write("""
        This application predicts emergency room wait times based on:
        - **Patient factors**: Age, triage level
        - **Department factors**: Available doctors, queue length
        - **Temporal factors**: Time of day, day of week, weekend status
        
        The prediction includes:
        - Expected wait time in minutes
        - Probability of long wait (>60 minutes)
        - Risk level classification
        - Prediction intervals with uncertainty quantification
        """)
        
        try:
            response = requests.get(f"{API_URL}/models", timeout=5)
            if response.status_code == 200:
                model_info = response.json()
                
                st.markdown("---")
                st.subheader("Model Information")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Model Version:** {model_info.get('model_version', 'N/A')}")
                    st.write(f"**Training Date:** {model_info.get('training_date', 'N/A')}")
                    st.write(f"**Features Used:** {model_info.get('feature_count', 'N/A')}")
                
                with col2:
                    metrics = model_info.get('metrics', {})
                    if metrics:
                        st.write("**Model Performance:**")
                        for key, value in metrics.items():
                            if isinstance(value, (int, float)):
                                st.write(f"- {key}: {value:.3f}")
                            else:
                                st.write(f"- {key}: {value}")
        except:
            pass

    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666;'>
            <p>ER Wait Time Predictor v1.0.0 | Powered by XGBoost & FastAPI</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
