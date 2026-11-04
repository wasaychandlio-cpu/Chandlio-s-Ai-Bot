import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Page configuration for a wide, professional layout
st.set_page_config(
    page_title="Chandlio's Free AI Bot", 
    page_icon="⚡", 
    layout="wide"
)

# Custom Styling & Header
st.title("⚡ Chandlio's Free AI Bot")
st.caption("Blazing-fast open-source intelligence with live artifact previews — 100% Free.")

# Sidebar for configuration
st.sidebar.header("🔑 Configuration")
st.sidebar.markdown("Get your free Groq API key at [console.groq.com](https://console.groq.com)")
user_groq_key = st.sidebar.text_input("Enter Groq API Key", type="password")

if user_groq_key:
    os.environ["GROQ_API_KEY"] = user_groq_key

    # Initialize the ultra-fast Groq model
    try:
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, max_tokens=2048)
        
        @tool
        def general_assistant_tool(query: str) -> str:
            """Provides contextual data and structured insights for user requests."""
            return f"Processed context for: {query}"

        agent = create_react_agent(llm, tools=[general_assistant_tool])

        # Dual-pane layout: Chat (Left) & Artifact Workspace (Right)
        chat_col, workspace_col = st.columns([1, 1], gap="medium")

        with chat_col:
            st.subheader("💬 Chat Interface")
            
            if "messages" not in st.session_state:
                st.session_state["messages"] = []
            if "artifact_content" not in st.session_state:
                st.session_state["artifact_content"] = "# Welcome to Chandlio's Workspace\n\nGenerated code, markdown notes, or scripts will automatically render here, just like Claude Artifacts!"

            # Render past chat history
            for msg in st.session_state["messages"]:
                st.chat_message(msg["role"]).write(msg["content"])

            # Handle new user input
            if prompt := st.chat_input("Ask your agent to write code, design an app, or analyze data..."):
                st.session_state["messages"].append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Chandlio's Bot is thinking at LPU speed..."):
                        response = agent.invoke({"messages": [("human", prompt)]})
                        answer = response["messages"][-1].content
                        st.write(answer)
                        st.session_state["messages"].append({"role": "assistant", "content": answer})
                        # Push output to workspace
                        st.session_state["artifact_content"] = answer
                        st.rerun()

        with workspace_col:
            st.subheader("🖥️ Artifact Workspace")
            # Display live workspace content
            st.code(st.session_state["artifact_content"], language="markdown")

    except Exception as e:
        st.error(f"Initialization Error: {e}")
else:
    st.info("👈 Please enter your Groq API key in the sidebar to activate Chandlio's Bot.")