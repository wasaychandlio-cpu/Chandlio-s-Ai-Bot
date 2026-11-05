import streamlit as st
import streamlit.components.v1 as components
import os
import io
import base64
import hashlib
import pathlib
import tempfile

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

.st-key-inputbar [data-baseweb="textarea"],
.st-key-inputbar [data-baseweb="base-input"] { background: transparent !important; border: none !important; }
.st-key-inputbar .stTextArea textarea {
    background: transparent !important; border: none !important;
    box-shadow: none !important; font-size: 1.1rem !important; color: #ffffff !important;
}
.st-key-inputbar .stTextArea textarea::placeholder { color: #8a8a8a !important; }

.st-key-inputbar [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.4rem !important; }
.st-key-inputbar [data-testid="stColumn"] { min-width: 0 !important; }

/* plus + mic popover buttons */
.st-key-inputbar [data-testid="stPopover"] button {
    background: transparent !important; border: none !important;
    color: #ffffff !important; font-size: 1.4rem !important; padding: 0 0.5rem !important;
}
.st-key-plus_wrap [data-testid="stPopover"] button svg { display: none; }
.st-key-plus_wrap [data-testid="stPopover"] button:hover { background: #3a3a3a !important; border-radius: 10px !important; }

/* Chat pill */
.chat-pill {
    display: inline-block; background: #3d3d3d; color: #ffffff; border: 1px solid #4a4a4a;
    border-radius: 10px; padding: 6px 18px; font-size: 1rem;
}

/* send button */
.st-key-inputbar button[kind="primary"] {
    background: #d97757 !important; border: none !important;
    border-radius: 50% !important; width: 2.4rem; height: 2.4rem; color: #fff !important;
}

/* ---------- Plus menu (popover body) ---------- */
[data-testid="stPopoverBody"] { background: #2b2b2b !important; border: 1px solid #3d3d3d !important; border-radius: 16px !important; min-width: 300px; }
[class*="st-key-menu_"] button {
    display: flex !important; justify-content: flex-start !important; text-align: left !important;
    background: transparent !important; border: none !important; color: #ffffff !important;
    padding: 0.55rem 0.7rem !important; border-radius: 10px !important; font-size: 1rem !important;
}
[class*="st-key-menu_"] button:hover { background: #3a3a3a !important; }
.st-key-menu_upload button::after { content: "Ctrl+U"; margin-left: auto; color: #9a9a9a; font-size: 0.9rem; padding-left: 2rem; }
.st-key-menu_project button::after { content: "›"; margin-left: auto; color: #aaaaaa; font-size: 1.5rem; padding-left: 2rem; }
.st-key-hidden_upload { display: none; }
</style>
""", unsafe_allow_html=True)

# ---------------- SCREEN CAPTURE COMPONENT (browser share picker) ----------------
SCREEN_CAPTURE_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { margin: 0; font-family: "Source Sans Pro", sans-serif; background: transparent; color: #fff; }
  #box { display: flex; align-items: center; gap: 12px; padding: 6px 2px; }
  button { background: #3a3a3a; color: #fff; border: 1px solid #4a4a4a; border-radius: 10px;
           padding: 8px 14px; font-size: 14px; cursor: pointer; }
  button:hover { background: #454545; }
  #msg { font-size: 13px; color: #b5b5b5; }
</style></head>
<body>
<div id="box"><button id="go">📸 Choose what to share</button>
<span id="msg">Pick a Chrome tab, a window or your entire screen.</span></div>
<script>
  var msg = document.getElementById("msg");
  function send(type, data) {
    window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: type}, data), "*");
  }
  var lastTrigger = null, busy = false;
  async function capture() {
    if (busy) return;
    busy = true;
    msg.textContent = "Waiting for your selection...";
    try {
      var nav = (window.parent && window.parent.navigator) ? window.parent.navigator : navigator;
      var stream = await nav.mediaDevices.getDisplayMedia({video: true, audio: false});
      var video = document.createElement("video");
      video.srcObject = stream; video.muted = true;
      await video.play();
      await new Promise(function(r){ setTimeout(r, 500); });
      var w = video.videoWidth, h = video.videoHeight;
      var scale = Math.min(1, 1920 / w);
      var c = document.createElement("canvas");
      c.width = Math.round(w * scale); c.height = Math.round(h * scale);
      c.getContext("2d").drawImage(video, 0, 0, c.width, c.height);
      stream.getTracks().forEach(function(t){ t.stop(); });
      msg.textContent = "Captured!";
      send("streamlit:setComponentValue", {value: {id: Date.now(), data: c.toDataURL("image/jpeg", 0.85)}, dataType: "json"});
    } catch (e) {
      msg.textContent = "Click the button, then choose a tab, window or screen.";
    }
    busy = false;
  }
  window.addEventListener("message", function(ev) {
    if (ev.data && ev.data.type === "streamlit:render") {
      var t = ev.data.args ? ev.data.args.trigger : null;
      if (t !== lastTrigger) { lastTrigger = t; capture(); }
      send("streamlit:setFrameHeight", {height: 52});
    }
  });
  document.getElementById("go").onclick = capture;
  send("streamlit:componentReady", {apiVersion: 1});
  send("streamlit:setFrameHeight", {height: 52});
</script>
</body></html>
"""

_COMPONENT_DIR = pathlib.Path(tempfile.gettempdir()) / "chandlio_screen_capture"
_COMPONENT_DIR.mkdir(parents=True, exist_ok=True)
_index_file = _COMPONENT_DIR / "index.html"
if not _index_file.exists() or _index_file.read_text(encoding="utf-8") != SCREEN_CAPTURE_HTML:
    _index_file.write_text(SCREEN_CAPTURE_HTML, encoding="utf-8")
screen_capture = components.declare_component("chandlio_screen_capture", path=str(_COMPONENT_DIR))

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
    "panel": None,           # "screenshot" | "upload" | "newproject" | None
    "menu_view": "main",     # "main" | "project"
    "shot_trigger": 0,
    "last_shot_id": None,
    "pending_prompt": None,
    "msg_box": "",
    "upload_nonce": 0,
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
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(f["data"]))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        elif name.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(f["data"]))
            text = "\n".join(p.text for p in doc.paragraphs)
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

def build_system_prompt():
    base = "You are a helpful, direct, premium AI assistant modeled after Claude."
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
def set_panel(name):
    st.session_state["panel"] = name
    st.session_state["menu_view"] = "main"

def start_screenshot():
    st.session_state["panel"] = "screenshot"
    st.session_state["shot_trigger"] += 1
    st.session_state["menu_view"] = "main"

def set_menu_view(view):
    st.session_state["menu_view"] = view

def close_panel():
    st.session_state["panel"] = None

def send_message():
    text = st.session_state["msg_box"].strip()
    if text or st.session_state["attachments"]:
        st.session_state["pending_prompt"] = text
        st.session_state["msg_box"] = ""

def remove_attachment(i):
    if 0 <= i < len(st.session_state["attachments"]):
        st.session_state["attachments"].pop(i)
    st.session_state["upload_nonce"] += 1

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
    st.session_state["menu_view"] = "main"
    st.session_state["toast"] = f"Project '{name}' created and linked to this chat."

def add_to_project(proj):
    if proj not in st.session_state["projects"]:
        return
    st.session_state["chat_project"][st.session_state["current_chat"]] = proj
    files = st.session_state["projects"][proj]["files"]
    for a in st.session_state["attachments"]:
        if not any(f["name"] == a["name"] and len(f["data"]) == len(a["data"]) for f in files):
            files.append(a)
    st.session_state["menu_view"] = "main"
    st.session_state["toast"] = f"Added to project '{proj}'."

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
              on_click=set_panel, args=("newproject",))
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
            res = screen_capture(trigger=st.session_state["shot_trigger"], key="screen_capture", default=None)
            if isinstance(res, dict) and res.get("data") and res.get("id") != st.session_state["last_shot_id"]:
                st.session_state["last_shot_id"] = res["id"]
                try:
                    raw = base64.b64decode(res["data"].split(",", 1)[1])
                    add_attachment(f"screenshot_{hashlib.md5(raw).hexdigest()[:6]}.jpg", "image/jpeg", raw)
                    st.session_state["toast"] = "Screenshot added."
                except Exception as e:
                    st.session_state["toast"] = f"Screenshot failed: {e}"
                st.session_state["panel"] = None
                st.rerun()
            st.button("✕ Close", key="close_shot", on_click=close_panel)

        elif panel == "upload":
            st.markdown("**📎 Upload or add files**")
            files = st.file_uploader("Add files", accept_multiple_files=True,
                                     key=f"uploader_{st.session_state['upload_nonce']}")
            for f in files or []:
                add_attachment(f.name, f.type, f.getvalue())
            st.button("✕ Close", key="close_upload", on_click=close_panel)

        elif panel == "newproject":
            st.markdown("**📁 New project**")
            st.text_input("Project name", key="new_project_name", placeholder="e.g. Trading Bot")
            st.text_area("Description (optional)", key="new_project_desc", height=80,
                         placeholder="What is this project about?")
            c1, c2 = st.columns(2)
            with c1:
                st.button("Create project", on_click=create_project, key="do_create_project")
            with c2:
                st.button("✕ Close", key="close_newproject", on_click=close_panel)

        # ----- Attached file chips -----
        for i, a in enumerate(st.session_state["attachments"]):
            st.button(f"📎 {a['name']}  ✕", key=f"rm_{i}", on_click=remove_attachment, args=(i,))

        # ----- Text box (Enter sends, Shift+Enter = new line) -----
        st.text_area("Message", key="msg_box", placeholder="How can I help you today?",
                     height=90, label_visibility="collapsed")

        # ----- Bottom row: + | Chat | ... | mic | send -----
        c_plus, c_chat, c_space, c_mic, c_send = st.columns([1, 2, 6, 1.4, 1.2], vertical_alignment="center")

        with c_plus:
            with st.container(key="plus_wrap"):
                with st.popover("＋"):
                    if st.session_state["menu_view"] == "main":
                        st.button("Upload or add files", icon=":material/attach_file:", key="menu_upload",
                                  use_container_width=True, on_click=set_panel, args=("upload",))
                        st.button("Take a screenshot", icon=":material/photo_camera:", key="menu_shot",
                                  use_container_width=True, on_click=start_screenshot)
                        st.button("Add to project", icon=":material/inventory_2:", key="menu_project",
                                  use_container_width=True, on_click=set_menu_view, args=("project",))
                    else:
                        st.button("Back", icon=":material/arrow_back:", key="menu_back",
                                  use_container_width=True, on_click=set_menu_view, args=("main",))
                        for i, pname in enumerate(st.session_state["projects"].keys()):
                            st.button(pname, icon=":material/folder:", key=f"menu_p_{i}",
                                      use_container_width=True, on_click=add_to_project, args=(pname,))
                        st.button("New project", icon=":material/add:", key="menu_newproject",
                                  use_container_width=True, on_click=set_panel, args=("newproject",))

        with c_chat:
            st.markdown("<div class='chat-pill'>Chat</div>", unsafe_allow_html=True)

        with c_mic:
            with st.container(key="mic_wrap"):
                with st.popover("🎤"):
                    if hasattr(st, "audio_input"):
                        st.audio_input("Record a voice message", key="mic_audio", on_change=transcribe_audio)
                    else:
                        st.caption("Update Streamlit to use voice input.")

        with c_send:
            st.button("↑", key="send_btn", type="primary", on_click=send_message)

    # Hidden button used by the Ctrl+U shortcut
    st.button("hidden upload", key="hidden_upload", on_click=set_panel, args=("upload",))

    # Enter = send, Shift+Enter = new line, Ctrl+U = upload
    components.html("""
    <script>
    (function () {
      var P = window.parent, doc = P.document;
      if (P.__chandlioKeys) { doc.removeEventListener("keydown", P.__chandlioKeys, true); }
      P.__chandlioKeys = function (e) {
        var t = e.target;
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing && t && t.tagName === "TEXTAREA"
            && t.closest(".st-key-inputbar")) {
          e.preventDefault(); e.stopPropagation();
          t.blur();
          setTimeout(function () {
            var b = doc.querySelector(".st-key-send_btn button");
            if (b) b.click();
          }, 150);
        }
        if ((e.ctrlKey || e.metaKey) && (e.key === "u" || e.key === "U")) {
          e.preventDefault();
          var h = doc.querySelector(".st-key-hidden_upload button");
          if (h) h.click();
        }
      };
      doc.addEventListener("keydown", P.__chandlioKeys, true);
    })();
    </script>
    """, height=0)

# ---------------- MAIN WINDOW ----------------
if st.session_state.get("toast"):
    st.toast(st.session_state.pop("toast"))

active_key = st.session_state["stored_groq_key"]

if not active_key:
    st.markdown("<br><br><h1 style='text-align: center; color: #ffffff;'>⚡ Welcome to Chandlio's AI Bot</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a1a1aa;'>Please enter your free Groq API key in the left sidebar to unlock the application.</p>", unsafe_allow_html=True)
    st.stop()

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
                        messages_payload = [("system", build_system_prompt())]
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

            if "```" in answer or len(answer) > 300:
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
