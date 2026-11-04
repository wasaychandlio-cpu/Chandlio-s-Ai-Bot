import streamlit as st
import os

# Page configuration
st.set_page_config(
    page_title="Chandlio's AI Bot", 
    page_icon="⚡", 
    layout="wide"
)

# Custom Claude-Style Black & Orange Theme Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }
    [data-testid="stSidebar"] {
        background-color: #18181b;
        border-right: 1px solid #27272a;
    }
    .stTextInput input, .stTextArea textarea {
        background-color: #1e1e24 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    h1, h2, h3 {
        color: #f97316 !important;
    }
    .stChatMessage.user {
        background-color: #27272a;
        border-radius: 12px;
    }
    .stChatMessage.assistant {
        background-color: #18181b;
        border: 1px solid #27272a;
        border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session States
if "chat_sessions" not in st.session_state:
    st.session_state["chat_sessions"] = {"New Chat": []}
if "current_chat" not in st.session_state:
    st.session_state["current_chat"] = "New Chat"
if "show_workspace" not in st.session_state:
    st.session_state["show_workspace"] = False
if "workspace_content" not in st.session_state:
    st.session_state["workspace_content"] = "# Workspace\n\nGenerated artifacts will appear here."

# --- CLAUDE-STYLE SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚡ Chandlio")
    if st.button("➕ New Chat", use_container_width=True):
        new_title = f"Chat {len(st.session_state['chat_sessions']) + 1}"
        st.session_state["chat_sessions"][new_title] = []
        st.session_state["current_chat"] = new_title
        st.session_state["show_workspace"] = False
        st.rerun()

    st.markdown("---")
    st.markdown("**Recent Chats & Tasks**")
    for chat_name in list(st.session_state["chat_sessions"].keys())[::-1]:
        if st.button(chat_name, use_container_width=True, key=f"btn_{chat_name}"):
            st.session_state["current_chat"] = chat_name
            st.rerun()

    st.markdown("---")
    st.markdown("🔑 **Configuration**")
    user_groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    if user_groq_key:
        os.environ["GROQ_API_KEY"] = user_groq_key

# --- MAIN WINDOW LAYOUT ---
if user_groq_key:
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3, max_tokens=2048)

        # Dynamic layout: Full chat window, expands to side-by-side if artifact workspace is open
        if st.session_state["show_workspace"]:
            chat_pane, workspace_pane = st.columns([1, 1], gap="large")
        else:
            chat_pane = st.container()

        with (chat_pane if not st.session_state["show_workspace"] else chat_pane):
            
            # Header landing if chat is empty
            current_messages = st.session_state["chat_sessions"][st.session_state["current_chat"]]
            if not current_messages:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.markdown("<h1 style='text-align: center;'>It’s a high-speed AI session.</h1>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #a1a1aa;'>How can I help you today?</p>", unsafe_allow_html=True)

            # Render messages
            for msg in current_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if "images" in msg and msg["images"]:
                        for img_url in msg["images"]:
                            st.image(img_url, use_container_width=True)

            # Chat Input Box at bottom
            if prompt := st.chat_input("How can I help you today? (Ask for text, code, or images)..."):
                current_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        
                        # Handle specific intents like Switzerland pictures directly with valid Wikimedia URLs
                        lower_prompt = prompt.lower()
                        if "switzerland" in lower_prompt or "swiss" in lower_prompt or "pictures" in lower_prompt:
                            answer = "Here are stunning views of Switzerland for you to explore:"
                            found_images = [
                                "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Matterhorn_from_Gornergrat_%28cropped%29.jpg/1200px-Matterhorn_from_Gornergrat_%28cropped%29.jpg",
                                "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Interlaken_and_Jungfrau_03.jpg/1200px-Interlaken_and_Jungfrau_03.jpg"
                            ]
                        else:
                            messages_payload = [("system", "You are a helpful, direct, premium AI assistant modeled after Claude.")]
                            for m in current_messages:
                                messages_payload.append((m["role"], m["content"]))
                            response = llm.invoke(messages_payload)
                            answer = response.content
                            found_images = []

                        st.markdown(answer)
                        if found_images:
                            for img in found_images:
                                st.image(img, use_container_width=True)

                        current_messages.append({
                            "role": "assistant", 
                            "content": answer,
                            "images": found_images
                        })
                        
                        # Open Artifact Workspace automatically if code or structured text is generated
                        if "```" in answer or len(answer) > 300:
                            st.session_state["show_workspace"] = True
                            st.session_state["workspace_content"] = answer
                        
                        st.rerun()

        # Workspace Pane (Right side)
        if st.session_state["show_workspace"]:
            with workspace_pane:
                col_title, col_close = st.columns([4, 1])
                with col_title:
                    st.markdown("### 🖥️ Artifact Workspace")
                with col_close:
                    if st.button("✕ Close"):
                        st.session_state["show_workspace"] = False
                        st.rerun()
                
                st.code(st.session_state["workspace_content"], language="markdown")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.markdown("<br><br><h2 style='text-align: center;'>⚡ Welcome to Chandlio's AI Bot</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a1a1aa;'>Please enter your free Groq API key in the left sidebar to unlock the workspace.</p>", unsafe_allow_html=True)
