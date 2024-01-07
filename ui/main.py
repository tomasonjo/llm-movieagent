from typing import List, Optional, Tuple

import streamlit as st
from langserve import RemoteRunnable
from streamlit.logger import get_logger

logger = get_logger(__name__)

st.title("Movie agent")


def get_agent_response(input: str, chat_history: Optional[List[Tuple]] = []) -> str:
    url = "http://api:8080/movie-agent/"
    remote_runnable = RemoteRunnable(url)
    return remote_runnable.invoke({"input": input, "chat_history": chat_history})

def generate_history():
    context = []
    # If any history exists
    if st.session_state['generated']:
        # Add the last three exchanges
        size = len(st.session_state['generated'])
        for i in range(max(size-3, 0), size):
            context.append((st.session_state['user_input'][i],  st.session_state['generated'][i]))
    return context


# Initialize chat history
if "generated" not in st.session_state:
    st.session_state["generated"] = []
# User input
if "user_input" not in st.session_state:
    st.session_state["user_input"] = []

# Accept user input
if prompt := st.chat_input("How can I help you today?"):
    chat_history = generate_history()
    answer = get_agent_response(prompt, chat_history)
    # Add user message to chat history
    st.session_state.user_input.append(prompt)
    st.session_state.generated.append(answer['output'])
# Display user message in chat message container
if st.session_state["generated"]:
    size = len(st.session_state["generated"])
    # Display only the last three exchanges
    for i in range(max(size - 3, 0), size):
        with st.chat_message("user"):
            st.markdown(st.session_state["user_input"][i])
        with st.chat_message("assistant"):
            st.markdown(st.session_state["generated"][i])
