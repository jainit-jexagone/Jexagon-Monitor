import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime

# ૧. પેજ સેટઅપ
st.set_page_config(page_title="ORIX Smart Factory", layout="wide")

# CSS - બધું વધારાનું હાઈડ કરવા માટે
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

LOG_FILE = "motor_logs.csv"
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "janit/motor/data"

# ૨. સેશન સ્ટેટ ઇનિશિયલાઈઝેશન
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])

# ૩. MQTT Callback
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        st.session_state.temp = float(data.get('temp', 0))
        st.session_state.sound = float(data.get('sound', 0))
        
        # ડેટા સેવ કરવાનું લોજિક
        now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
        new_row = pd.DataFrame([[now, st.session_state.temp, st.session_state.sound]], 
                                columns=['Date-time', 'Temperature', 'sound_level'])
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
        new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))
    except:
        pass

# ૪. MQTT કનેક્શન
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    st.session_state.mqtt_client = client

# ૫. UI LAYOUT
st.title("🏭 ORIX Smart Factory Dashboard")
st.sidebar.title("🚀 ORIX IoT Settings")
points = st.sidebar.slider("Points to show", 5, 100, 20)

if not st.session_state.history.empty:
    display_data = st.session_state.history.tail(points)
    last_temp = display_data['Temperature'].iloc[-1]
    last_sound = display_data['sound_level'].iloc[-1]

    # મેટ્રિક્સ
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("🌡️ Temp", f"{last_temp}°C")
    with col2: st.metric("📈 Max", f"{display_data['Temperature'].max()}°C")
    with col3: st.metric("📉 Min", f"{display_data['Temperature'].min()}°C")
    with col4: st.metric("🔊 Sound", f"{last_sound}dB")

    # લાઈવ ગ્રાફ
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['Temperature'], name='Temp (°C)', line=dict(color='#FF4B4B')))
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['sound_level'], name='Sound (dB)', line=dict(color='#1C83E1')))
    fig.update_layout(template='plotly_dark', height=400)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⌛ ESP32 માંથી ડેટાની રાહ જોવાય છે... સીરીયલ મોનિટર મુજબ પબ્લિશિંગ ચાલુ છે!")

st.write(f"🕒 Last Sync: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
