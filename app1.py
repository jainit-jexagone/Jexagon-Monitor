import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="Smart Factory", layout="wide")

# CSS to hide header/footer
hide_style = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_style, unsafe_allow_html=True)

LOG_FILE = "motor_logs.csv"
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "janit/motor/data"

# 2. INITIALIZE SESSION STATE (Run only once)
if 'history' not in st.session_state:
    if os.path.exists(LOG_FILE):
        try:
            st.session_state.history = pd.read_csv(LOG_FILE)
        except:
            st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
    else:
        st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])

if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0
if 'new_data_arrived' not in st.session_state: st.session_state.new_data_arrived = False

# 3. MQTT CALLBACK FUNCTIONS
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        # Update session state values
        st.session_state.temp = float(data.get('temp', 0))
        st.session_state.sound = float(data.get('sound', 0))
        st.session_state.new_data_arrived = True
    except Exception as e:
        print(f"MQTT Error: {e}")

# 4. MQTT CLIENT SETUP
if 'mqtt_client' not in st.session_state:
    # Use CallbackAPIVersion.VERSION2 for newer paho-mqtt versions
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except:
        client = mqtt.Client() # Fallback for older versions
        
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    st.session_state.mqtt_client = client

# 5. DATA SAVING LOGIC
if st.session_state.new_data_arrived:
    now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
    temp = st.session_state.temp
    sound = st.session_state.sound
    
    new_row = pd.DataFrame([[now, temp, sound]], columns=['Date-time', 'Temperature', 'sound_level'])
    
    # Update local CSV
    new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))
    
    # Update session state history
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    st.session_state.new_data_arrived = False

# 6. UI LAYOUT
st.title("Smart Factory Dashboard")
st.write(f"Monitoring System Active (Topic: {MQTT_TOPIC})")

# Sidebar
# Note: Ensure "1000046431.png" is in the same folder as this script
if os.path.exists("1000046431.png"):
    st.sidebar.image("1000046431.png", use_container_width=True)
else:
    st.sidebar.warning("Logo image not found.")

points = st.sidebar.slider("GRAPH PROPORTION (Last N points)", 5, 200, 20)
user_phone = st.sidebar.text_input("Worker Number", value="+91")

# 7. MAIN DASHBOARD LOGIC
if not st.session_state.history.empty:
    display_data = st.session_state.history.tail(points)
    last_temp = display_data['Temperature'].iloc[-1]
    last_sound = display_data['sound_level'].iloc[-1]

    # Alerts
    if last_temp > 75:
        st.error(f"⚠️ DANGER: Temperature High: {last_temp}°C")
        # Alert Sound (Hidden HTML)
        st.components.v1.html("<audio autoplay><source src='https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg' type='audio/ogg'></audio>", height=0)
    else:
        st.success(f"✅ System Normal: {last_temp}°C")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Current Temp", f"{last_temp}°C")
    with col2: st.metric("Max Temp", f"{display_data['Temperature'].max()}°C")
    with col3: st.metric("Min Temp", f"{display_data['Temperature'].min()}°C")
    with col4: st.metric("Sound Level", f"{last_sound}dB")

    # Live Graph
    st.subheader("📊 Performance Graph")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['Temperature'], name='Temp (°C)', line=dict(color='#FF4B4B')))
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['sound_level'], name='Sound (dB)', line=dict(color='#1C83E1')))
    fig.update_layout(template='plotly_dark', hovermode='x unified', height=400)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⌛ Waiting for sensor data... Please ensure the motor and MQTT publisher are active.")

# 8. HISTORICAL REPORT
st.markdown("---")
st.header("🔍 Historical Report")
selected_date = st.date_input("Select Date", value=datetime.now())

if st.button("Show Report"):
    if os.path.exists(LOG_FILE):
        df_h = pd.read_csv(LOG_FILE)
        # Robust date parsing
        df_h['Date-time'] = pd.to_datetime(df_h['Date-time'], format='%d/%m/%Y | %H:%M:%S', errors='coerce')
        df_h = df_h.dropna(subset=['Date-time'])
        
        filtered = df_h[df_h['Date-time'].dt.date == selected_date]
        
        if not filtered.empty:
            st.write(f"Data for {selected_date}")
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(x=filtered['Date-time'], y=filtered['Temperature'], name="Temp"))
            fig_h.add_trace(go.Scatter(x=filtered['Date-time'], y=filtered['sound_level'], name="Sound"))
            st.plotly_chart(fig_h, use_container_width=True)
            st.dataframe(filtered)
        else:
            st.warning(f"No data found for {selected_date}")
    else:
        st.error("No log file found yet.")

# Auto-refresh every 2 seconds
time.sleep(2)
st.rerun()
