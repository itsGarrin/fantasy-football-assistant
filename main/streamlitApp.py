import streamlit as st
from agent import NFLAgent

# Initialize the NFLAgent
nfl_agent = NFLAgent()

# Set up the Streamlit app
st.title("Fantasy Football Assistant")
st.sidebar.title("Settings")

# Sidebar inputs for League ID and Team Name
st.sidebar.header("League Information")
league_id = st.sidebar.text_input("Enter your League ID", "")
team_name = st.sidebar.text_input("Enter your Team Name", "")

# Chat interface
st.header("Chat with your Fantasy Football Assistant")
if not league_id or not team_name:
    st.warning("Please enter your League ID and Team Name in the sidebar to get personalized advice.")
else:
    nfl_agent.reset()  # Reset the agent to start a new session
    league_info_message = f"League ID: {league_id}, Team Name: {team_name}"
    nfl_agent.messages.append({"role": "system", "content": league_info_message})

# Chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# User input for chat
user_input = st.text_input("Type your question here:")
if st.button("Send"):
    if user_input:
        # Add user input to chat history
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Get response from NFLAgent
        response = nfl_agent.run(user_input, verbose=False)

        # Add response to chat history
        st.session_state["messages"].append({"role": "assistant", "content": response})
        user_input = ""  # Clear the input box

# Display chat history
st.write("### Chat History")
for message in st.session_state["messages"]:
    role = "User" if message["role"] == "user" else "Assistant"
    st.markdown(f"**{role}:** {message['content']}")

# Provide league-specific context if inputs are valid
if league_id and team_name:
    st.sidebar.markdown(f"**League ID:** {league_id}")
    st.sidebar.markdown(f"**Team Name:** {team_name}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("You can now ask questions about your team or league matchups in the chat interface.")

# Clear chat button
if st.sidebar.button("Clear Chat"):
    st.session_state["messages"] = []
    st.success("Chat cleared!")

# Debugging tools (optional)
if st.sidebar.checkbox("Show Debug Information"):
    st.subheader("Debug Information")
    st.write("Agent Messages:", nfl_agent.messages)