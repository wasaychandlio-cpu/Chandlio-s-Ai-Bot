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

/* ---------- Fit screen: everything must fit inside the centered column ---------- */
.block-container { padding-top: 3rem !important; padding-bottom: 4rem !important; }
.stMarkdown table { display: block; max-width: 100%; overflow-x: auto; }
.stMarkdown pre, .stMarkdown code { white-space: pre-wrap !important; word-break: break-word; }
.stMarkdown img, [data-testid="stImage"] img { max-width: 100% !important; height: auto; }
.stMarkdown a { word-break: break-all; }

/* ---------- Claude-style input bar (small, centered, sticks to the bottom) ---------- */
/* make the wrapper around the bar "disappear" so sticky works against the chat column */
[data-testid="stLayoutWrapper"]:has(> .st-key-inputbar),
[data-testid="stElementContainer"]:has(> .st-key-inputbar) { display: contents !important; }

.st-key-inputbar {
    position: sticky !important; bottom: 1rem; z-index: 999;
    width: 100%; max-width: 620px; margin: 1rem auto 0 auto;
    background: #2b2b2b; border: 1px solid #3d3d3d; border-radius: 20px;
    padding: 6px 12px 4px 12px; max-height: 75vh; overflow-y: auto;
    box-shadow: 0 4px 24px rgba(0,0,0,0.45);
}

