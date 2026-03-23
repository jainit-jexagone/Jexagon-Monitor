import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ૧. પેજ સેટઅપ
st.set_page_config(page_title="Smart Factory", layout="wide")

# CSS - બધું હાઈડ કરવા માટે
hide_style = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_style, unsafe_allow_html=True)

LOG_FILE = "motor_logs.csv"
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "janit/motor/data"

# ૨. MQTT & CSV ફંક્શન્સ
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        st.session_state.temp = float(data.get('temp', 0))
        st.session_state.sound = float(data.get('sound', 0))
        st.session_state.new_data_arrived = True 
    except Exception as e:
        print(f"MQTT Error: {e}")

def save_to_csv_and_update_history():
    now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
    temp = st.session_state.temp
    sound = st.session_state.sound
    new_row = pd.DataFrame([[now, temp, sound]], columns=['Date-time', 'Temperature', 'sound_level'])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

# ૩. ઇનિશિયલાઈઝેશન
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0

if 'mqtt_client' not in st.session_state:
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    st.session_state.mqtt_client = client

# ૪. ડેટા પ્રોસેસિંગ
if st.session_state.get('new_data_arrived', False):
    save_to_csv_and_update_history() 
    st.session_state.new_data_arrived = False

# ૫. UI
st.title("Smart Factory Dashboard")
st.write("Welcome, motor monitoring system")

st.sidebar.image("1000046431.png", use_container_width=True) # તારો ORIX લોગો
points = st.sidebar.slider("GRAPH PROPORTION", 10, 100, 20)
user_phone = st.sidebar.text_input("Worker Number", value="+91")

# ૬. મેઈન લોજિક (IF ડેટા હોય તો જ)
if not st.session_state.history.empty:
    display_data = st.session_state.history.tail(points)
    last_temp = display_data['Temperature'].iloc[-1]
    last_sound = display_data['sound_level'].iloc[-1]

    # એલર્ટ્સ
    if last_temp > 75:
        st.error(f"⚠️ DANGER: Temperature High: {last_temp}°C")
        st.components.v1.html("<audio autoplay><source src='https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg' type='audio/ogg'></audio>", height=0)
    else:
        st.success(f"✅ System Normal: {last_temp}°C")

    # મેટ્રિક્સ
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Current", f"{last_temp}°C")
    with col2: st.metric("Max", f"{display_data['Temperature'].max()}°C")
    with col3: st.metric("Min", f"{display_data['Temperature'].min()}°C")
    with col4: st.metric("Sound", f"{last_sound}dB")

    # લાઈવ ગ્રાફ
    st.subheader("📊 ORIX Performance Graph")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['Temperature'], name='Temp', line=dict(color='#FF4B4B')))
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['sound_level'], name='Sound', line=dict(color='#1C83E1')))
    fig.update_layout(template='plotly_dark', hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⌛ Waiting for ORIX sensor data... Please start the motor.")

# ૭. કેલેન્ડર (Historical Report)
st.markdown("---")
st.header("🔍 Historical Report")
selected_date = st.date_input("Select Date", value=datetime.now())
if st.button("Show Report"):
    if os.path.exists(LOG_FILE):
        df_h = pd.read_csv(LOG_FILE)
        df_h['Date-time'] = pd.to_datetime(df_h['Date-time'], format='%d/%m/%Y | %H:%M:%S')
        filtered = df_h[df_h['Date-time'].dt.date == selected_date]
        if not filtered.empty:
            st.plotly_chart(go.Figure(data=[go.Scatter(x=filtered['Date-time'], y=filtered['Temperature'])]))
        else: st.warning("No data found.")

time.sleep(2)
st.rerun()
