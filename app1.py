
#OWNER_PHONE = "+919XXXXXXXXX"  
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
LOG_FILE = "motor_logs.csv"
import os
#import pywhatkit as kit
from datetime import datetime, timedelta
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import json

# --- Aa bhag tara Sidebar ma ke main page na niche muki de ---
st.markdown("---")
st.header("🔍 Historical Data Report (Calendar)")

# 1. Calendar input (Owner mate ekdam saral)
selected_date = st.date_input("Select Date for Report", value=datetime.now())

if st.button("Show Report"):
    LOG_FILE = "motor_logs.csv"
    
    # Check karo ke file che ke nahi
    if os.path.exists(LOG_FILE):
        # CSV file vancho
        df_h = pd.read_csv(LOG_FILE)
        
        # Date-time column ne convert karo
        df_h['Date-time'] = pd.to_datetime(df_h['Date-time'], format='%d/%m/%Y | %H:%M:%S')
        
        # Owner e select kareli date mujab data filter karo
        filtered_data = df_h[df_h['Date-time'].dt.date == selected_date]
        
        if not filtered_data.empty:
            st.success(f"📊 Displaying report for {selected_date}")
            
            # 2. Report no Graph (Owner ne joi ne maza padi jase)
            fig_report = go.Figure()
            fig_report.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['Temperature'], name='Temp (°C)', line=dict(color='#FF4B4B')))
            fig_report.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['sound_level'], name='Sound (dB)', line=dict(color='#1C83E1')))
            
            fig_report.update_layout(title=f"Motor Performance on {selected_date}", template='plotly_dark')
            st.plotly_chart(fig_report, use_container_width=True)
            
            # 3. Data Table (Jo owner ne numbers jova hoy to)
            with st.expander("View Detailed Log Table"):
                st.write(filtered_data)
                
            # Download Button (Jo owner ne Excel file joiye to)
            csv_data = filtered_data.to_csv(index=False)
            st.download_button("📥 Download This Report", data=csv_data, file_name=f"report_{selected_date}.csv", mime='text/csv')
        else:
            st.warning(f"⚠️ No data found for {selected_date}. Make sure the machine was ON.")
    else:
        st.error("❌ No log file found. Start the motor to generate data!")


# --- ૧. ThingSpeak credentials કાઢીને આ નવા સેટિંગ્સ નાખો ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "janit/motor/data"

# --- ૨. આ 'on_message' ફંક્શન ઉમેરો (ડેટા પકડવા અને સેવ કરવા માટે) ---
def on_message(client, userdata, msg):
    try:
        # JSON ડેટા વાંચો
        data = json.loads(msg.payload.decode())
        st.session_state.temp = data['temp']
        st.session_state.sound = data['sound']
        
        # લાઈવ હિસ્ટ્રી અને CSV (કેલેન્ડર માટે) અપડેટ કરો
        now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
        new_row = pd.DataFrame([[now, data['temp'], data['sound']]], 
                                columns=['Date-time', 'Temperature', 'sound_level'])
        
        # ડેટાને Session State માં ઉમેરો
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
        
        # ડેટાને CSV ફાઈલમાં કાયમી સેવ કરો (Calendar રિપોર્ટ માટે)
        new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))
    except Exception as e:
        pass

