import logging
import os
import sys
import time
import traceback

import requests
import streamlit as st

logger = logging.getLogger(__name__)

from ui_components import display_call_interface

st.set_page_config(page_title="AI Dialer", page_icon="📞", layout="wide")

# Initialize session state variables
if 'call_active' not in st.session_state:
    st.session_state.call_active = False
if 'call_sid' not in st.session_state:
    st.session_state.call_sid = None
if 'transcript' not in st.session_state:
    st.session_state.transcript = []
if 'system_message' not in st.session_state:
    st.session_state.system_message = os.getenv("SYSTEM_MESSAGE")
if 'initial_message' not in st.session_state:
    st.session_state.initial_message = os.getenv("INITIAL_MESSAGE")
if 'all_transcripts' not in st.session_state:
    st.session_state.all_transcripts = []
if 'recording_url' not in st.session_state:
    st.session_state.recording_url = None

# Move all UI elements except transcript to sidebar
with st.sidebar:
    st.markdown("<h1 style='font-size: 2.5em;'>📞 AI Dialer</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='margin-top: -0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)
    
    # Fetch all transcripts
    if st.button("Refresh Call List"):
        try:
            backend_url = os.getenv("SERVER")
            response = requests.get(f"https://{backend_url}/all_transcripts")
            response.raise_for_status()
            st.session_state.all_transcripts = response.json().get('transcripts', [])
        except requests.RequestException as e:
            st.error(f"Error fetching call list: {str(e)}")

    # Dropdown for selecting past calls
    call_options = ["Current Call"] + [f"Call {t['call_sid']}" for t in st.session_state.all_transcripts]
    selected_call = st.selectbox("Select Call", options=call_options)
    
    phone_number = display_call_interface()
    
    # System Message and Initial Message input fields
    st.session_state.system_message = st.text_area("System Message", value=st.session_state.system_message, disabled=st.session_state.call_active)
    st.session_state.initial_message = st.text_area("Initial Message", value=st.session_state.initial_message, disabled=st.session_state.call_active)
    
    col1, col2 = st.columns([1, 1], gap="small")
    start_call_button = col1.button("Start Call", use_container_width=True, type="primary", disabled=st.session_state.call_active)
    if start_call_button and not st.session_state.call_active:
        if phone_number:
            with st.spinner(f"Attempting to make call to: {phone_number}"):
                try:
                    backend_url = os.getenv("SERVER")
                    logger.info(f"Initiating call to {phone_number} via {backend_url}")
                    response = requests.post(f"https://{backend_url}/start_call", json={
                        "to_number": phone_number,
                        "system_message": st.session_state.system_message,
                        "initial_message": st.session_state.initial_message
                    }, timeout=10)
                    response.raise_for_status()
                    call_data = response.json()
                    call_sid = call_data.get('call_sid')
                    
                    if call_sid:
                        st.session_state.call_sid = call_sid
                        st.session_state.transcript = []  # Clear the transcript for the new call
                        st.success(f"✅ Call initiated successfully. Call SID: {call_sid}")
                        st.info("⏳ Waiting for call to be established...")
                        
                        # Wait for call to be established
                        max_attempts = 60
                        for attempt in range(max_attempts):
                            time.sleep(1)  # Wait for 1 second before checking
                            call_status_response = requests.get(f"https://{backend_url}/call_status/{call_sid}")
                            call_status_response.raise_for_status()
                            call_status = call_status_response.json().get('status')
                            
                            if call_status == 'in-progress':
                                st.session_state.call_active = True
                                break
                            elif call_status in ['completed', 'failed', 'busy', 'no-answer']:
                                st.error(f"❌ Call ended with status: {call_status}")
                                break
                        else:
                            st.error("⏱️ Timeout waiting for call to be established.")
                    else:
                        error_message = f"❌ Call SID not received. Response: {call_data}"
                        logger.error(error_message)
                        st.error(error_message)
                except requests.RequestException as e:
                    error_message = f"❌ Error initiating call: {str(e)}\n{traceback.format_exc()}"
                    logger.error(error_message)
                    st.error(error_message)
                except Exception as e:
                    error_message = f"❌ Unexpected error: {str(e)}\n{traceback.format_exc()}"
                    logger.error(error_message)
                    st.error(error_message)
        else:
            st.warning("⚠️ Please enter a valid phone number.")

    # End Call button
    if st.session_state.call_active:
        if col2.button("End Call", use_container_width=True, type="secondary"):
            try:
                backend_url = os.getenv("SERVER")
                response = requests.post(f"https://{backend_url}/end_call", json={"call_sid": st.session_state.call_sid})
                response.raise_for_status()
                st.success("✅ Request to end call sent successfully.")
                logger.info(f"End call request sent for call SID: {st.session_state.call_sid}")
                st.session_state.call_active = False
            except requests.RequestException as e:
                logger.error(f"Error sending end call request: {str(e)}")
                st.error(f"❌ Error sending end call request: {str(e)}")
    else:
        # Placeholder button when call is not active
        col2.button("End Call", use_container_width=True, type="secondary", disabled=True)

    # Add error placeholder
    error_placeholder = st.empty()

    if st.session_state.call_active:
        st.success("📞 Call in progress")
    st.markdown("<hr style='margin-top: 0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)

# Display transcript based on selection
if selected_call == "Current Call":
    if st.session_state.call_sid:
        st.markdown(f"### 📝 Transcript for Current Call {st.session_state.call_sid}")
        for entry in st.session_state.transcript:
            if entry['role'] in ['user', 'assistant']:
                with st.chat_message(entry['role']):
                    st.write(entry['content'])
else:
    selected_transcript = next((t for t in st.session_state.all_transcripts if f"Call {t['call_sid']}" == selected_call), None)
    if selected_transcript:
        st.markdown(f"### 📝 Transcript for {selected_call}")
        for entry in selected_transcript['transcript']:
            if entry['role'] in ['user', 'assistant']:
                with st.chat_message(entry['role']):
                    st.write(entry['content'])

if selected_call != "Current Call":
    selected_transcript = next((t for t in st.session_state.all_transcripts if f"Call {t['call_sid']}" == selected_call), None)
    if selected_transcript:
        call_sid = selected_transcript['call_sid']
        st.markdown(f"### 📝 Transcript for {selected_call}")
        for entry in selected_transcript['transcript']:
            if entry['role'] in ['user', 'assistant']:
                with st.chat_message(entry['role']):
                    st.write(entry['content'])
        
        # Add a button to fetch the recording URL
        if st.button("Get Recording URL"):
            try:
                backend_url = os.getenv("SERVER")
                response = requests.get(f"https://{backend_url}/call_recording/{call_sid}")
                response.raise_for_status()
                recording_data = response.json()
                recording_url = recording_data.get('recording_url')
                if recording_url:
                    st.session_state.recording_url = recording_url
                    st.success("Recording URL fetched successfully!")
                else:
                    st.warning("No recording URL available for this call.")
            except requests.RequestException as e:
                st.error(f"Error fetching recording URL: {str(e)}")

        # Display the recording URL if it's available
        if st.session_state.recording_url:
            st.markdown(f"### 🎵 Call Recording")
            st.markdown(f"[Click here to listen to the recording]({st.session_state.recording_url})")


# Update transcript and poll for updates if call is active
if st.session_state.call_active:
    def check_call_status_and_update_transcript():
        try:
            backend_url = os.getenv("SERVER")
            
            # First, check the call status
            status_response = requests.get(f"https://{backend_url}/call_status/{st.session_state.call_sid}")
            status_response.raise_for_status()
            call_status = status_response.json().get('status')
            
            if call_status not in ['in-progress', 'ringing']:
                st.session_state.call_active = False
                st.warning(f"Call ended with status: {call_status}")
                return False  # Indicate that we should stop updating
            
            # If call is still active, update the transcript
            transcript_response = requests.get(f"https://{backend_url}/transcript/{st.session_state.call_sid}")
            transcript_response.raise_for_status()
            transcript_data = transcript_response.json()
            
            if transcript_data.get('call_ended', False):
                st.session_state.call_active = False
                st.info(f"📞 Call has ended. Final status: {transcript_data.get('final_status', 'Unknown')}")
                return False  # Stop updating
            
            # Update the transcript in session state
            st.session_state.transcript = transcript_data.get('transcript', [])
            
            return True  # Indicate that we should continue updating

        except requests.RequestException as e:
            logger.error(f"Error fetching call status or transcript: {str(e)}")
            st.sidebar.error(f"Error updating call information: {str(e)}")
            return False  # Stop updating on error

    # Automatically update the call status and transcript
    should_continue = check_call_status_and_update_transcript()

    if should_continue:
        # Rerun the app every 1 second to refresh the status and transcript
        time.sleep(1)
        st.rerun()
    else:
        # If the call has ended, update the UI to reflect this
        st.session_state.call_active = False
        st.sidebar.info("Call has ended. You can start a new call if needed.")