import os

import streamlit as st


def display_call_interface():
    st.write("Enter a phone number to start a call:")
    phone_number = st.text_input("Phone Number (format: +1XXXXXXXXXX)", key="phone_number_input", value=os.getenv("YOUR_NUMBER") or "")
    return phone_number

def display_transcript(transcript, placeholder):
    placeholder.empty()
    with placeholder.container():
        st.write("Call Transcript:")
        st.write("\n".join(transcript))

def display_end_call_button():
    return st.button("End Call")
