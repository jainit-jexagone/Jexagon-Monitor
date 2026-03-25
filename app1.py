import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. PAGE SETUP
st.set_page_config(
    page_title="Smart Factory", 
    layout="wide"
)

# CSS to hide Streamlit elements
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    .viewerBadge_container__1QS13 {display: none !important;}
    div.stDeployButton {display:none;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

LOG_FILE = "motor_logs.csv"
MQTT_BROKER = "mqtt.eclipseprojects.io"
MQTT_TOPIC = "janit/motor/data"

# 2. INITIALIZE SESSION STATE (At the very beginning)
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0
if 'new_data_arrived' not in st.session_state: st.session_state.new_data_arrived = False

if 'history' not in st.session_state:
    # Try to load existing data from CSV on startup
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE)
            st.session_state.history = df
        except:
            st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
    else:
        st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])

# ૧. આ ફંક્શનને બરાબર આ રીતે અપડેટ કરો
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        # આ વેલ્યુ સીધી સેશનમાં સેવ કરો
        st.session_state.temp = float(data.get('temp', 0))
        st.session_state.sound = float(data.get('sound', 0))
        st.session_state.new_data_arrived = True 
        
        # ટર્મિનલમાં ચેક કરવા માટે (ઓનરને નહીં દેખાય)
        print(f"MQTT Received: {payload}")
    except Exception as e:
        print(f"Error Decoding: {e}")

# ૨. MQTT કનેક્શનમાં 'KeepAlive' વધારી દો
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    
    # સુરક્ષિત કનેક્શન
    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.subscribe(MQTT_TOPIC)
        client.loop_start()
        st.session_state.mqtt_client = client
    except Exception as e:
        st.error(f"MQTT Connection Error: {e}")
# 4. DATA PROCESSING
def save_data():
    now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
    temp = st.session_state.temp
    sound = st.session_state.sound
    
    new_row = pd.DataFrame([[now, temp, sound]], 
                            columns=['Date-time', 'Temperature', 'sound_level'])
    
    # Update Session State
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    # Save to CSV
    new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

if st.session_state.new_data_arrived:
    save_data()
    st.session_state.new_data_arrived = False

# 5. UI LAYOUT
st.title("🏭 Smart Factory Dashboard")
st.write("Motor Monitoring and Vibration Analysis System")

# Sidebar Configuration
st.sidebar.header("Settings")
points = st.sidebar.slider("Points to show on graph", 5, 200, 20)
user_phone = st.sidebar.text_input("Worker Contact", value="+91")

# 6. DASHBOARD LOGIC
if not st.session_state.history.empty:
    display_data = st.session_state.history.tail(points)
    last_temp = display_data['Temperature'].iloc[-1]
    last_sound = display_data['sound_level'].iloc[-1]

    # Alerts & Safety Logic
    TEMP_LIMIT = 70.0
    SOUND_LIMIT = 85.0 

    if last_temp > TEMP_LIMIT:
        st.error(f"🚨 CRITICAL ALERT: Motor Overheating! ({last_temp}°C)")
        # Alarm sound
        st.components.v1.html("<audio autoplay><source src='https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg' type='audio/ogg'></audio>", height=0)
    elif last_sound > SOUND_LIMIT:
        st.warning(f"⚠️ WARNING: High Noise Level Detected! ({last_sound}dB)")
    else:
        st.success(f"✅ System Healthy: Operating within normal parameters.")

    # Display Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("🌡️ Temperature", f"{last_temp}°C")
    with col2: st.metric("📈 Max Temp (Session)", f"{display_data['Temperature'].max()}°C")
    with col3: st.metric("📉 Min Temp (Session)", f"{display_data['Temperature'].min()}°C")
    with col4: st.metric("🔊 Sound level", f"{last_sound}dB")

    # Main Performance Graph
    st.subheader("📊 Real-time Performance Graph")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['Temperature'], mode='lines+markers', name='Temp (°C)', line=dict(color='#FF4B4B', width=3)))
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['sound_level'], mode='lines', name='Sound (dB)', line=dict(color='#1C83E1', width=2, dash='dot')))
    fig.update_layout(template='plotly_dark', xaxis_title='Timestamp', yaxis_title='Reading', hovermode='x unified', height=500)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⌛ Waiting for data from sensors... Please ensure the motor is running and sending MQTT data.")

# 7. HISTORICAL REPORT SECTION
st.markdown("---")
st.header("🔍 Historical Data Report")
selected_date = st.date_input("Select Date", value=datetime.now())

if st.button("Generate Report"):
    if os.path.exists(LOG_FILE):
        df_h = pd.read_csv(LOG_FILE)
        # Fix date parsing to be robust
        df_h['Date-time'] = pd.to_datetime(df_h['Date-time'], format='%d/%m/%Y | %H:%M:%S', errors='coerce')
        df_h = df_h.dropna(subset=['Date-time'])
        
        filtered_data = df_h[df_h['Date-time'].dt.date == selected_date]
        
        if not filtered_data.empty:
            st.success(f"Report for {selected_date}")
            fig_rep = go.Figure()
            fig_rep.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['Temperature'], name='Temp'))
            fig_rep.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['sound_level'], name='Sound'))
            fig_rep.update_layout(template='plotly_dark')
            st.plotly_chart(fig_rep, use_container_width=True)
            
            st.download_button("📥 Download CSV", data=filtered_data.to_csv(index=False), file_name=f"report_{selected_date}.csv")
        else:
            st.warning("No data found for this date.")
    else:
        st.error("No log file found.")

# 8. AUTO-REFRESH
st.markdown("---")
st.write(f"🕒 **Last Sync: {datetime.now().strftime('%H:%M:%S')}**")
time.sleep(2)
st.rerun()
