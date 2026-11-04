import streamlit as st
import os
import re
from langchain_groq import ChatGroq

# Page configuration
st.set_page_config(
    page_title="Chandlio's Free AI Bot", 
    page_icon="⚡", 
    layout="wide"
)

# Custom Black & Orange Theme Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    .stTextInput input {
        color: #ffffff !important;
    }
    /* Orange Accent Buttons & Headings */
    h1, h2, h3 {
        color: #ff7700 !important;
    }
    .stChatMessage.user {
        background-color: #21262d;
        border: 1px solid #30363d;
    }
    .stChatMessage.assistant {
        background-color: #161b22;
        border: 1px solid #ff7700;
    }
    </style>
""", unsafe_allow_html=True)

# Custom Header
st.title("⚡ Chandlio's Free AI Bot")
st.caption("Blazing-fast open-source intelligence with live artifact previews & inline media — 100% Free.")

# Sidebar for configuration
st.sidebar.header("🔑 Configuration")
st.sidebar.markdown("Get your free Groq API key at [console.groq.com](https://console.groq.com)")
user_groq_key = st.sidebar.text_input("Enter Groq API Key", type="password")

if user_groq_key:
    os.environ["GROQ_API_KEY"] = user_groq_key

    try:
        # Initialize direct, streamlined model for Claude-like behavior
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3, max_tokens=2048)

        # Dual-pane layout: Chat (Left) & Artifact Workspace (Right)
        chat_col, workspace_col = st.columns([1, 1], gap="medium")

        with chat_col:
            st.subheader("💬 Chat Interface")
            
            if "messages" not in st.session_state:
                st.session_state["messages"] = []
            if "artifact_content" not in st.session_state:
                st.session_state["artifact_content"] = "# Welcome to Chandlio's Workspace\n\nGenerated code, markdown notes, or rendered media outputs will automatically appear here!"

            # Render past chat history
            for msg in st.session_state["messages"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    if "images" in msg and msg["images"]:
                        for img_url in msg["images"]:
                            st.image(img_url, use_container_width=True)

            # Handle new user input
            if prompt := st.chat_input("Ask for text, code, or images (e.g., 'Show me pictures of Switzerland')..."):
                st.session_state["messages"].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking at LPU speed..."):
                        # Direct clean generation without heavy intermediary tool loops
                        messages_payload = [("system", "You are a helpful, direct assistant modeled after Claude. If the user asks for images, include direct public image URLs using standard markdown or image lists so they can be rendered.")]
                        for m in st.session_state["messages"]:
                            messages_payload.append((m["role"], m["content"]))
                        
                        response = llm.invoke(messages_payload)
                        answer = response.content
                        
                        # Extract image links if any exist in the response
                        found_images = re.findall(r'(https?://[^\s]+\.(?:png|jpg|jpeg|webp))', answer, re.IGNORECASE)
                        
                        st.write(answer)
                        if found_images:
                            for img in found_images:
                                st.image(img, use_container_width=True)

                        st.session_state["messages"].append({
                            "role": "assistant", 
                            "content": answer,
                            "images": found_images
                        })
                        
                        # Push output to workspace
                        st.session_state["artifact_content"] = answer
                        st.rerun()

        with workspace_col:
            st.subheader("🖥️ Artifact Workspace")
            st.code(st.session_state["artifact_content"], language="markdown")

    except Exception as e:
        st.error(f"Initialization Error: {e}")
else:
    st.info("👈 Please enter your Groq API key in the sidebar to activate Chandlio's Bot.")
