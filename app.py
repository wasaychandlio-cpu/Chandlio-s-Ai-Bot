"""Chandlio's AI Bot - upgraded single-file Streamlit app.

Run locally:  streamlit run app.py
Deploy:       push app.py + requirements.txt to GitHub -> Streamlit Cloud.
Optional:     add GROQ_API_KEY to the app's Secrets so visitors don't need a key.
"""
import json
import re

import streamlit as st

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Chandlio's AI Bot", page_icon="⚡", layout="wide")

MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]
MAX_HISTORY = 20  # last N messages sent to the model (protects free-tier limits)
MAX_TOKENS = 4096
SYSTEM_PROMPT = (
    "You are Chandlio's AI Bot: a helpful, direct and concise assistant. "
    "Use markdown. Put code in fenced code blocks with the language name. "
    "If you are unsure, say so instead of guessing."
)

st.markdown(
    """
<style>
.stApp { background-color: #191919; color: #ffffff; }
[data-testid="stSidebar"] { background-color: #1e1e1e; border-right: 1px solid #2a2a2a; }
[data-testid="stChatMessage"] { border-radius: 12px; border: 1px solid #2a2a2a; }
.stTextInput input { background-color: #252525 !important; color: #ffffff !important; }
h1, h2, h3 { color: #ffffff !important; }
.hero { text-align: center; margin-top: 12vh; }
.hero p { color: #a1a1aa; }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# State helpers
# ----------------------------------------------------------------------------
def new_chat():
    cid = st.session_state.next_id
    st.session_state.next_id += 1
    st.session_state.chats[cid] = {"title": "New chat", "messages": [], "blocks": [], "error": ""}
    st.session_state.current = cid
    st.session_state.show_workspace = False
    st.session_state.pending = False


def init_state():
    if "chats" not in st.session_state:
        st.session_state.chats = {}
        st.session_state.next_id = 1
        st.session_state.show_workspace = False
        st.session_state.pending = False
        st.session_state.last_import = None
        new_chat()


def secret_key():
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return ""


def extract_blocks(text):
    """Return [(language, code), ...] for fenced code blocks in text."""
    return [(lang or "text", code.strip("\n")) for lang, code in re.findall(r"```(\w*)\n(.*?)```", text, re.S)]


def friendly_error(e):
    name, msg = type(e).__name__, str(e)
    low = msg.lower()
    if "401" in msg or "invalid_api_key" in low or "authentication" in name.lower():
        return "Your Groq API key looks invalid. Check it in the sidebar."
    if "429" in msg or "ratelimit" in name.lower() or "rate limit" in low:
        return "Rate limit reached. Wait a moment and retry, or switch to a smaller model."
    if "connection" in name.lower() or "timeout" in name.lower():
        return "Couldn't reach Groq. Check your connection and retry."
    if "model" in low and ("not found" in low or "decommissioned" in low):
        return "That model isn't available on Groq right now. Pick another one in the sidebar."
    return f"Something went wrong: {msg}"


@st.cache_resource(show_spinner=False)
def get_llm(api_key, model, temperature):
    from langchain_groq import ChatGroq

    return ChatGroq(model=model, api_key=api_key, temperature=temperature, max_tokens=MAX_TOKENS)


def stream_tokens(llm, payload):
    for chunk in llm.stream(payload):
        if chunk.content:
            yield chunk.content


init_state()

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ Chandlio")
    if st.button("➕ New chat", use_container_width=True):
        new_chat()
        st.rerun()

    st.markdown("---")
    st.caption("Recent chats")
    for cid in reversed(list(st.session_state.chats.keys())):
        c = st.session_state.chats[cid]
        label = ("▸ " if cid == st.session_state.current else "") + c["title"]
        if st.button(label, use_container_width=True, key=f"chat_{cid}"):
            st.session_state.current = cid
            st.session_state.show_workspace = False
            st.session_state.pending = False
            st.rerun()

    if st.button("🗑️ Delete this chat", use_container_width=True):
        st.session_state.chats.pop(st.session_state.current, None)
        if st.session_state.chats:
            st.session_state.current = list(st.session_state.chats.keys())[-1]
            st.session_state.pending = False
            st.session_state.show_workspace = False
        else:
            new_chat()
        st.rerun()

    st.markdown("---")
    st.caption("Settings")
    typed_key = st.text_input("Groq API key", type="password", placeholder="gsk_...", key="groq_key")
    api_key = typed_key or secret_key()
    model = st.selectbox("Model", MODELS)
    temperature = st.slider("Creativity", 0.0, 1.0, 0.3, 0.05)

    st.markdown("---")
    st.caption("Backup")
    export = {str(k): v for k, v in st.session_state.chats.items()}
    st.download_button(
        "⬇️ Export chats",
        data=json.dumps(export, ensure_ascii=False, indent=2),
        file_name="chandlio_chats.json",
        mime="application/json",
        use_container_width=True,
    )
    upload = st.file_uploader("Import chats", type="json", label_visibility="collapsed")
    if upload is not None and st.session_state.last_import != upload.file_id:
        try:
            data = json.loads(upload.getvalue())
            for item in data.values():
                if isinstance(item.get("messages"), list):
                    cid = st.session_state.next_id
                    st.session_state.next_id += 1
                    st.session_state.chats[cid] = {
                        "title": str(item.get("title", "Imported chat"))[:40],
                        "messages": [
                            {"role": m["role"], "content": m["content"]}
                            for m in item["messages"]
                            if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
                        ],
                        "blocks": [],
                        "error": "",
                    }
            st.session_state.last_import = upload.file_id
            st.rerun()
        except Exception:
            st.session_state.last_import = upload.file_id
            st.error("That file isn't a valid chat export.")

# ----------------------------------------------------------------------------
# Gate: need a key
# ----------------------------------------------------------------------------
if not api_key:
    st.markdown(
        "<div class='hero'><h1>⚡ Welcome to Chandlio's AI Bot</h1>"
        "<p>Enter your free Groq API key in the sidebar to get started.</p></div>",
        unsafe_allow_html=True,
    )
    st.stop()

try:
    llm = get_llm(api_key, model, temperature)
except Exception as e:
    st.error(f"Could not start the model client: {e}")
    st.stop()

# ----------------------------------------------------------------------------
# Main layout
# ----------------------------------------------------------------------------
chat = st.session_state.chats[st.session_state.current]
messages = chat["messages"]
show_ws = bool(chat["blocks"]) and st.session_state.show_workspace

if show_ws:
    chat_pane, ws_pane = st.columns([1, 1], gap="large")
else:
    chat_pane, ws_pane = st.container(), None

with chat_pane:
    if not messages:
        st.markdown(
            "<div class='hero'><h1>It's a high-speed AI session.</h1>"
            "<p>How can I help you today?</p></div>",
            unsafe_allow_html=True,
        )

    for m in messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Generate a reply when the last message is from the user
    if st.session_state.pending and messages and messages[-1]["role"] == "user":
        st.session_state.pending = False
        payload = [("system", SYSTEM_PROMPT)] + [(m["role"], m["content"]) for m in messages[-MAX_HISTORY:]]
        with st.chat_message("assistant"):
            try:
                answer = st.write_stream(stream_tokens(llm, payload))
                messages.append({"role": "assistant", "content": answer})
                chat["error"] = ""
                blocks = extract_blocks(answer)
                chat["blocks"] = blocks
                st.session_state.show_workspace = bool(blocks)
            except Exception as e:
                chat["error"] = friendly_error(e)
        st.rerun()

    if chat["error"]:
        st.error(chat["error"])
        if st.button("🔁 Retry", key="retry"):
            chat["error"] = ""
            st.session_state.pending = True
            st.rerun()
    elif messages and messages[-1]["role"] == "assistant":
        if st.button("🔄 Regenerate", key="regen"):
            messages.pop()
            st.session_state.pending = True
            st.rerun()

if ws_pane is not None:
    with ws_pane:
        left, right = st.columns([4, 1])
        left.markdown("### 🖥️ Workspace")
        if right.button("✕ Close"):
            st.session_state.show_workspace = False
            st.rerun()
        for lang, code in chat["blocks"]:
            st.code(code, language=lang)

# Chat input is created last, outside the columns, so it stays pinned to the bottom
if prompt := st.chat_input("Message Chandlio..."):
    messages.append({"role": "user", "content": prompt})
    if chat["title"] == "New chat":
        chat["title"] = prompt.strip().replace("\n", " ")[:30] or "New chat"
    chat["error"] = ""
    st.session_state.pending = True
    st.rerun()
