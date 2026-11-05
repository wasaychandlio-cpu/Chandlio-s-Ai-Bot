import streamlit as st
import os
import io
import hashlib

# Page configuration
st.set_page_config(
    page_title="Chandlio's AI Bot",
    page_icon="⚡",
    layout="wide"
)

# Custom Exact Claude Theme Styling (Background #191919, White Text, Orange Accents)
st.markdown("""
<style>
.stApp { background-color: #191919; color: #ffffff; }
[data-testid="stSidebar"] { background-color: #1e1e1e; border-right: 1px solid #2a2a2a; }
.stTextInput input, .stTextArea textarea {
    background-color: #252525 !important; color: #ffffff !important;
    border-radius: 8px !important; border: 1px solid #333333 !important;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #ffffff !important; }
.stChatMessage.user { background-color: #252525; border-radius: 12px; color: #ffffff; }
.stChatMessage.assistant { background-color: #191919; border: 1px solid #2a2a2a; border-radius: 12px; color: #ffffff; }

/* ---------- Claude-style input bar ---------- */
.block-container { padding-bottom: 280px !important; }

.st-key-inputbar {
    position: fixed; bottom: 1.2rem; left: 21rem; right: 1rem;
    max-width: 820px; margin: 0 auto; z-index: 999;
    background: #2b2b2b; border: 1px solid #3d3d3d; border-radius: 24px;
    padding: 12px 16px 10px 16px; max-height: 75vh; overflow-y: auto;
    box-shadow: 0 4px 24px rgba(0,0,0,0.45);
}
@media (max-width: 900px) { .st-key-inputbar { left: 1rem; } }

/* transparent text area inside the bar */
.st-key-inputbar [data-baseweb="textarea"],
.st-key-inputbar [data-baseweb="base-input"] { background: transparent !important; border: none !important; }
.st-key-inputbar .stTextArea textarea {
    background: transparent !important; border: none !important;
    box-shadow: none !important; font-size: 1.1rem !important; color: #ffffff !important;
}
.st-key-inputbar .stTextArea textarea::placeholder { color: #8a8a8a !important; }

/* keep the button row on one line (also on mobile) */
.st-key-inputbar [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.4rem !important; }
.st-key-inputbar [data-testid="stColumn"] { min-width: 0 !important; }

/* plus / mic popover buttons */
.st-key-inputbar [data-testid="stPopover"] button {
    background: transparent !important; border: none !important;
    color: #ffffff !important; font-size: 1.4rem !important; padding: 0 0.5rem !important;
}
.st-key-inputbar [data-testid="stPopover"] button svg { display: none; }

/* send button */
.st-key-inputbar button[kind="primary"] {
    background: #d97757 !important; border: none !important;
    border-radius: 50% !important; width: 2.4rem; height: 2.4rem; color: #fff !important;
}

/* Chat / Cowork toggle */
.st-key-inputbar [data-testid="stButtonGroup"] button { background: #333 !important; color: #fff !important; border: none !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
defaults = {
    "chat_sessions": {"New Chat": []},
    "current_chat": "New Chat",
    "show_workspace": False,
    "workspace_content": "# Workspace\n\nGenerated artifacts will appear here.",
    "stored_groq_key": "",
    "projects": {},          # project name -> {"description": str, "files": [ {name,type,data} ]}
    "chat_project": {},      # chat name -> project name
    "attachments": [],       # files waiting to be sent with the next message
    "panel": None,           # "screenshot" | "upload" | "project" | None
    "pending_prompt": None,
    "msg_box": "",
    "upload_nonce": 0,
    "cam_nonce": 0,
    "project_tab": "Add to project",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

TEXT_EXT = (".txt", ".md", ".py", ".csv", ".json", ".js", ".html", ".css", ".xml",
            ".yaml", ".yml", ".log", ".sql", ".ini", ".toml")

# ---------------- HELPERS ----------------
def add_attachment(name, mime, data):
    if not any(a["name"] == name and len(a["data"]) == len(data) for a in st.session_state["attachments"]):
        st.session_state["attachments"].append({"name": name, "type": mime or "", "data": data})

def is_image(f):
    return f["type"].startswith("image/") or f["name"].lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))

def file_to_text(f, limit=6000):
    name = f["name"].lower()
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader  # optional: add `pypdf` to requirements.txt
            reader = PdfReader(io.BytesIO(f["data"]))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        elif name.endswith(TEXT_EXT):
            text = f["data"].decode("utf-8", errors="ignore")
        else:
            return ""
    except Exception:
        return ""
    return text[:limit]

def message_text(m):
    text = m["content"]
    for f in m.get("files", []):
        if is_image(f):
            text += f"\n\n[Attached image: {f['name']} (this model cannot view images)]"
        else:
            t = file_to_text(f)
            if t:
                text += f"\n\n[Attached file: {f['name']}]\n{t}"
            else:
                text += f"\n\n[Attached file: {f['name']} (content could not be read)]"
    return text

def build_system_prompt(mode):
    base = "You are a helpful, direct, premium AI assistant modeled after Claude."
    if mode == "Cowork":
        base += (" You are in Cowork mode: act as a hands-on collaborator. Break the task into a short plan, "
                 "then deliver complete, ready-to-use work products (documents, code, structured output).")
    proj = st.session_state["chat_project"].get(st.session_state["current_chat"])
    if proj and proj in st.session_state["projects"]:
        p = st.session_state["projects"][proj]
        base += f"\n\nThis chat belongs to the project '{proj}'."
        if p["description"]:
            base += f" Project description: {p['description']}"
        for f in p["files"]:
            t = file_to_text(f, 4000)
            if t:
                base += f"\n\n--- Project file: {f['name']} ---\n{t}"
    return base

# ---------------- CALLBACKS ----------------
def open_panel(name):
    st.session_state["panel"] = None if st.session_state["panel"] == name else name

def send_message():
    text = st.session_state["msg_box"].strip()
    if text or st.session_state["attachments"]:
        st.session_state["pending_prompt"] = text
        st.session_state["msg_box"] = ""

def remove_attachment(i):
    if 0 <= i < len(st.session_state["attachments"]):
        st.session_state["attachments"].pop(i)
    st.session_state["upload_nonce"] += 1
    st.session_state["cam_nonce"] += 1

def create_project():
    name = st.session_state.get("new_project_name", "").strip()
    if not name:
        st.session_state["toast"] = "Please enter a project name."
        return
    if name in st.session_state["projects"]:
        st.session_state["toast"] = "A project with that name already exists."
        return
    st.session_state["projects"][name] = {
        "description": st.session_state.get("new_project_desc", "").strip(),
        "files": [],
    }
    st.session_state["chat_project"][st.session_state["current_chat"]] = name
    st.session_state["new_project_name"] = ""
    st.session_state["new_project_desc"] = ""
    st.session_state["panel"] = None
    st.session_state["toast"] = f"Project '{name}' created and linked to this chat."

def add_to_project():
    proj = st.session_state.get("project_pick")
    if not proj or proj not in st.session_state["projects"]:
        return
    st.session_state["chat_project"][st.session_state["current_chat"]] = proj
    files = st.session_state["projects"][proj]["files"]
    for a in st.session_state["attachments"]:
        if not any(f["name"] == a["name"] and len(f["data"]) == len(a["data"]) for f in files):
            files.append(a)
    st.session_state["panel"] = None
    st.session_state["toast"] = f"Added to project '{proj}'."

def open_new_project_from_sidebar():
    st.session_state["panel"] = "project"
    st.session_state["project_tab"] = "New project"

def link_chat_to_project(proj):
    st.session_state["chat_project"][st.session_state["current_chat"]] = proj

def transcribe_audio():
    audio = st.session_state.get("mic_audio")
    if audio is None:
        return
    try:
        from groq import Groq
        client = Groq(api_key=st.session_state["stored_groq_key"])
        result = client.audio.transcriptions.create(
            file=("voice.wav", audio.getvalue()),
            model="whisper-large-v3-turbo",
        )
        st.session_state["msg_box"] = (st.session_state["msg_box"] + " " + result.text).strip()
    except Exception as e:
        st.session_state["toast"] = f"Voice input failed: {e}"

# ---------------- CLAUDE-STYLE SIDEBAR ----------------
with st.sidebar:
    st.markdown("<h3 style='color: #ffffff;'>⚡ Chandlio</h3>", unsafe_allow_html=True)
    if st.button("➕ New Chat", use_container_width=True):
        new_title = f"Chat {len(st.session_state['chat_sessions']) + 1}"
        st.session_state["chat_sessions"][new_title] = []
        st.session_state["current_chat"] = new_title
        st.session_state["show_workspace"] = False
        st.rerun()

    st.markdown("---")
    st.markdown("<p style='color: #aaaaaa; font-weight: bold;'>Recent Chats & Tasks</p>", unsafe_allow_html=True)
    for chat_name in list(st.session_state["chat_sessions"].keys())[::-1]:
        if st.button(chat_name, use_container_width=True, key=f"btn_{chat_name}"):
            st.session_state["current_chat"] = chat_name
            st.rerun()

    st.markdown("---")
    st.markdown("<p style='color: #aaaaaa; font-weight: bold;'>📁 Projects</p>", unsafe_allow_html=True)
    st.button("➕ New Project", use_container_width=True, key="side_new_project",
              on_click=open_new_project_from_sidebar)
    active_proj = st.session_state["chat_project"].get(st.session_state["current_chat"])
    for pname, pdata in st.session_state["projects"].items():
        label = f"{'✅ ' if pname == active_proj else '📁 '}{pname} ({len(pdata['files'])})"
        st.button(label, use_container_width=True, key=f"proj_{pname}",
                  on_click=link_chat_to_project, args=(pname,))

    st.markdown("---")
    st.markdown("<p style='color: #ffffff; font-weight: bold;'>🔑 Configuration</p>", unsafe_allow_html=True)
    user_groq_key = st.text_input("Groq API Key", value=st.session_state["stored_groq_key"],
                                  type="password", placeholder="gsk_...")
    if user_groq_key:
        st.session_state["stored_groq_key"] = user_groq_key
        os.environ["GROQ_API_KEY"] = user_groq_key

# ---------------- INPUT BAR ----------------
def render_input_bar():
    with st.container(key="inputbar"):
        panel = st.session_state["panel"]

        # ----- Panels opened from the + menu -----
        if panel == "screenshot":
            st.markdown("**📸 Take a screenshot**")
            shot = st.camera_input("Capture with your camera", key=f"cam_{st.session_state['cam_nonce']}")
            if shot is not None:
                data = shot.getvalue()
                add_attachment(f"capture_{hashlib.md5(data).hexdigest()[:6]}.png", shot.type, data)
            st.caption("To capture your screen: press Win+Shift+S (Windows) / Cmd+Shift+4 (Mac), then upload it here.")
            shots = st.file_uploader("Upload a screenshot", type=["png", "jpg", "jpeg", "webp"],
                                     accept_multiple_files=True, key=f"shotup_{st.session_state['upload_nonce']}")
            for f in shots or []:
                add_attachment(f.name, f.type, f.getvalue())

        elif panel == "upload":
            st.markdown("**📎 Upload or add files**")
            files = st.file_uploader("Add files", accept_multiple_files=True,
                                     key=f"uploader_{st.session_state['upload_nonce']}")
            for f in files or []:
                add_attachment(f.name, f.type, f.getvalue())

        elif panel == "project":
            st.markdown("**📁 Projects**")
            st.radio("Project action", ["Add to project", "New project"], key="project_tab",
                     horizontal=True, label_visibility="collapsed")
            if st.session_state["project_tab"] == "Add to project":
                if st.session_state["projects"]:
                    st.selectbox("Choose a project", list(st.session_state["projects"].keys()), key="project_pick")
                    st.caption("Links this chat to the project and saves any attached files into it.")
                    st.button("Add to project", on_click=add_to_project, key="do_add_project")
                else:
                    st.info("No projects yet. Switch to 'New project' to create one.")
            else:
                st.text_input("Project name", key="new_project_name", placeholder="e.g. Trading Bot")
                st.text_area("Description (optional)", key="new_project_desc", height=80,
                             placeholder="What is this project about?")
                st.button("Create project", on_click=create_project, key="do_create_project")

        # ----- Attached file chips -----
        for i, a in enumerate(st.session_state["attachments"]):
            st.button(f"📎 {a['name']}  ✕", key=f"rm_{i}", on_click=remove_attachment, args=(i,))

        # ----- Text box -----
        st.text_area("Message", key="msg_box", placeholder="How can I help you today?",
                     height=90, label_visibility="collapsed")

        # ----- Bottom row: + | Chat/Cowork | mic | send -----
        c_plus, c_mode, c_space, c_mic, c_send = st.columns([1.2, 4, 5, 1.2, 1.2], vertical_alignment="center")

        with c_plus:
            with st.popover("＋"):
                st.button("📸  Take a screenshot", key="m_shot", use_container_width=True,
                          on_click=open_panel, args=("screenshot",))
                st.button("📎  Upload or add files", key="m_upload", use_container_width=True,
                          on_click=open_panel, args=("upload",))
                st.button("📁  Add to project", key="m_project", use_container_width=True,
                          on_click=open_panel, args=("project",))

        with c_mode:
            if hasattr(st, "segmented_control"):
                st.segmented_control("Mode", ["Chat", "Cowork"], default="Chat",
                                     key="mode_sel", label_visibility="collapsed")
            else:
                st.radio("Mode", ["Chat", "Cowork"], key="mode_sel", horizontal=True,
                         label_visibility="collapsed")

        with c_mic:
            with st.popover("🎤"):
                if hasattr(st, "audio_input"):
                    st.audio_input("Record a voice message", key="mic_audio", on_change=transcribe_audio)
                else:
                    st.caption("Update Streamlit to use voice input.")

        with c_send:
            st.button("↑", key="send_btn", type="primary", on_click=send_message)

# ---------------- MAIN WINDOW ----------------
if st.session_state.get("toast"):
    st.toast(st.session_state.pop("toast"))

active_key = st.session_state["stored_groq_key"]

if not active_key:
    st.markdown("<br><br><h1 style='text-align: center; color: #ffffff;'>⚡ Welcome to Chandlio's AI Bot</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a1a1aa;'>Please enter your free Groq API key in the left sidebar to unlock the application.</p>", unsafe_allow_html=True)
    st.stop()

mode = st.session_state.get("mode_sel") or "Chat"

try:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3, max_tokens=2048)

    if st.session_state["show_workspace"]:
        chat_pane, workspace_pane = st.columns([1, 1], gap="large")
    else:
        chat_pane = st.container()

    with chat_pane:
        current_messages = st.session_state["chat_sessions"][st.session_state["current_chat"]]
        proj_name = st.session_state["chat_project"].get(st.session_state["current_chat"])
        if proj_name:
            st.caption(f"📁 Project: {proj_name}")

        if not current_messages:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; color: #ffffff;'>It’s a high-speed AI session.</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #a1a1aa;'>How can I help you today?</p>", unsafe_allow_html=True)

        # Render messages
        for msg in current_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                for f in msg.get("files", []):
                    if is_image(f):
                        st.image(f["data"], width=300)
                    else:
                        st.caption(f"📎 {f['name']}")
                if "images" in msg and msg["images"]:
                    for img_url in msg["images"]:
                        st.markdown(f'<img src="{img_url}" style="width:100%; border-radius:10px; margin-top:10px;">', unsafe_allow_html=True)

        # Handle a message sent from the custom input bar
        pending = st.session_state["pending_prompt"]
        if pending is not None:
            st.session_state["pending_prompt"] = None
            files = list(st.session_state["attachments"])
            st.session_state["attachments"] = []
            st.session_state["panel"] = None
            st.session_state["upload_nonce"] += 1
            st.session_state["cam_nonce"] += 1

            prompt = pending or "(see attached files)"
            current_messages.append({"role": "user", "content": prompt, "files": files})

            with st.chat_message("user"):
                st.markdown(prompt)
                for f in files:
                    if is_image(f):
                        st.image(f["data"], width=300)
                    else:
                        st.caption(f"📎 {f['name']}")

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    lower_prompt = prompt.lower()
                    if "switzerland" in lower_prompt or "swiss" in lower_prompt or "pictures" in lower_prompt:
                        answer = "Here are stunning views of Switzerland for you to explore:"
                        found_images = [
                            "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Matterhorn_from_Gornergrat_%28cropped%29.jpg/1200px-Matterhorn_from_Gornergrat_%28cropped%29.jpg",
                            "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Interlaken_and_Jungfrau_03.jpg/1200px-Interlaken_and_Jungfrau_03.jpg"
                        ]
                    else:
                        messages_payload = [("system", build_system_prompt(mode))]
                        for m in current_messages:
                            messages_payload.append((m["role"], message_text(m)))
                        response = llm.invoke(messages_payload)
                        answer = response.content
                        found_images = []

                    st.markdown(answer)
                    if found_images:
                        for img in found_images:
                            st.markdown(f'<img src="{img}" style="width:100%; border-radius:10px; margin-top:10px;">', unsafe_allow_html=True)

            current_messages.append({"role": "assistant", "content": answer, "images": found_images})

            if "```" in answer or len(answer) > 300 or mode == "Cowork":
                st.session_state["show_workspace"] = True
                st.session_state["workspace_content"] = answer
                st.rerun()

    # Workspace Pane (Right side)
    if st.session_state["show_workspace"]:
        with workspace_pane:
            col_title, col_close = st.columns([4, 1])
            with col_title:
                st.markdown("<h3 style='color: #ffffff;'>🖥️ Artifact Workspace</h3>", unsafe_allow_html=True)
            with col_close:
                if st.button("✕ Close"):
                    st.session_state["show_workspace"] = False
                    st.rerun()
            st.code(st.session_state["workspace_content"], language="markdown")

except Exception as e:
    st.error(f"Error: {e}")

# Custom Claude-style input bar (fixed at the bottom)
render_input_bar() 