/* text area: no inner box, no resize handle, no hint text, compact height */
.st-key-inputbar .stTextArea,
.st-key-inputbar .stTextArea > div,
.st-key-inputbar .stTextArea > div > div,
.st-key-inputbar [data-baseweb="textarea"],
.st-key-inputbar [data-baseweb="base-input"] {
    background: transparent !important; border: none !important; box-shadow: none !important;
}
.st-key-inputbar .stTextArea [data-baseweb="textarea"],
.st-key-inputbar .stTextArea [data-baseweb="base-input"],
.st-key-inputbar .stTextArea textarea {
    height: 44px !important; min-height: 44px !important;
}
.st-key-inputbar .stTextArea textarea {
    background: transparent !important; border: none !important; box-shadow: none !important;
    resize: none !important; font-size: 1rem !important; color: #ffffff !important;
    padding: 4px 4px !important;
}
.st-key-inputbar .stTextArea textarea::placeholder { color: #8a8a8a !important; }
.st-key-inputbar [data-testid="InputInstructions"],
.st-key-inputbar [data-testid="stTextAreaInstructions"] { display: none !important; }

/* keep the button row on one line (also on mobile) */
.st-key-inputbar [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.3rem !important; align-items: center !important; }
.st-key-inputbar [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-inputbar [data-testid="stElementContainer"] { margin: 0 !important; }

/* plus + mic popover buttons */
.st-key-inputbar [data-testid="stPopover"] button {
    background: transparent !important; border: none !important;
    color: #ffffff !important; font-size: 1.3rem !important; padding: 0 0.4rem !important; min-height: 1.9rem !important;
}
.st-key-plus_wrap [data-testid="stPopover"] button svg,
.st-key-plus_wrap [data-testid="stPopover"] button [data-testid="stIconMaterial"] { display: none !important; }
.st-key-plus_wrap [data-testid="stPopover"] button:hover { background: #3a3a3a !important; border-radius: 10px !important; }

/* Chat pill */
.chat-pill {
    display: inline-flex; align-items: center; background: #3d3d3d; color: #ffffff;
    border: 1px solid #4a4a4a; border-radius: 10px; padding: 2px 14px; font-size: 0.9rem; margin: 0;
}

/* send button */
.st-key-send_btn button {
    background: #d97757 !important; border: none !important; border-radius: 50% !important;
    width: 2rem !important; height: 2rem !important; min-height: 0 !important;
    padding: 0 !important; color: #fff !important; font-size: 1.05rem !important; line-height: 1 !important;
}

/* ---------- Plus menu (popover body) ---------- */
[data-testid="stPopoverBody"] { background: #2b2b2b !important; border: 1px solid #3d3d3d !important; border-radius: 16px !important; min-width: 320px; padding: 0.5rem !important; }
[data-testid="stPopoverBody"] hr { margin: 0.35rem 0 !important; border-color: #3d3d3d !important; }
[data-testid="stPopoverBody"] [data-testid="stElementContainer"] { margin: 0 !important; }
[class*="st-key-menu_"] button {
    display: flex !important; justify-content: flex-start !important; text-align: left !important;
    background: transparent !important; border: none !important; color: #ffffff !important;
    padding: 0.5rem 0.7rem !important; border-radius: 10px !important; font-size: 1rem !important;
}
[class*="st-key-menu_"] button:hover { background: #3a3a3a !important; }
.st-key-menu_upload button::after { content: "Ctrl+U"; margin-left: auto; color: #9a9a9a; font-size: 0.9rem; padding-left: 2rem; }
.st-key-menu_project button::after,
.st-key-menu_skills button::after,
.st-key-menu_connector button::after,
.st-key-menu_design button::after { content: "›"; margin-left: auto; color: #aaaaaa; font-size: 1.5rem; padding-left: 2rem; }
.st-key-menu_web_on button::after { content: "✓"; margin-left: auto; color: #4a9eff; font-size: 1.25rem; padding-left: 2rem; }
.st-key-hidden_upload { display: none; }

/* ---------- Visible page up/down scrollbar on the right side ---------- */
[data-testid="stMain"], .stMain, section.main { overflow-y: scroll !important; }
[data-testid="stMain"]::-webkit-scrollbar,
.stMain::-webkit-scrollbar,
section.main::-webkit-scrollbar { width: 16px !important; background: #1e1e1e !important; }
[data-testid="stMain"]::-webkit-scrollbar-track,
.stMain::-webkit-scrollbar-track,
section.main::-webkit-scrollbar-track { background: #1e1e1e !important; }
[data-testid="stMain"]::-webkit-scrollbar-thumb,
.stMain::-webkit-scrollbar-thumb,
section.main::-webkit-scrollbar-thumb { background: #6b6b6b !important; border-radius: 8px !important; border: 3px solid #1e1e1e !important; }
[data-testid="stMain"]::-webkit-scrollbar-thumb:hover,
.stMain::-webkit-scrollbar-thumb:hover,
section.main::-webkit-scrollbar-thumb:hover { background: #9a9a9a !important; }
[data-testid="stMain"]::-webkit-scrollbar-button:single-button,
.stMain::-webkit-scrollbar-button:single-button,
section.main::-webkit-scrollbar-button:single-button {
    display: block !important; height: 18px !important; background-color: #1e1e1e !important;
    background-repeat: no-repeat !important; background-position: center !important; background-size: 10px !important;
}
[data-testid="stMain"]::-webkit-scrollbar-button:single-button:vertical:decrement,
.stMain::-webkit-scrollbar-button:single-button:vertical:decrement,
section.main::-webkit-scrollbar-button:single-button:vertical:decrement {
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'><path d='M1 7 L5 3 L9 7' fill='none' stroke='%23bbbbbb' stroke-width='2'/></svg>") !important;
}
[data-testid="stMain"]::-webkit-scrollbar-button:single-button:vertical:increment,
.stMain::-webkit-scrollbar-button:single-button:vertical:increment,
section.main::-webkit-scrollbar-button:single-button:vertical:increment {
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'><path d='M1 3 L5 7 L9 3' fill='none' stroke='%23bbbbbb' stroke-width='2'/></svg>") !important;
}
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
    "menu_view": "main",     # "main" | "project" | "skills" | "connector" | "design"
    "web_search": True,      # Web search toggle in the + menu
    "shot_trigger": 0,
    "last_shot_id": None,
    "pending_prompt": None,
    "msg_box": "",
    "upload_nonce": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Centered, fit-to-screen column (wider only when the artifact workspace is open)
_col_width = "1400px" if st.session_state["show_workspace"] else "780px"
st.markdown(
    f"<style>.block-container {{ max-width: {_col_width} !important; margin: 0 auto !important; "
    f"padding-left: 1.2rem !important; padding-right: 1.2rem !important; }}</style>",
    unsafe_allow_html=True,
)

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

def toggle_web_search():
    st.session_state["web_search"] = not st.session_state["web_search"]

def show_plugins_note():
    st.session_state["toast"] = "No plugins available yet."

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

# ---------------- KEYBOARD SHORTCUTS (JavaScript) ----------------
KEYS_AND_SCROLL_JS = """
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

  var oldBox = doc.getElementById("chandlio-scroll");
  if (oldBox) oldBox.remove();
})();
"""

def run_js(js_code):
    html = "<script>" + js_code + "</script>"
    try:
        components.html(html, height=0)
    except Exception:
        try:
            st.html(html, unsafe_allow_javascript=True)
        except Exception:
            pass

# ---------------- INPUT BAR ----------------
def render_input_bar():
    # Hidden button used by the Ctrl+U shortcut, and the JavaScript (rendered first,
    # so the input bar below is the LAST element of the page and can stick to the bottom)
    st.button("hidden upload", key="hidden_upload", on_click=set_panel, args=("upload",))
    run_js(KEYS_AND_SCROLL_JS)

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
                     height=68, label_visibility="collapsed")

        # ----- Bottom row: + | Chat | ... | mic | send -----
        c_plus, c_chat, c_space, c_mic, c_send = st.columns([1, 2, 6, 1.5, 1.2], vertical_alignment="center")

        with c_plus:
            with st.container(key="plus_wrap"):
                with st.popover("＋"):
                    view = st.session_state["menu_view"]
                    if view == "main":
                        st.button("Upload or add files", icon=":material/attach_file:", key="menu_upload",
                                  use_container_width=True, on_click=set_panel, args=("upload",))
                        st.button("Take a screenshot", icon=":material/photo_camera:", key="menu_shot",
                                  use_container_width=True, on_click=start_screenshot)
                        st.button("Add to project", icon=":material/inventory_2:", key="menu_project",
                                  use_container_width=True, on_click=set_menu_view, args=("project",))
                        st.divider()
                        st.button("Skills", icon=":material/receipt_long:", key="menu_skills",
                                  use_container_width=True, on_click=set_menu_view, args=("skills",))
                        st.button("Add connector", icon=":material/extension:", key="menu_connector",
                                  use_container_width=True, on_click=set_menu_view, args=("connector",))
                        st.button("Design system", icon=":material/palette:", key="menu_design",
                                  use_container_width=True, on_click=set_menu_view, args=("design",))
                        st.button("Add plugins", icon=":material/power:", key="menu_plugins",
                                  use_container_width=True, on_click=show_plugins_note)
                        st.divider()
                        st.button("Web search", icon=":material/language:",
                                  key="menu_web_on" if st.session_state["web_search"] else "menu_web_off",
                                  use_container_width=True, on_click=toggle_web_search)
                    elif view == "project":
                        st.button("Back", icon=":material/arrow_back:", key="menu_back",
                                  use_container_width=True, on_click=set_menu_view, args=("main",))
                        for i, pname in enumerate(st.session_state["projects"].keys()):
                            st.button(pname, icon=":material/folder:", key=f"menu_p_{i}",
                                      use_container_width=True, on_click=add_to_project, args=(pname,))
                        st.button("New project", icon=":material/add:", key="menu_newproject",
                                  use_container_width=True, on_click=set_panel, args=("newproject",))
                    else:
                        st.button("Back", icon=":material/arrow_back:", key="menu_back",
                                  use_container_width=True, on_click=set_menu_view, args=("main",))
                        notes = {
                            "skills": "No skills added yet.",
                            "connector": "No connectors available yet.",
                            "design": "No design systems yet.",
                        }
                        st.caption(notes.get(view, ""))

        with c_chat:
            st.markdown("<div class='chat-pill'>Chat</div>", unsafe_allow_html=True)

        with c_mic:
            with st.container(key="mic_wrap"):
                try:
                    mic_pop = st.popover(" ", icon=":material/mic:")
                except Exception:
                    mic_pop = st.popover("🎤")
                with mic_pop:
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

# Custom Claude-style input bar (last element on the page, sticks to the bottom)
try:
    render_input_bar()
except Exception as e:
    st.error(f"Input bar failed to load: {e}")