# --- ૩. આ MQTT કનેક્શન બ્લોક ઉમેરો (ThingSpeak વાળા કનેક્શનની જગ્યાએ) ---
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
# GitHub આઈકન અને મેનૂ હટાવવા માટેનો જાદુઈ કોડ
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QS13 {display: none;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

st.set_page_config(
    page_title="Smart Factory", 
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)
st.title("Smart Factory Dashboard")
st.write("Welcome, motor monitoring system")

points = st.sidebar.slider("GRAPH PROPORTION", 10, 100, 20)

current_time=datetime.now().strftime("%d/%m/%Y | %H:%M:%S")

if 'history' not in st.session_state:
    
    st.session_state.history = pd.DataFrame(columns=['Temperature','sound_level'])
    

now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")


 # ડેટા સાચવવા માટે Session State
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

#if (new_temp > TEMP_LIMIT) or (new_sound > SOUND_LIMIT):
   # kit.sendwhatmsg_instantly(OWNER_PHONE, f"🚨 Danger! Temp: {new_temp}C, Sound: {new_sound}dB")


if new_temp > TEMP_LIMIT:
    st.error(f"⚠️ ખતરો (DANGER): મશીન અતિશય ગરમ છે! તાપમાન: {new_temp}°C")
    st.markdown(f"<h1 style='color:red; text-align:center;'>🚨 MACHINE OVERHEATING 🚨</h1>", unsafe_allow_html=True)

if new_sound > SOUND_LIMIT:
    st.warning(f"🔔 ચેતવણી (WARNING): મશીનનો અવાજ વધી રહ્યો છે! લેવલ: {new_sound}dB")

#if new_temp > TEMP_LIMIT:
    # મેસેજ મોકલવા માટે: (નંબર, મેસેજ)
    # અત્યારે આને કમેન્ટમાં રાખવું અથવા સાવચેતીથી વાપરવું
    # kit.sendwhatmsg_instantly("+91XXXXXXXXXX", f"🚨 એલર્ટ: મશીન M01 ગરમ છે! તાપમાન: {new_temp}°C")
    #st.success("WhatsApp એલર્ટ મોકલવામાં આવ્યો છે!")


user_phone = st.sidebar.text_input("worker number", value="+91")

#if new_temp > TEMP_LIMIT:
   # if len(user_phone) > 10: 
        #kit.sendwhatmsg_instantly(user_phone, f"🚨 મશીન એલર્ટ: તાપમાન વધી ગયું છે!")

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
st.header("🔍 Search History (Single Day)")

# આજના દિવસથી ૬ મહિના (૧૮૦ દિવસ) પહેલાની તારીખ ગણો
six_months_ago = datetime.now() - timedelta(days=180)

# કેલેન્ડરમાં લિમિટ મૂકો
selected_date = st.date_input(
    "Select Date", 
    value=datetime.now(),
    min_value=six_months_ago, # આનાથી જૂની તારીખ નહીં દેખાય
    max_value=datetime.now()
)

if st.button("Show Report"):
    try:
        
        df_history = pd.read_csv("motor_logs.csv")
        
        df_history['Date-time'] = pd.to_datetime(df_history['Date-time'], format='%d/%m/%Y | %H:%M:%S')
        
        filtered_df = df_history[df_history['Date-time'].dt.date == selected_date]
        
        if not filtered_df.empty:
            st.success(f"📊 Report for {selected_date}")
            st.line_chart(filtered_df.set_index('Date-time')['Temperature'])
            st.write(filtered_df)
        else:
            st.warning(f"Dilgiri, {selected_date} na divas no koi data save thayo nathi.")
            
    except FileNotFoundError:
        st.error("Haji sudhi koi data save thayo nathi (CSV file missing).")

st.markdown("---") 
st.write(f"🕒 **Last Updated: {current_time}**")
       
st.markdown("---")
st.subheader("📊 GRAPH")

# ૧. નવો પ્લોટલી ગ્રાફ બનાવવો
fig = go.Figure()

# ૨. તાપમાનની લાઈન (Temperature)
fig.add_trace(go.Scatter(x=display_data['Date-time'], 
                         y=display_data['Temperature'],
                         mode='lines+markers', 
                         name='તાપમાન (°C)',
                         line=dict(color='#FF4B4B', width=3)))

# ૩. અવાજની લાઈન (Sound)
fig.add_trace(go.Scatter(x=display_data['Date-time'], 
                         y=display_data['sound_level'],
                         mode='lines', 
                         name='sound (dB)',
                         line=dict(color='#1C83E1', width=2, dash='dot')))

# ૪. ગ્રાફનો દેખાવ (Layout) સેટ કરવો
fig.update_layout(template='plotly_dark', 
                  xaxis_title='time', 
                  yaxis_title='value',
                  hovermode='x unified')

# ૫. ગ્રાફને સ્ક્રીન પર બતાવવો
st.plotly_chart(fig, use_container_width=True)

time.sleep(2)
st.rerun()
