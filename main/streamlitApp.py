import random
import time

import streamlit as st
from sleeper_wrapper import League

import globals
from agent import NFLAgent  # Import your agent class

# Global variables to store league ID and team name
global_league_id = None
global_team_name = None

# Streamed response emulator
def response_generator():
    response = random.choice(
        [
            "Hello there! How can I assist you today?",
            "Hi, human! Is there anything I can help you with?",
            "Do you need help?",
        ]
    )
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

# Sidebar for league and team selection
st.sidebar.title("Fantasy League Settings")

# Step 1: Enter League ID
global_league_id = st.sidebar.text_input("Enter League ID", key="league_id")

# Step 2: Fetch teams if League ID is provided
if global_league_id:
    # Initialize a temporary agent to fetch teams
    league = League(global_league_id)
    users = league.get_users()

    if users:
        display_names = [user["display_name"] for user in users if "display_name" in user]
        # Step 3: Dropdown for team selection
        global_team_name = st.sidebar.selectbox("Select Your Team", display_names, key="team_name")
    else:
        st.sidebar.error("No teams found for this League ID. Please check and try again.")
        global_team_name = None
else:
    users = []

# Initialize the NFLAgent if League ID and Team Name are provided
if global_league_id and global_team_name:
    globals.set_league_id(global_league_id)
    globals.set_team_name(global_team_name)
    nfl_agent = NFLAgent()
else:
    nfl_agent = None

# Display chat interface only if NFLAgent is initialized
st.title("Fantasy Football Chat Assistant")

if nfl_agent:
    # Add a button to start a new chat
    if st.sidebar.button("Start New Chat"):
        # Clear the chat history when the button is clicked
        st.session_state.messages = []
        nfl_agent.reset()

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask me anything about your league or players!"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.write(prompt)

        # Use the agent to generate a response
        response = nfl_agent.run(prompt, verbose=True)
        print(response)
        with st.chat_message("assistant"):
            st.write(response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

else:
    st.write("Please provide a valid League ID and select a team in the sidebar to start chatting.")