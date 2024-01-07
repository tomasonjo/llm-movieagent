import streamlit as st
import requests

from typing import List, Tuple, Optional

st.title("Movie agent")

def get_agent_response(input: str, chat_history: Optional[List[Tuple]] = []) -> str:
    url = 'http://api:8080/movie-agent/stream'
    data = {'input': {'input': input, 'chat_history': chat_history}}
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(response.json())
        else:
            print('Error: ' + str(response.status_code))
    except requests.exceptions.ChunkedEncodingError as e:
        print("Chunked Encoding Error occurred:", e)
    except requests.exceptions.RequestException as e:
        print("Error during request:", e)


# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("How can I help you today?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    get_agent_response(prompt)
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""