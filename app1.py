import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
LOG_FILE = "motor_logs.csv"
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import json

st.set_page_config(
    page_title="Smart Factory", 
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* આ નીચેની લાઈન ખાસ ઉમેરજો Footer અને Badge કાઢવા માટે */
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    .viewerBadge_container__1QS13 {display: none !important;}
    div.stDeployButton {display:none;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QS13 {display: none;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "janit/motor/data"

def on_message(client, userdata, msg):
    try:
    
        data = json.loads(msg.payload.decode())
        st.session_state.temp = data['temp']
        st.session_state.sound = data['sound']
        
        now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
        new_row = pd.DataFrame([[now, data['temp'], data['sound']]], 
                                columns=['Date-time', 'Temperature', 'sound_level'])
        
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
        
        new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))
    except Exception as e:
        pass

if 'mqtt_connected' not in st.session_state:
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    st.session_state.mqtt_connected = True

def cleanup_old_data(filename):
    if os.path.exists(filename):

        try:
            df = pd.read_csv(filename)
            df['Date-time'] = pd.to_datetime(df['Date-time'], format='mixed', dayfirst=True)
            
            cutoff_date = datetime.now() - timedelta(days=180)
            filtered_df = df[df['Date-time'] >= cutoff_date]
            
            if len(filtered_df) < len(df):
                filtered_df.to_csv(filename, index=False)
        except Exception as e:
            st.error(f"Error cleaning data: {e}")

st.title("Smart Factory Dashboard")
st.write("Welcome, motor monitoring system")

points = st.sidebar.slider("GRAPH PROPORTION", 10, 100, 20)

current_time=datetime.now().strftime("%d/%m/%Y | %H:%M:%S")

if 'history' not in st.session_state:
    
    st.session_state.history = pd.DataFrame(columns=['Temperature','sound_level'])
    

now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")

if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0

new_temp = st.session_state.temp
new_sound = st.session_state.sound

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    val = float(payload)
    if "field1" in msg.topic:
        st.session_state.temp = val
    elif "field2" in msg.topic:
        st.session_state.sound = val


new_data = pd.DataFrame({ 'Date-time': [now], 
                         'Temperature': [new_temp],
                         'sound_level': [new_sound]})
TEMP_LIMIT = 70.0
SOUND_LIMIT = 85.0 

if new_temp > TEMP_LIMIT:
    st.error(f"⚠️ ખતરો (DANGER): મશીન અતિશય ગરમ છે! તાપમાન: {new_temp}°C")
    st.markdown(f"<h1 style='color:red; text-align:center;'>🚨 MACHINE OVERHEATING 🚨</h1>", unsafe_allow_html=True)

if new_sound > SOUND_LIMIT:
    st.warning(f"🔔 ચેતવણી (WARNING): મશીનનો અવાજ વધી રહ્યો છે! લેવલ: {new_sound}dB")

user_phone = st.sidebar.text_input("worker number", value="+91")

st.session_state.history = pd.concat([st.session_state.history, new_data], ignore_index=True)

display_data = st.session_state.history.tail(points)

last_temp =display_data['Temperature'].iloc[-1]

if last_temp < 75:
    st.success(f"System Healthy: {last_temp}°C")

else:
    st.error(f"High Temp Alert: {last_temp}°C")

last_sound=display_data['sound_level'].iloc[-1]

if last_sound > 85:
    st.error(f"sound is very high: {last_sound}dB")
else:
    st.success(f"sound is maintain :{last_sound}dB")

critical_condition = (last_temp > 75) or (last_sound > 85)
if critical_condition:
    st.error("🚨 CRITICAL ALERT! Motor at Risk!")
    st.components.v1.html(
        """
        <audio autoplay>
          <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg">
        </audio>
        """,
        height=0
    )        
else:   st.success(f"✅ System Normal: {last_temp}°C | {last_sound}dB")    

max_temp = display_data['Temperature'].max()
min_temp = display_data['Temperature'].min()

new_entry = pd.DataFrame([[current_time, new_temp, new_sound]], 
                         columns=['Date-time', 'Temperature', 'sound_level'])

if not os.path.isfile(LOG_FILE):
    new_entry.to_csv(LOG_FILE, index=False)
else:
    new_entry.to_csv(LOG_FILE, mode='a', index=False, header=False)

col1, col2, col3, col4  = st.columns(4)

with col1:
    st.metric("હાલનું (Current)", f"{last_temp}°C")
with col2:
    st.metric("મહત્તમ (Max)", f"{max_temp}°C")
with col3:
    st.metric("ન્યૂનતમ (Min)", f"{min_temp}°C")
with col4:
    st.metric("sound level",f"{last_sound}dB") 

st.markdown("---")
st.header("🔍 Historical Data Report (Calendar)")

selected_date = st.date_input("Select Date for Report", value=datetime.now())

if st.button("Show Report"):
    LOG_FILE = "motor_logs.csv"
    
    if os.path.exists(LOG_FILE):
        df_h = pd.read_csv(LOG_FILE)
        
        df_h['Date-time'] = pd.to_datetime(df_h['Date-time'], format='%d/%m/%Y | %H:%M:%S')
        
        filtered_data = df_h[df_h['Date-time'].dt.date == selected_date]
        
        if not filtered_data.empty:
            st.success(f"📊 Displaying report for {selected_date}")
            
            fig_report = go.Figure()
            fig_report.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['Temperature'], name='Temp (°C)', line=dict(color='#FF4B4B')))
            fig_report.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['sound_level'], name='Sound (dB)', line=dict(color='#1C83E1')))
            
            fig_report.update_layout(title=f"Motor Performance on {selected_date}", template='plotly_dark')
            st.plotly_chart(fig_report, use_container_width=True)
            
            with st.expander("View Detailed Log Table"):
                st.write(filtered_data)
                
            csv_data = filtered_data.to_csv(index=False)
            st.download_button("📥 Download This Report", data=csv_data, file_name=f"report_{selected_date}.csv", mime='text/csv')
        else:
            st.warning(f"⚠️ No data found for {selected_date}. Make sure the machine was ON.")
    else:
        st.error("❌ No log file found. Start the motor to generate data!")

st.markdown("---") 
st.write(f"🕒 **Last Updated: {current_time}**")
       
st.markdown("---")
st.subheader("📊 GRAPH")

fig = go.Figure()

fig.add_trace(go.Scatter(x=display_data['Date-time'], 
                         y=display_data['Temperature'],
                         mode='lines+markers', 
                         name='તાપમાન (°C)',
                         line=dict(color='#FF4B4B', width=3)))

fig.add_trace(go.Scatter(x=display_data['Date-time'], 
                         y=display_data['sound_level'],
                         mode='lines', 
                         name='sound (dB)',
                         line=dict(color='#1C83E1', width=2, dash='dot')))

fig.update_layout(template='plotly_dark', 
                  xaxis_title='time', 
                  yaxis_title='value',
                  hovermode='x unified')

st.plotly_chart(fig, use_container_width=True)

time.sleep(2)
st.rerun()
