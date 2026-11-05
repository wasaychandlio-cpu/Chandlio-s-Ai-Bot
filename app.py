import streamlit as st
import streamlit.components.v1 as components
import os
import io
import base64
import hashlib
import pathlib
import tempfile
import requests
import html as _html

st.set_page_config(page_title="Chandlio's AI Bot", page_icon="⚡", layout="wide")

GREETING = "Let’s have a think"      # <- change the home-screen heading here
MODEL_LABEL, MODEL_NOTE = "gpt-oss-120b", "Fast"

# Claude-style starburst logo (data URI so the markdown sanitizer keeps it)
_STAR_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">'
             '<g stroke="#d97757" stroke-width="3.2" stroke-linecap="round">'
             + "".join(f'<line x1="20" y1="20" x2="20" y2="4" transform="rotate({a} 20 20)"/>' for a in range(0, 360, 30))
             + "</g></svg>")
STAR_URI = "data:image/svg+xml;base64," + base64.b64encode(_STAR_SVG.encode()).decode()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500&display=swap');
:root { --serif: "Source Serif 4", "Tiempos Text", Georgia, "Times New Roman", serif; }

.stApp { background-color: #191919; color: #ffffff; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbarActions"], [data-testid="stMainMenu"] { display: none !important; }
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #ffffff !important; }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 2rem !important; padding-bottom: 7rem !important; }
.stMarkdown table { display: block; max-width: 100%; overflow-x: auto; }
.stMarkdown pre, .stMarkdown code { white-space: pre-wrap !important; word-break: break-word; }
.stMarkdown img, [data-testid="stImage"] img { max-width: 100% !important; height: auto; border-radius: 10px; }
.stMarkdown a { word-break: break-word; }

/* ---------- Home screen (serif heading + plan pill) ---------- */
.plan-wrap { text-align: center; margin-bottom: 3.2rem; }
.plan-pill { display: inline-block; background: #222; border: 1px solid #2f2f2f; color: #a8a8a8;
    border-radius: 12px; padding: 6px 16px; font-size: .95rem; }
.hero { font-family: var(--serif); font-weight: 400; font-size: 3rem; color: #f5f4ef;
    display: flex; align-items: center; justify-content: center; gap: .9rem; margin: 0 0 1.8rem; line-height: 1.1; }
.hero img { width: 40px; height: 40px; }

/* ---------- Chat messages (user = box, assistant = plain serif text) ---------- */
[data-testid="stChatMessage"] { background: transparent !important; border: none !important; padding: .4rem 0 !important; }
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"],
[data-testid="stChatMessageAvatarCustom"] { display: none !important; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: #262626 !important; border-radius: 14px !important; padding: .7rem 1rem !important; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stMarkdownContainer"] {
    font-family: var(--serif); font-size: 1.05rem; line-height: 1.7; color: #ececec; }

/* Simple answers: small headings, tidy lists, no divider lines */
[data-testid="stChatMessage"] .stMarkdown h1,
[data-testid="stChatMessage"] .stMarkdown h2,
[data-testid="stChatMessage"] .stMarkdown h3,
[data-testid="stChatMessage"] .stMarkdown h4 {
    font-family: var(--serif); font-size: 1.1rem !important; font-weight: 600 !important; line-height: 1.4 !important;
    margin: 1.1rem 0 .25rem 0 !important; padding: 0 !important; }
[data-testid="stChatMessage"] .stMarkdown p,
[data-testid="stChatMessage"] .stMarkdown li { font-size: 1.05rem; line-height: 1.7; }
[data-testid="stChatMessage"] .stMarkdown ul,
[data-testid="stChatMessage"] .stMarkdown ol { padding-left: 1.4rem; margin: .3rem 0; }
[data-testid="stChatMessage"] .stMarkdown li { margin: .15rem 0; }
[data-testid="stChatMessage"] .stMarkdown hr { display: none; }
[data-testid="stChatMessage"] .stMarkdown strong { font-weight: 600; }

/* ---------- Sidebar (flat Claude-style nav) ---------- */
[data-testid="stSidebar"] { background-color: #1f1f1e; border-right: 1px solid #2a2a2a; }
.brand { font-family: var(--serif); font-size: 1.7rem; color: #f5f4ef; padding: .2rem .4rem .6rem; }
.side-label { color: #9a9a9a; font-size: .9rem; padding: .9rem .7rem .2rem; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .15rem; }
[data-testid="stSidebar"] button { background: transparent !important; border: none !important; color: #e8e8e8 !important;
    justify-content: flex-start !important; text-align: left !important; padding: .42rem .7rem !important;
    border-radius: 10px !important; min-height: 0 !important; font-size: 1rem !important; box-shadow: none !important; }
[data-testid="stSidebar"] button > div, [data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] {
    justify-content: flex-start !important; text-align: left !important; width: auto; }
[data-testid="stSidebar"] button p { text-align: left !important; }
[data-testid="stSidebar"] button:hover { background: #2a2a29 !important; }
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] { background: #2f2f2e !important; }
[data-testid="stSidebar"] [data-testid="stExpander"] { border: none !important; }
[data-testid="stSidebar"] .stTextInput input { background: #252525 !important; color: #fff !important; border: 1px solid #333 !important; border-radius: 8px !important; }

/* ---------- Input bar (medium width = same as the chat column, sticky, rounded) ---------- */
[data-testid="stLayoutWrapper"]:has(> .st-key-inputbar),
[data-testid="stElementContainer"]:has(> .st-key-inputbar) { display: contents !important; }
.st-key-inputbar { position: sticky !important; bottom: 1rem; z-index: 999;
    width: 100%; max-width: 760px; margin: 1rem auto 0 auto;
    background: #2b2b2b; border: 1px solid #3d3d3d; border-radius: 22px; padding: 10px 14px 12px 14px;
    max-height: 75vh; overflow-y: auto; overflow-x: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.45); }
.st-key-inputbar .stTextArea, .st-key-inputbar .stTextArea > div, .st-key-inputbar .stTextArea > div > div,
.st-key-inputbar [data-baseweb="textarea"], .st-key-inputbar [data-baseweb="base-input"] {
    background: transparent !important; border: none !important; box-shadow: none !important; }
.st-key-inputbar .stTextArea [data-baseweb="textarea"], .st-key-inputbar .stTextArea [data-baseweb="base-input"],
.st-key-inputbar .stTextArea textarea { height: 52px !important; min-height: 52px !important; }
.st-key-inputbar .stTextArea textarea { background: transparent !important; border: none !important; box-shadow: none !important;
    resize: none !important; font-size: 1.05rem !important; color: #fff !important; padding: 4px 4px !important; }
.st-key-inputbar .stTextArea textarea::placeholder { color: #8a8a8a !important; }
.st-key-inputbar [data-testid="InputInstructions"], .st-key-inputbar [data-testid="stTextAreaInstructions"] { display: none !important; }
.st-key-inputbar [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .3rem !important; align-items: center !important; }
.st-key-inputbar [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-inputbar [data-testid="stElementContainer"] { margin: 0 !important; }
.st-key-inputbar [data-testid="stMarkdownContainer"] p { margin: 0 !important; }
.st-key-inputbar button:focus, .st-key-inputbar button:focus-visible { outline: none !important; box-shadow: none !important; }

/* + button, mic, send: flat icon buttons */
.st-key-inputbar [data-testid="stPopover"] button, .st-key-send_btn button {
    background: transparent !important; border: none !important; color: #e6e6e6 !important;
    padding: 0 .5rem !important; min-height: 2.1rem !important; border-radius: 10px !important; }
.st-key-inputbar [data-testid="stPopover"] button:hover, .st-key-send_btn button:hover { background: #3a3a3a !important; }
.st-key-plus_wrap [data-testid="stPopover"] button { font-size: 1.7rem !important; font-weight: 300 !important; }
.st-key-plus_wrap [data-testid="stPopover"] button svg,
.st-key-plus_wrap [data-testid="stPopover"] button [data-testid="stIconMaterial"] { display: none !important; }
.st-key-send_btn button { font-size: 1.3rem !important; }

/* Chat | Cowork toggle + model label */
.seg { display: inline-flex; background: #232323; border: 1px solid #3a3a3a; border-radius: 10px; padding: 2px; }
.seg span { padding: 4px 13px; border-radius: 8px; color: #a8a8a8; font-size: .95rem; }
.seg .on { background: #3d3d3d; color: #fff; }
.model-label { text-align: right; white-space: nowrap; color: #fff; font-size: .95rem; }
.model-label span { color: #9a9a9a; margin-left: .3rem; }
@media (max-width: 640px) { .model-label { display: none; } }

/* ---------- + menu (left aligned, compact, like Claude) ---------- */
[data-testid="stPopoverBody"] { background: #2b2b2b !important; border: 1px solid #3d3d3d !important; border-radius: 16px !important;
    width: 330px !important; min-width: 330px !important; padding: .4rem !important; max-height: 85vh !important; }
[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] { gap: .1rem !important; }
[data-testid="stPopoverBody"] hr { margin: .3rem .5rem !important; border-color: #3d3d3d !important; }
[data-testid="stPopoverBody"] [data-testid="stElementContainer"] { margin: 0 !important; }
[class*="st-key-menu_"] button { display: flex !important; justify-content: flex-start !important; text-align: left !important;
    gap: .6rem; width: 100%; background: transparent !important; border: none !important; color: #fff !important;
    padding: .45rem .7rem !important; border-radius: 10px !important; font-size: 1rem !important; min-height: 0 !important; }
[class*="st-key-menu_"] button > div, [class*="st-key-menu_"] button [data-testid="stMarkdownContainer"] {
    justify-content: flex-start !important; text-align: left !important; flex: 0 1 auto; width: auto; }
[class*="st-key-menu_"] button p { text-align: left !important; }
[class*="st-key-menu_"] button:hover { background: #3a3a3a !important; }
.st-key-menu_upload button::after { content: "Ctrl+U"; margin-left: auto; color: #9a9a9a; font-size: .95rem; }
.st-key-menu_project button::after, .st-key-menu_skills button::after,
.st-key-menu_connector button::after, .st-key-menu_design button::after { content: "›"; margin-left: auto; color: #aaa; font-size: 1.5rem; line-height: 1; }
.st-key-menu_web_on button::after { content: "✓"; margin-left: auto; color: #4a9eff; font-size: 1.3rem; }
.st-key-hidden_upload { display: none; }

/* ---------- Starter chips under the input bar ---------- */
.st-key-chips [data-testid="stHorizontalBlock"] { justify-content: center; flex-wrap: wrap !important; gap: .5rem !important; margin-top: 1.4rem; }
.st-key-chips [data-testid="stColumn"] { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
.st-key-chips button { background: #222 !important; border: 1px solid #333 !important; border-radius: 12px !important;
    color: #e0e0e0 !important; padding: .35rem .95rem !important; min-height: 2.4rem !important; }
.st-key-chips button:hover { background: #2c2c2c !important; }

/* ---------- Visible page scrollbar ---------- */
[data-testid="stMain"], .stMain, section.main { overflow-y: scroll !important; }
[data-testid="stMain"]::-webkit-scrollbar { width: 14px !important; background: #1e1e1e !important; }
[data-testid="stMain"]::-webkit-scrollbar-track { background: #1e1e1e !important; }
[data-testid="stMain"]::-webkit-scrollbar-thumb { background: #6b6b6b !important; border-radius: 8px !important; border: 3px solid #1e1e1e !important; }
[data-testid="stMain"]::-webkit-scrollbar-thumb:hover { background: #9a9a9a !important; }

/* ---------- Top bar (chat title left, Share right) ---------- */
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 4.5rem !important; }
.topbar { position: fixed; top: 0; left: 0; right: 0; height: 3.5rem; display: flex; align-items: center;
    justify-content: space-between; padding: 0 1.4rem; background: #191919; border-bottom: 1px solid #262626; z-index: 99; }
.stApp:has([data-testid="stSidebar"][aria-expanded="true"]) .topbar { left: 21rem; }
.stApp:has([data-testid="stSidebar"][aria-expanded="false"]) .topbar { left: 3.5rem; }
.tb-title { display: flex; align-items: center; gap: .55rem; color: #f2f2f2; font-size: 1.05rem; max-width: 60%;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tb-right { display: flex; align-items: center; gap: 1.1rem; color: #e8e8e8; font-size: 1.05rem; }
.tb-right span { display: inline-flex; align-items: center; gap: .45rem; }
.tb-right svg, .tb-title svg { stroke: #e8e8e8; fill: none; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }

/* ---------- Sidebar nav like Claude ---------- */
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { display: none; }
[data-testid="stSidebar"] .stButton button { display: flex !important; align-items: center !important; gap: .8rem; width: 100%; font-size: 1.05rem !important; }
.st-key-nav_code button::after { content: "Upgrade"; margin-left: auto; color: #5aa9ff; background: #1b2430; border: 1px solid #2c3a4d;
    border-radius: 999px; padding: 1px 12px; font-size: .85rem; }
.side-head { display: flex; align-items: center; justify-content: space-between; color: #f2f2f2; font-weight: 600;
    font-size: 1rem; padding: 1.4rem .7rem .4rem; }
.side-head svg { stroke: #e8e8e8; fill: none; stroke-width: 1.8; stroke-linecap: round; }
.st-key-view_all button { color: #9a9a9a !important; }
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] { background: #3a3a39 !important; }
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
    "projects": {},
    "chat_project": {},
    "attachments": [],
    "panel": None,
    "menu_view": "main",
    "web_search": True,
    "shot_trigger": 0,
    "last_shot_id": None,
    "pending_prompt": None,
    "msg_box": "",
    "upload_nonce": 0,
    "show_projects": False,
    "show_search": False,
    "show_all_chats": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Centered Claude-width column (wider only when the artifact workspace is open)
_col_width = "1200px" if st.session_state["show_workspace"] else "760px"
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

@st.cache_data(show_spinner=False)
def fetch_wiki_image(title):
    """Download the image on the server so the browser never has to hotlink it."""
    try:
        h = {"User-Agent": "ChandlioBot/1.0 (personal project)"}
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                         headers=h, timeout=10)
        thumb = r.json().get("thumbnail", {}).get("source")
        if not thumb:
            return None
        big = thumb.replace("/320px-", "/1000px-")
        for url in (big, thumb):
            img = requests.get(url, headers=h, timeout=15)
            if img.ok and img.headers.get("content-type", "").startswith("image/"):
                return img.content
    except Exception:
        pass
    return None


def chat_title(name):
    for m in st.session_state["chat_sessions"].get(name, []):
        if m["role"] == "user":
            t = m["content"].strip().replace("\n", " ")
            return (t[:34] + "…") if len(t) > 34 else t
    return "New chat"

def toggle_state(key):
    st.session_state[key] = not st.session_state[key]

def soon(msg):
    st.session_state["toast"] = msg

def build_system_prompt():
    base = ("You are a helpful, direct assistant. Reply like Claude: natural conversational prose, "
            "short paragraphs, no emojis, no horizontal rules and no big headings. "
            "Use a short plain bullet or numbered list only when it really helps. "
            "Put code in code blocks.")
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

def set_starter(text):
    st.session_state["msg_box"] = text

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
FILTER_SVG = ('<svg width="18" height="18" viewBox="0 0 24 24"><line x1="4" y1="7" x2="20" y2="7"/>'
              '<line x1="7" y1="12" x2="17" y2="12"/><line x1="10" y1="17" x2="14" y2="17"/></svg>')

with st.sidebar:
    st.markdown("<div class='brand'>Chandlio</div>", unsafe_allow_html=True)

    if st.button("New", icon=":material/add:", use_container_width=True, key="nav_new"):
        new_title = f"Chat {len(st.session_state['chat_sessions']) + 1}"
        st.session_state["chat_sessions"][new_title] = []
        st.session_state["current_chat"] = new_title
        st.session_state["show_workspace"] = False
        st.rerun()

    st.button("Search", icon=":material/search:", use_container_width=True, key="nav_search",
              on_click=toggle_state, args=("show_search",))
    search_q = ""
    if st.session_state["show_search"]:
        search_q = st.text_input("Search chats", key="search_q", placeholder="Search chats...",
                                 label_visibility="collapsed").strip().lower()

    st.button("Projects", icon=":material/inventory_2:", use_container_width=True, key="nav_projects",
              on_click=toggle_state, args=("show_projects",))
    if st.session_state["show_projects"]:
        st.button("New project", icon=":material/create_new_folder:", use_container_width=True,
                  key="side_new_project", on_click=set_panel, args=("newproject",))
        active_proj = st.session_state["chat_project"].get(st.session_state["current_chat"])
        for pname, pdata in st.session_state["projects"].items():
            st.button(f"{pname} ({len(pdata['files'])})", use_container_width=True, key=f"proj_{pname}",
                      icon=":material/check_circle:" if pname == active_proj else ":material/folder:",
                      on_click=link_chat_to_project, args=(pname,))

    if st.button("Artifacts", icon=":material/filter_none:", use_container_width=True, key="nav_artifacts"):
        st.session_state["show_workspace"] = True
        st.rerun()

    st.button("Code", icon=":material/code:", use_container_width=True, key="nav_code",
              on_click=soon, args=("Code is not available yet.",))
    st.button("Customize", icon=":material/work:", use_container_width=True, key="nav_customize",
              on_click=soon, args=("Customize is not available yet.",))

    st.markdown(f"<div class='side-head'><span>Chats and tasks &#9662;</span>{FILTER_SVG}</div>",
                unsafe_allow_html=True)

    names = list(st.session_state["chat_sessions"].keys())[::-1]
    if search_q:
        names = [n for n in names if search_q in chat_title(n).lower()]
    limit = len(names) if (st.session_state["show_all_chats"] or search_q) else 8
    for chat_name in names[:limit]:
        is_active = chat_name == st.session_state["current_chat"]
        if st.button(chat_title(chat_name), use_container_width=True, key=f"btn_{chat_name}",
                     type="primary" if is_active else "secondary"):
            st.session_state["current_chat"] = chat_name
            st.rerun()
    if len(names) > 8 and not search_q:
        st.button("Show less" if st.session_state["show_all_chats"] else "View all", key="view_all",
                  use_container_width=True, on_click=toggle_state, args=("show_all_chats",))

    st.markdown("<div class='side-label'></div>", unsafe_allow_html=True)
    with st.expander("Chandlio · Free", icon=":material/settings:",
                     expanded=not st.session_state["stored_groq_key"]):
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
    st.button("hidden upload", key="hidden_upload", on_click=set_panel, args=("upload",))
    run_js(KEYS_AND_SCROLL_JS)

    with st.container(key="inputbar"):
        panel = st.session_state["panel"]

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

        for i, a in enumerate(st.session_state["attachments"]):
            st.button(f"📎 {a['name']}  ✕", key=f"rm_{i}", on_click=remove_attachment, args=(i,))

        st.text_area("Message", key="msg_box", placeholder="How can I help you today?",
                     height=68, label_visibility="collapsed")

        # Bottom row: + | Chat/Cowork | ... | model | mic | send
        c_plus, c_chat, c_space, c_model, c_mic, c_send = st.columns(
            [0.8, 2.6, 3.4, 2.6, 1.0, 0.9], vertical_alignment="center")

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
            st.markdown("<div class='seg'><span class='on'>Chat</span><span>Cowork</span></div>",
                        unsafe_allow_html=True)

        with c_model:
            st.markdown(f"<div class='model-label'>{MODEL_LABEL}<span>{MODEL_NOTE}</span></div>",
                        unsafe_allow_html=True)

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
            st.button(" ", icon=":material/keyboard_return:", key="send_btn", on_click=send_message)

def render_starter_chips():
    chips = [("Write", ":material/edit:", "Help me write "),
             ("Learn", ":material/school:", "Teach me about "),
             ("Code", ":material/code:", "Help me write code that "),
             ("Life stuff", ":material/coffee:", "I need advice on "),
             ("Chandlio’s choice", ":material/lightbulb:", "Surprise me with something interesting.")]
    with st.container(key="chips"):
        cols = st.columns(len(chips))
        for col, (label, icon, text) in zip(cols, chips):
            with col:
                st.button(label, icon=icon, key=f"chip_{label}", on_click=set_starter, args=(text,))

# ---------------- MAIN WINDOW ----------------
if st.session_state.get("toast"):
    st.toast(st.session_state.pop("toast"))

active_key = st.session_state["stored_groq_key"]

if not active_key:
    st.markdown(f"<div style='height:14vh'></div><div class='hero'><img src='{STAR_URI}'>Welcome to Chandlio</div>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a1a1aa;'>Please enter your free Groq API key in the left sidebar to unlock the application.</p>", unsafe_allow_html=True)
    st.stop()

_DOC_SVG = '<svg width="20" height="20" viewBox="0 0 24 24"><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/></svg>'
_SHARE_SVG = '<svg width="20" height="20" viewBox="0 0 24 24"><path d="M12 15V4"/><path d="M8 8l4-4 4 4"/><path d="M5 13v7h14v-7"/></svg>'
_CHEV_SVG = '<svg width="16" height="16" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>'
st.markdown(
    f"<div class='topbar'><div class='tb-title'>{_html.escape(chat_title(st.session_state['current_chat']))} {_CHEV_SVG}</div>"
    f"<div class='tb-right'>{_DOC_SVG}<span>{_SHARE_SVG}Share</span></div></div>",
    unsafe_allow_html=True)

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

        if not current_messages and st.session_state["pending_prompt"] is None:
            st.markdown(
                f"<div style='height:12vh'></div>"
                f"<div class='plan-wrap'><span class='plan-pill'>Free plan · Groq</span></div>"
                f"<div class='hero'><img src='{STAR_URI}'>{GREETING}</div>",
                unsafe_allow_html=True)

        for msg in current_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                for f in msg.get("files", []):
                    if is_image(f):
                        st.image(f["data"], width=300)
                    else:
                        st.caption(f"📎 {f['name']}")
                for img in msg.get("images", []):
                    st.image(img, use_container_width=True)

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
                        answer = "Here are some views of Switzerland:"
                        found_images = [b for b in (fetch_wiki_image(t) for t in
                                        ["Matterhorn", "Jungfrau", "Lake_Lucerne"]) if b]
                        if not found_images:
                            answer = "I couldn't load the images right now. Please try again."
                    else:
                        messages_payload = [("system", build_system_prompt())]
                        for m in current_messages:
                            messages_payload.append((m["role"], message_text(m)))
                        response = llm.invoke(messages_payload)
                        answer = response.content
                        found_images = []

                    st.markdown(answer)
                    for img in found_images:
                        st.image(img, use_container_width=True)

            current_messages.append({"role": "assistant", "content": answer, "images": found_images})

            # Keep the latest code answer for the Artifacts button, but do NOT split the screen automatically
            if "```" in answer:
                st.session_state["workspace_content"] = answer

    if st.session_state["show_workspace"]:
        with workspace_pane:
            col_title, col_close = st.columns([4, 1])
            with col_title:
                st.markdown("<h3 style='color: #ffffff;'>Artifacts</h3>", unsafe_allow_html=True)
            with col_close:
                if st.button("✕ Close"):
                    st.session_state["show_workspace"] = False
                    st.rerun()
            st.code(st.session_state["workspace_content"], language="markdown")

except Exception as e:
    st.error(f"Error: {e}")

# Input bar (sticky) + starter chips on an empty chat
try:
    render_input_bar()
    if not st.session_state["chat_sessions"][st.session_state["current_chat"]] and st.session_state["panel"] is None:
        render_starter_chips()
except Exception as e:
    st.error(f"Input bar failed to load: {e}")
