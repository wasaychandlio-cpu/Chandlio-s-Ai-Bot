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
ACCOUNT_EMAIL = "mabdulwasay81@gmail.com"   # <- shown at the top of the account menu
AI_NAME = "Chandlio"                 # <- the AI name used in every label (replaces "Claude")

# ---------------- LOGO ----------------
# Put your logo image (png / jpg / jpeg / webp) in the same folder as app.py.
# Any file whose name starts with "logo" is accepted (logo.png, logo.jpg, logo.png.png ...).
# If nothing valid is found, the Claude-style starburst is shown, so you never get a broken image.
_LOGO_B64 = ""   # optional: paste a base64 logo string here instead of using a file

_STAR_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">'
             '<g stroke="#d97757" stroke-width="3.2" stroke-linecap="round">'
             + "".join(f'<line x1="20" y1="20" x2="20" y2="4" transform="rotate({a} 20 20)"/>' for a in range(0, 360, 30))
             + "</g></svg>")

def _sniff_mime(raw):
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return None

def _load_logo():
    try:
        folders = [pathlib.Path(__file__).resolve().parent, pathlib.Path.cwd()]
        exts = (".png", ".jpg", ".jpeg", ".webp")
        for folder in folders:
            if not folder.is_dir():
                continue
            files = sorted(p for p in folder.iterdir()
                           if p.is_file() and p.name.lower().startswith("logo") and p.name.lower().endswith(exts))
            for p in files:
                raw = p.read_bytes()
                mime = _sniff_mime(raw)
                if mime:
                    return f"data:{mime};base64," + base64.b64encode(raw).decode()
    except Exception:
        pass
    return None

def _b64_logo_uri(b64):
    try:
        raw = base64.b64decode(b64.strip(), validate=True)
    except Exception:
        return None
    mime = _sniff_mime(raw)
    return f"data:{mime};base64,{b64.strip()}" if mime else None

_STAR_FALLBACK_URI = "data:image/svg+xml;base64," + base64.b64encode(_STAR_SVG.encode()).decode()
STAR_URI = _load_logo() or (_b64_logo_uri(_LOGO_B64) if _LOGO_B64.strip() else None) or _STAR_FALLBACK_URI

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

/* zero-height helper iframes (JS runners) must not add gaps to the layout */
[data-testid="stElementContainer"]:has(> iframe[height="0"]) {
    position: absolute !important; width: 0 !important; height: 0 !important; overflow: hidden !important; margin: 0 !important; }

/* ---------- Home screen (serif heading + plan pill) ---------- */
.plan-wrap { text-align: center; margin-bottom: 3.2rem; }
.plan-pill { display: inline-block; background: #222; border: 1px solid #2f2f2f; color: #a8a8a8;
    border-radius: 12px; padding: 6px 16px; font-size: .95rem; }
.hero { font-family: var(--serif); font-weight: 400; font-size: 3rem; color: #f5f4ef;
    display: flex; align-items: center; justify-content: center; gap: .9rem; margin: 0 0 1.8rem; line-height: 1.1; }
.hero img { height: 64px; width: auto; border-radius: 0 !important; mix-blend-mode: screen; }

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
    border-radius: 10px !important; min-height: 0 !important; font-size: 1rem !important; box-shadow: none !important;
    overflow: hidden; }
[data-testid="stSidebar"] button > div, [data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] {
    justify-content: flex-start !important; text-align: left !important; width: auto; min-width: 0; }
[data-testid="stSidebar"] button p { text-align: left !important; white-space: nowrap !important;
    overflow: hidden; text-overflow: ellipsis; }
[data-testid="stSidebar"] button:hover { background: #2a2a29 !important; }
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] { background: #2f2f2e !important; }
[data-testid="stSidebar"] [data-testid="stExpander"] { border: none !important; }
[data-testid="stSidebar"] .stTextInput input { background: #252525 !important; color: #fff !important; border: 1px solid #333 !important; border-radius: 8px !important; }

/* ---------- Input bar: rounded box docked at the bottom (like Claude) ---------- */
[data-testid="stLayoutWrapper"]:has(> .st-key-inputbar),
[data-testid="stElementContainer"]:has(> .st-key-inputbar) { display: contents !important; }
.st-key-inputbar { position: sticky !important; bottom: 0; z-index: 999;
    width: 100%; max-width: 760px; margin: 1rem auto 0 auto;
    background: #191919; padding: .5rem 0 .3rem 0; }
.st-key-pill { background: #2b2b2b; border: 1px solid #3d3d3d; border-radius: 26px;
    padding: 8px 12px 8px 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.45); gap: .2rem !important; }
.st-key-inputbar .stTextArea, .st-key-inputbar .stTextArea > div, .st-key-inputbar .stTextArea > div > div,
.st-key-inputbar [data-baseweb="textarea"], .st-key-inputbar [data-baseweb="base-input"] {
    background: transparent !important; border: none !important; box-shadow: none !important; }
.st-key-inputbar .stTextArea [data-baseweb="textarea"], .st-key-inputbar .stTextArea [data-baseweb="base-input"] {
    height: auto !important; min-height: 44px !important; }
.st-key-inputbar .stTextArea textarea { background: transparent !important; border: none !important; box-shadow: none !important;
    resize: none !important; font-size: 1.05rem !important; line-height: 1.5 !important; color: #fff !important;
    padding: 9px 8px !important; height: 44px; min-height: 44px !important; max-height: 200px !important; overflow-y: auto; }
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
    padding: 0 .5rem !important; min-height: 2.4rem !important; border-radius: 10px !important; }
.st-key-inputbar [data-testid="stPopover"] button:hover, .st-key-send_btn button:hover { background: #3a3a3a !important; }
.st-key-plus_wrap [data-testid="stPopover"] button { font-size: 1.7rem !important; font-weight: 300 !important; }
.st-key-plus_wrap [data-testid="stPopover"] button svg,
.st-key-plus_wrap [data-testid="stPopover"] button [data-testid="stIconMaterial"] { display: none !important; }
.st-key-send_btn button { font-size: 1.3rem !important; }

/* Chat | Cowork toggle (bottom-left of the box) */
.st-key-mode_wrap [data-testid="stButtonGroup"], .st-key-mode_wrap [role="radiogroup"] {
    background: #222; border: 1px solid #353535; border-radius: 12px; padding: 2px; gap: 2px; width: fit-content; }
.st-key-mode_wrap [data-testid^="stBaseButton-segmented"], .st-key-mode_wrap [role="radiogroup"] label {
    background: transparent !important; border: none !important; outline: none !important; color: #9a9a9a !important;
    border-radius: 9px !important; min-height: 2rem !important; padding: 0 .9rem !important; box-shadow: none !important; }
.st-key-mode_wrap [data-testid^="stBaseButton-segmented"] p { color: inherit !important; }
.st-key-mode_wrap [data-testid^="stBaseButton-segmented"][data-testid$="Active"],
.st-key-mode_wrap [data-testid^="stBaseButton-segmented"][aria-pressed="true"],
.st-key-mode_wrap [data-testid^="stBaseButton-segmented"][aria-checked="true"] {
    background: #3a3a3a !important; color: #ffffff !important; border: none !important; outline: none !important; }

/* model label inside the box (bottom-right) */
.st-key-inputbar [data-testid="stMarkdown"], .st-key-inputbar [data-testid="stMarkdownContainer"] { margin: 0 !important; padding: 0 !important; }
.mdl-in { color: #ffffff; white-space: nowrap; font-size: .95rem; height: 2.4rem; line-height: 2.4rem;
    display: flex; align-items: center; justify-content: flex-end; }
.mdl-in b { color: #9a9a9a; font-weight: 400; margin-left: .35rem; }
@media (max-width: 640px) { .mdl-in { display: none; } }

/* footer under the box */
.input-foot { display: flex; justify-content: center; align-items: center; gap: 1rem;
    padding: .55rem .9rem 0; color: #8a8a8a; font-size: .85rem; }
@media (max-width: 640px) { .input-foot .dis { font-size: .75rem; } }

/* ---------- + menu and account menu (left aligned, compact, like Claude) ---------- */
[data-testid="stPopoverBody"] { background: #2b2b2b !important; border: 1px solid #3d3d3d !important; border-radius: 16px !important;
    width: 330px !important; min-width: 330px !important; padding: .4rem !important; max-height: 85vh !important; }
[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] { gap: .1rem !important; }
[data-testid="stPopoverBody"] hr { margin: .3rem .5rem !important; border-color: #3d3d3d !important; }
[data-testid="stPopoverBody"] [data-testid="stElementContainer"] { margin: 0 !important; }
[class*="st-key-menu_"] button, [class*="st-key-acct_"] button { display: flex !important; justify-content: flex-start !important; text-align: left !important;
    gap: .6rem; width: 100%; background: transparent !important; border: none !important; color: #fff !important;
    padding: .45rem .7rem !important; border-radius: 10px !important; font-size: 1rem !important; min-height: 0 !important; }
[class*="st-key-menu_"] button > div, [class*="st-key-menu_"] button [data-testid="stMarkdownContainer"],
[class*="st-key-acct_"] button > div, [class*="st-key-acct_"] button [data-testid="stMarkdownContainer"] {
    justify-content: flex-start !important; text-align: left !important; flex: 0 1 auto; width: auto; }
[class*="st-key-menu_"] button p, [class*="st-key-acct_"] button p { text-align: left !important; }
[class*="st-key-menu_"] button:hover, [class*="st-key-acct_"] button:hover { background: #3a3a3a !important; }
.st-key-menu_upload button::after { content: "Ctrl+U"; margin-left: auto; color: #9a9a9a; font-size: .95rem; }
.st-key-menu_project button::after, .st-key-menu_skills button::after,
.st-key-menu_connector button::after, .st-key-menu_design button::after,
.st-key-acct_learn button::after { content: "›"; margin-left: auto; color: #aaa; font-size: 1.5rem; line-height: 1; }
.st-key-acct_settings button::after { content: "Ctrl+Shift+,"; margin-left: auto; color: #9a9a9a; font-size: .95rem; }
.st-key-menu_web_on button::after { content: "✓"; margin-left: auto; color: #4a9eff; font-size: 1.3rem; }
.st-key-hidden_upload, .st-key-hidden_settings { display: none; }
.acct-email { color: #a8a8a8; font-size: .95rem; padding: .5rem .7rem .4rem; word-break: break-all; }

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
/* --sbw = sidebar width, measured live by JavaScript so the title is never hidden behind the sidebar */
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 4.5rem !important; }
.topbar { position: fixed; top: 0; left: var(--sbw, 21rem); right: 0; height: 3.5rem; display: flex; align-items: center;
    justify-content: space-between; padding: 0 1.4rem; background: #191919; border-bottom: 1px solid #262626; z-index: 99; }
.tb-title { display: flex; align-items: center; gap: .55rem; color: #f2f2f2; font-size: 1.05rem; max-width: 60%;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tb-right { display: flex; align-items: center; gap: 1.1rem; color: #e8e8e8; font-size: 1.05rem; }
.tb-right span { display: inline-flex; align-items: center; gap: .45rem; }
.tb-right svg, .tb-title svg { stroke: #e8e8e8; fill: none; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }

/* ---------- Sidebar nav like Claude ---------- */
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { display: none; }
[data-testid="stSidebar"] .stButton button { display: flex !important; align-items: center !important; gap: .8rem; width: 100%; font-size: 1.05rem !important; }
.st-key-nav_code button::after { content: "Upgrade"; margin-left: auto; color: #5aa9ff; background: #1b2430; border: 1px solid #2c3a4d;
    border-radius: 999px; padding: 1px 10px; font-size: .8rem; white-space: nowrap; flex: 0 0 auto; }
.side-head { display: flex; align-items: center; justify-content: space-between; color: #f2f2f2; font-weight: 600;
    font-size: 1rem; padding: 1.4rem .7rem .9rem; }
.side-head svg { stroke: #e8e8e8; fill: none; stroke-width: 1.8; stroke-linecap: round; }
.st-key-view_all button { color: #9a9a9a !important; }
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] { background: #3a3a39 !important; }

/* ---------- Account row pinned to the bottom of the sidebar ---------- */
[data-testid="stSidebarUserContent"] { padding-bottom: 5.5rem !important; }
.st-key-account_wrap { position: fixed !important; left: 0; bottom: 0; width: var(--sbw, 21rem); box-sizing: border-box;
    z-index: 1000; border-top: 1px solid #2a2a2a; padding: .7rem 1rem .8rem 1rem; background: #1f1f1e; }
html[data-sbcollapsed] .st-key-account_wrap { display: none !important; }
.st-key-side_account button { display: flex !important; align-items: center !important; gap: .7rem; width: 100%; font-size: 1.05rem !important; }
.st-key-side_account button::before { content: "C"; flex: 0 0 auto; width: 30px; height: 30px; border-radius: 50%;
    background: #3a3a39; color: #e8e8e8; display: inline-flex; align-items: center; justify-content: center; font-size: .85rem; }
.st-key-side_devices button { color: #e8e8e8 !important; justify-content: center !important; padding: .42rem .4rem !important; }

/* ---------- Search popup ---------- */
[data-testid="stDialog"] [role="dialog"] { background: #2f2f2f !important; border-radius: 20px !important;
    padding: 0 !important; width: 720px !important; max-width: 94vw !important; overflow: hidden; }
[data-testid="stDialog"] [role="dialog"] h2 { display: none !important; }
[data-testid="stDialog"] button[aria-label="Close"] { position: absolute !important; top: 18px !important; right: 20px !important;
    color: #f2f2f2 !important; z-index: 5; transform: scale(1.35); }
[data-testid="stDialog"] [data-testid="stVerticalBlock"] { gap: 0 !important; }

.st-key-srch_head { padding: 22px 64px 0 26px; }
.st-key-srch_head .stTextInput, .st-key-srch_head .stTextInput > div, .st-key-srch_head .stTextInput > div > div,
.st-key-srch_head [data-baseweb="input"], .st-key-srch_head [data-baseweb="base-input"] {
    background: transparent !important; border: none !important; box-shadow: none !important; }
.st-key-srch_head input { background: transparent !important; border: none !important; box-shadow: none !important;
    color: #fff !important; font-size: 1.25rem !important; padding: 6px 0 !important; }
.st-key-srch_head input::placeholder { color: #8a8a8a !important; }
.st-key-srch_head [data-testid="InputInstructions"] { display: none !important; }

.st-key-srch_tabs { padding: 10px 18px 18px 18px; border-bottom: 1px solid #3d3d3d; }
.st-key-srch_tabs [data-testid="stButtonGroup"], .st-key-srch_tabs [role="radiogroup"] {
    background: transparent !important; border: none !important; gap: 4px !important; flex-wrap: nowrap !important; padding: 0 !important; }
.st-key-srch_tabs [data-testid^="stBaseButton-segmented"], .st-key-srch_tabs [role="radiogroup"] label {
    background: transparent !important; border: none !important; outline: none !important; box-shadow: none !important;
    color: #e8e8e8 !important; border-radius: 10px !important; min-height: 2.5rem !important; padding: 0 .9rem !important; }
.st-key-srch_tabs [data-testid^="stBaseButton-segmented"] p { color: inherit !important; font-size: 1.1rem !important; }
.st-key-srch_tabs [data-testid^="stBaseButton-segmented"][data-testid$="Active"],
.st-key-srch_tabs [data-testid^="stBaseButton-segmented"][aria-pressed="true"],
.st-key-srch_tabs [data-testid^="stBaseButton-segmented"][aria-checked="true"] { background: #4a4a4a !important; color: #fff !important; }

.st-key-srch_body { padding: 22px 12px 12px 12px; }
.srch-label { color: #9a9a9a; font-size: 1rem; padding: 0 22px 10px; }
.srch-empty { text-align: center; color: #9a9a9a; font-size: 1.5rem; padding-top: 2.4rem; padding-bottom: 1.1rem; }
.st-key-srch_all { display: flex; justify-content: center; padding-bottom: 1rem; }
.st-key-srch_all button { background: #4a4a4a !important; border: none !important; color: #fff !important;
    border-radius: 10px !important; padding: .3rem 1rem !important; font-size: 1.1rem !important; min-height: 0 !important; }

[class*="st-key-srch_row_"] button, .st-key-srch_newchat button { display: flex !important; justify-content: flex-start !important;
    text-align: left !important; gap: .8rem; width: 100%; background: transparent !important; border: none !important;
    color: #fff !important; padding: .7rem 1rem !important; border-radius: 12px !important; font-size: 1.15rem !important; min-height: 0 !important; }
[class*="st-key-srch_row_"] button:hover, .st-key-srch_newchat button:hover { background: #3a3a3a !important; }

.srch-foot { display: flex; justify-content: space-between; align-items: center; padding: 14px 26px;
    border-top: 1px solid #3d3d3d; color: #a8a8a8; font-size: 1rem; }
.srch-foot .grp { display: flex; align-items: center; gap: 2rem; }
.srch-foot .it { display: inline-flex; align-items: center; gap: .55rem; }
.srch-foot kbd { border: 1px solid #5a5a5a; border-radius: 6px; padding: 0 .4rem; font-family: inherit; font-size: .9rem; color: #a8a8a8; }

/* =====================================================================
   NEW (from the video): sidebar details, pages, create-project dialog
   ===================================================================== */

/* sidebar: "New" shows its shortcut on hover, "Projects" shows a + on hover */
.st-key-nav_new button:hover::after { content: "Ctrl+Shift+O"; margin-left: auto; color: #9a9a9a; font-size: .8rem; white-space: nowrap; }
.st-key-proj_row { position: relative; }
.st-key-proj_plus { position: absolute !important; right: 6px; top: 50%; transform: translateY(-50%);
    width: auto !important; opacity: 0; z-index: 3; }
.st-key-proj_row:hover .st-key-proj_plus { opacity: 1; }
.st-key-proj_plus .stButton, .st-key-proj_plus [data-testid="stElementContainer"] { width: auto !important; }
.st-key-proj_plus button { width: auto !important; padding: .1rem .4rem !important; font-size: 1.2rem !important; }

/* home screen "Free plan · Upgrade" pill */
.st-key-plan_wrap { align-items: center; }
.st-key-plan_wrap button { background: #222 !important; border: 1px solid #2f2f2f !important; color: #a8a8a8 !important;
    border-radius: 12px !important; min-height: 0 !important; padding: .25rem .95rem !important; font-size: .9rem !important; }
.st-key-plan_wrap button:hover { background: #2a2a2a !important; }

/* page headers (Projects / Artifacts) */
.pg-title { font-family: var(--serif); font-size: 2rem; font-weight: 400; color: #f5f4ef; line-height: 1.2; }
.st-key-pj_head [data-testid="stHorizontalBlock"], .st-key-art_bar [data-testid="stHorizontalBlock"] {
    align-items: center !important; flex-wrap: nowrap !important; gap: .3rem !important; }
.st-key-pj_head [data-testid="stColumn"], .st-key-art_bar [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-pj_search_btn button, .st-key-pj_sort_btn button, [class*="st-key-ab_"] button {
    background: transparent !important; border: none !important; color: #e6e6e6 !important; box-shadow: none !important;
    min-height: 2.2rem !important; padding: 0 .45rem !important; border-radius: 8px !important; }
.st-key-pj_search_btn button:hover, .st-key-pj_sort_btn button:hover, [class*="st-key-ab_"] button:hover { background: #2a2a29 !important; }
.st-key-pj_new button, .st-key-pj_empty button { background: #f5f4ef !important; color: #191919 !important; border: none !important;
    border-radius: 8px !important; min-height: 2.1rem !important; padding: 0 .9rem !important; font-weight: 500 !important; box-shadow: none !important; }
.st-key-pj_new button p, .st-key-pj_empty button p { color: #191919 !important; }
.st-key-pj_new button:hover, .st-key-pj_empty button:hover { background: #ffffff !important; }
.st-key-pj_new { display: flex; justify-content: flex-end; }

/* empty states */
.pg-empty { display: flex; flex-direction: column; align-items: center; text-align: center; margin-top: 5rem; }
.pg-empty svg { stroke: #e8e8e8; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.pg-empty .t1 { color: #b5b5b5; font-size: .95rem; margin-top: 1rem; }
.pg-empty .t2 { color: #8a8a8a; font-size: .85rem; max-width: 320px; margin-top: .6rem; line-height: 1.5; }
.st-key-pj_empty { align-items: center; margin-top: .6rem; }
.pg-note { margin-top: 2.2rem; }
.pg-note .t1 { color: #b5b5b5; font-size: .95rem; }
.pg-note .t2 { color: #8a8a8a; font-size: .85rem; max-width: 300px; margin-top: .8rem; line-height: 1.5; }

/* project and artifact cards: HTML card with an invisible button laid over it */
[class*="st-key-pcard_"], [class*="st-key-acard_"], [class*="st-key-tile_"] { position: relative; gap: 0 !important; }
[class*="st-key-pcard_"] .stButton, [class*="st-key-acard_"] .stButton, [class*="st-key-tile_"] .stButton {
    position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; }
[class*="st-key-pcard_"] .stButton button, [class*="st-key-acard_"] .stButton button, [class*="st-key-tile_"] .stButton button {
    width: 100% !important; height: 100% !important; opacity: 0; cursor: pointer; }
.pcard { background: #222; border: 1px solid #2f2f2f; border-radius: 14px; padding: 1rem 1.1rem; min-height: 110px; }
[class*="st-key-pcard_"]:hover .pcard, [class*="st-key-acard_"]:hover .pcard { background: #2a2a29; border-color: #3a3a39; }
.pcard .pc-title { font-family: var(--serif); font-size: 1.15rem; color: #f5f4ef; margin-bottom: .35rem; }
.pcard .pc-desc { color: #a8a8a8; font-size: .9rem; line-height: 1.45; max-height: 3em; overflow: hidden; }
.pcard .pc-meta { color: #7d7d7d; font-size: .8rem; margin-top: .7rem; }
.st-key-pj_cards, .st-key-art_cards { margin-top: 1.4rem; }

/* artifacts page */
.art-label { color: #a8a8a8; font-size: .85rem; margin: 1.3rem 0 .6rem; }
.tile { width: 112px; height: 72px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
    position: relative; overflow: hidden; }
.tile svg { stroke-width: 1.8; fill: none; stroke-linecap: round; stroke-linejoin: round; position: relative; z-index: 2; }
.tile::before { content: ""; position: absolute; inset: 0; opacity: .22;
    background: repeating-linear-gradient(115deg, transparent 0 9px, rgba(255,255,255,.55) 9px 10px); }
.t-docs { background: linear-gradient(135deg, #1d429a, #162f78); } .t-docs svg { stroke: #a9c8ff; }
.t-slides { background: linear-gradient(135deg, #8f3813, #6b270c); } .t-slides svg { stroke: #ffb994; }
.t-design { background: linear-gradient(135deg, #5326b3, #3b1a89); } .t-design svg { stroke: #d6c2ff; }
.tile-label { color: #d0d0d0; font-size: .8rem; margin-top: .4rem; }
[class*="st-key-tile_"] { width: 112px; }
.st-key-art_tabs [data-testid="stButtonGroup"], .st-key-art_tabs [role="radiogroup"] {
    background: transparent !important; border: none !important; gap: 4px !important; flex-wrap: nowrap !important; padding: 0 !important; }
.st-key-art_tabs [data-testid^="stBaseButton-segmented"], .st-key-art_tabs [role="radiogroup"] label {
    background: transparent !important; border: none !important; outline: none !important; box-shadow: none !important;
    color: #e8e8e8 !important; border-radius: 8px !important; min-height: 2rem !important; padding: 0 .8rem !important; }
.st-key-art_tabs [data-testid^="stBaseButton-segmented"] p { color: inherit !important; }
.st-key-art_tabs [data-testid^="stBaseButton-segmented"][data-testid$="Active"],
.st-key-art_tabs [data-testid^="stBaseButton-segmented"][aria-pressed="true"],
.st-key-art_tabs [data-testid^="stBaseButton-segmented"][aria-checked="true"] { background: #3a3a3a !important; color: #fff !important; }

/* "Create a project" popup */
[data-testid="stDialog"] [role="dialog"]:has(.st-key-np_wrap) { width: 520px !important; padding: 22px 24px 22px 24px !important;
    background: #2b2b2b !important; border-radius: 16px !important; }
[data-testid="stDialog"] [role="dialog"]:has(.st-key-np_wrap) h2 { display: block !important; font-size: 1rem !important;
    font-weight: 600 !important; color: #fff !important; padding: 0 0 .9rem 0 !important; }
[data-testid="stDialog"] [role="dialog"]:has(.st-key-np_wrap) button[aria-label="Close"] { top: 16px !important; right: 18px !important; transform: scale(1); }
.st-key-np_wrap [data-testid="stElementContainer"] { margin-bottom: .6rem !important; }
.st-key-np_wrap label, .st-key-np_wrap label p { color: #f2f2f2 !important; font-size: .9rem !important; font-weight: 500 !important; }
.st-key-np_wrap input, .st-key-np_wrap textarea { background: #242424 !important; color: #fff !important;
    border: 1px solid #3d3d3d !important; border-radius: 8px !important; }
.st-key-np_wrap input:focus, .st-key-np_wrap textarea:focus { border-color: #4a9eff !important; }
.st-key-np_wrap [data-baseweb="input"], .st-key-np_wrap [data-baseweb="textarea"], .st-key-np_wrap [data-baseweb="base-input"] {
    background: #242424 !important; border-radius: 8px !important; }
.st-key-np_wrap [data-testid="InputInstructions"] { display: none !important; }
.st-key-np_wrap [data-testid="stHorizontalBlock"] { gap: .5rem !important; }
.st-key-np_cancel button, .st-key-np_create button { border: none !important; border-radius: 8px !important; min-height: 2.2rem !important;
    box-shadow: none !important; font-weight: 500 !important; }
.st-key-np_cancel button { background: #4a4a4a !important; color: #fff !important; }
.st-key-np_create button { background: #f5f4ef !important; color: #191919 !important; }
.st-key-np_create button p { color: #191919 !important; }

/* ---------- fixes: search popup + artifacts tabs on newer Streamlit versions ---------- */
[data-testid="stDialog"] [role="dialog"]:has(.st-key-srch_head) { background: #2f2f2f !important; border-radius: 20px !important;
    padding: 0 !important; width: 720px !important; max-width: 94vw !important; margin: 0 auto !important; overflow: hidden !important; }
[data-testid="stDialog"] [role="dialog"]:has(.st-key-srch_head) h2,
[data-testid="stDialog"] [role="dialog"]:has(.st-key-srch_head) [data-testid="stDialogTitle"] { display: none !important; }
[data-testid="stDialog"] [role="dialog"]:has(.st-key-srch_head) > div,
[data-testid="stDialog"] [role="dialog"]:has(.st-key-srch_head) [data-testid="stVerticalBlock"] { background: transparent !important; }

.st-key-srch_tabs button, .st-key-srch_tabs label, .st-key-art_tabs button, .st-key-art_tabs label {
    background: transparent !important; border: none !important; outline: none !important; box-shadow: none !important;
    color: #e8e8e8 !important; border-radius: 10px !important; min-height: 2.5rem !important; padding: 0 .9rem !important; }
.st-key-art_tabs button, .st-key-art_tabs label { min-height: 2rem !important; padding: 0 .8rem !important; border-radius: 8px !important; }
.st-key-srch_tabs button p, .st-key-srch_tabs label p, .st-key-art_tabs button p, .st-key-art_tabs label p {
    color: inherit !important; font-size: 1.1rem !important; }
.st-key-art_tabs button p, .st-key-art_tabs label p { font-size: 1rem !important; }
.st-key-srch_tabs button:hover, .st-key-art_tabs button:hover { background: #3a3a3a !important; }
.st-key-srch_tabs button[aria-checked="true"], .st-key-srch_tabs button[aria-pressed="true"],
.st-key-srch_tabs button[kind$="Active"], .st-key-srch_tabs button[data-testid$="Active"],
.st-key-art_tabs button[aria-checked="true"], .st-key-art_tabs button[aria-pressed="true"],
.st-key-art_tabs button[kind$="Active"], .st-key-art_tabs button[data-testid$="Active"] {
    background: #4a4a4a !important; color: #ffffff !important; }
.st-key-art_tabs button[aria-checked="true"], .st-key-art_tabs button[aria-pressed="true"],
.st-key-art_tabs button[kind$="Active"], .st-key-art_tabs button[data-testid$="Active"] { background: #3a3a3a !important; }

/* search rows: icon + text on the left, like the + menu */
[class*="st-key-srch_row_"] button > div, [class*="st-key-srch_row_"] button [data-testid="stMarkdownContainer"],
.st-key-srch_newchat button > div, .st-key-srch_newchat button [data-testid="stMarkdownContainer"] {
    justify-content: flex-start !important; text-align: left !important; flex: 0 1 auto; width: auto; }
[class*="st-key-srch_row_"] button p, .st-key-srch_newchat button p { text-align: left !important; }
[class*="st-key-srch_row_"] button, .st-key-srch_newchat button { display: flex !important; justify-content: flex-start !important;
    align-items: center !important; width: 100% !important; }
[class*="st-key-srch_row_"] button::after, .st-key-srch_newchat button::after { white-space: nowrap; flex: 0 0 auto; }
[data-testid="stDialog"] .srch-label { padding-left: 22px; }

/* ---------- fix: remove the dark outer frame around the search popup + footer spacing ---------- */
[data-testid="stDialog"] div:has(.st-key-srch_head) { background: transparent !important; box-shadow: none !important;
    border: none !important; outline: none !important; }
[data-testid="stDialog"] [role="dialog"]:has(.st-key-srch_head) { background: #2f2f2f !important; }
[data-testid="stDialog"] div:has(.st-key-np_wrap):not([role="dialog"]) { background: transparent !important; box-shadow: none !important; border: none !important; }
[data-testid="stDialog"] [role="dialog"]:has(.st-key-np_wrap) { background: #2b2b2b !important; }
.srch-foot { gap: .8rem; flex-wrap: nowrap; font-size: .9rem; padding: 14px 20px; }
.srch-foot .grp { gap: 1.1rem; flex-wrap: nowrap; }
.srch-foot .it { gap: .4rem; white-space: nowrap; }
.srch-foot kbd { font-size: .8rem; }
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
    "chat_titles": {},            # short generated titles, keyed by chat name
    "current_chat": "New Chat",
    "show_workspace": False,
    "workspace_content": "# Workspace\n\nGenerated artifacts will appear here.",
    "stored_groq_key": "",
    "projects": {},
    "chat_project": {},
    "attachments": [],
    "panel": None,
    "menu_view": "main",
    "acct_view": "main",
    "open_settings": False,
    "settings_open": False,
    "auto_settings_done": False,
    "settings_section": "Account",
    "settings_search": "",
    "custom_instructions": "",
    "notifications_enabled": True,
    "reduce_motion": False,
    "response_style": "Balanced",
    "profile_full_name": "Chandlio User",
    "profile_call_name": "Chandlio User",
    "profile_work": "Other",
    "web_search": True,
    "shot_trigger": 0,
    "last_shot_id": None,
    "pending_prompt": None,
    "msg_box": "",
    "upload_nonce": 0,
    "show_projects": False,
    "show_search": False,
    "show_all_chats": False,
    "scroll_bottom": False,       # when True, the page scrolls to the newest message
    # ---- pages shown in the video ----
    "page": "chat",               # "chat" | "projects" | "artifacts"
    "open_newproj": False,        # opens the "Create a project" popup
    "proj_search_on": False,
    "proj_sort": "recent",        # "recent" | "name"
    "artifact_items": [],         # every code answer, listed on the Artifacts page
    "art_search_on": False,
    "art_newest_first": True,
    "art_list_view": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

_page = st.session_state["page"]

# Centered Claude-width column (wider only when the artifact workspace is open, or on the Projects / Artifacts pages)
if _page != "chat":
    _col_width = "1100px"
else:
    _col_width = "1200px" if st.session_state["show_workspace"] else "760px"
st.markdown(
    f"<style>.block-container {{ max-width: {_col_width} !important; margin: 0 auto !important; "
    f"padding-left: 1.2rem !important; padding-right: 1.2rem !important; }}</style>",
    unsafe_allow_html=True,
)
if _page != "chat":
    st.markdown("<style>.block-container, [data-testid=\"stMainBlockContainer\"] { padding-top: 2.6rem !important; }</style>",
                unsafe_allow_html=True)

# Once a chat has messages, dock the input bar at the very bottom of the screen (like Claude)
_has_msgs = _page == "chat" and (bool(st.session_state["chat_sessions"][st.session_state["current_chat"]])
                                 or st.session_state["pending_prompt"] is not None)
if _has_msgs:
    st.markdown("""
<style>
[data-testid="stMainBlockContainer"] { padding-bottom: .4rem !important; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { min-height: calc(100vh - 5rem); }
.st-key-inputbar { margin: auto auto 0 auto !important; }
</style>""", unsafe_allow_html=True)

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
    """Short generated title if we have one, otherwise a trimmed first message."""
    titles = st.session_state.get("chat_titles", {})
    if titles.get(name):
        return titles[name]
    for m in st.session_state["chat_sessions"].get(name, []):
        if m["role"] == "user":
            t = m["content"].strip().replace("\n", " ")
            return (t[:34] + "…") if len(t) > 34 else t
    if name == next(iter(st.session_state["chat_sessions"]), None):
        return f"Your first chat with {AI_NAME}"
    return "New chat"

def listed_chats():
    """Chats shown in the sidebar and in Search > Recents (newest first).
    When nothing has been said yet, the very first chat is listed, like in the video."""
    s = st.session_state
    names = [n for n, msgs in s["chat_sessions"].items()
             if msgs or (n == s["current_chat"] and s["pending_prompt"] is not None)][::-1]
    if not names:
        names = [next(iter(s["chat_sessions"]))]
    return names

def make_title(user_text, answer):
    """Ask a small model for a 2-5 word title (like Claude does). Returns None on failure."""
    from langchain_groq import ChatGroq
    system = ("Write a very short title (2 to 5 words) that summarises this conversation. "
              "Reply with ONLY the title: no quotes, no full stop, no emojis.")
    convo = f"User: {user_text[:500]}\n\nAssistant: {answer[:500]}"
    for model, tokens in (("llama-3.1-8b-instant", 24), ("openai/gpt-oss-120b", 400)):
        try:
            r = ChatGroq(model=model, temperature=0.2, max_tokens=tokens,
                         api_key=st.session_state["stored_groq_key"]).invoke(
                [("system", system), ("user", convo)])
            title = (r.content or "").strip().splitlines()[0].strip().strip("\"'“”‘’*#").rstrip(".").strip()
            if title:
                return title[:40]
        except Exception:
            continue
    return None

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
    style = st.session_state.get("response_style", "Balanced")
    style_guidance = {
        "Concise": "Keep responses concise and focused.",
        "Detailed": "Provide thorough explanations with useful context.",
        "Step by step": "Explain processes in clear, ordered steps.",
        "Balanced": "Use a balanced level of detail.",
    }.get(style, "")
    if style_guidance:
        base += "\n\nResponse style: " + style_guidance
    custom = st.session_state.get("custom_instructions", "").strip()
    if custom:
        base += "\n\nAdditional user instructions: " + custom
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

def set_acct_view(view):
    st.session_state["acct_view"] = view

def open_settings():
    st.session_state["open_settings"] = True
    st.session_state["settings_open"] = True
    st.session_state["settings_section"] = "Account"
    st.session_state["acct_view"] = "main"

def logout():
    st.session_state["stored_groq_key"] = ""
    st.session_state["acct_view"] = "main"
    st.session_state["toast"] = "Logged out."

def on_mode_change():
    val = st.session_state.get("mode_sel")
    if val != "Chat":
        if val == "Cowork":
            st.session_state["toast"] = "Cowork is not available yet."
        st.session_state["mode_sel"] = "Chat"

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

# ---- callbacks for the pages from the video ----
def go_page(name):
    st.session_state["page"] = name

def go_chat(prefill=None):
    """Open the chat screen (re-using the current chat if it is still empty)."""
    s = st.session_state
    if s["chat_sessions"][s["current_chat"]]:
        new_title = f"Chat {len(s['chat_sessions']) + 1}"
        s["chat_sessions"][new_title] = []
        s["current_chat"] = new_title
    s["page"] = "chat"
    s["show_workspace"] = False
    if prefill:
        s["msg_box"] = prefill

def open_newproject():
    st.session_state["open_newproj"] = True

def go_projects_and_new():
    st.session_state["page"] = "projects"
    st.session_state["open_newproj"] = True

def toggle_proj_sort():
    st.session_state["proj_sort"] = "name" if st.session_state["proj_sort"] == "recent" else "recent"

def open_project(name):
    link_chat_to_project(name)
    st.session_state["page"] = "chat"
    st.session_state["toast"] = f"This chat is now linked to project '{name}'."

def open_artifact(idx):
    items = st.session_state["artifact_items"]
    if 0 <= idx < len(items):
        st.session_state["workspace_content"] = items[idx]["content"]
        st.session_state["show_workspace"] = True
        st.session_state["page"] = "chat"

# ---------------- SETTINGS DIALOG (account menu entry; full Claude-style layout) ----------------
@st.dialog("Settings", width="large")
def settings_dialog():
    sections = ["Account", "Billing", "Appearance", "Your Chandlio", "Capabilities",
                "Notifications", "Privacy", "Wellbeing", "Customize", "Code"]
    st.markdown("""
    <style>
    /* Large, centered settings surface matching the supplied reference */
    [data-testid="stDialog"] { align-items:center !important; justify-content:center !important; }
    [data-testid="stDialog"] [role="dialog"] {
        width:94vw !important; max-width:94vw !important; min-width: min(94vw, 1100px) !important;
        height:92vh !important; max-height:92vh !important; margin:auto !important;
        padding:0 !important; overflow:hidden !important; background:#202020 !important;
        border:1px solid #383838 !important; border-radius:16px !important;
        box-shadow:0 18px 60px rgba(0,0,0,.55) !important;
    }
    [data-testid="stDialog"] [data-testid="stDialogHeader"] {display:none !important;}
    [data-testid="stDialog"] [data-testid="stDialogContent"] {
        padding:0 !important; height:100% !important; max-height:92vh !important; overflow:hidden !important;
    }
    [data-testid="stDialog"] [data-testid="stVerticalBlock"] {gap:.35rem !important;}
    .st-key-settings_shell {height:100%; padding:0 !important; gap:0 !important;}
    .st-key-settings_top {padding:12px 22px 10px !important; border-bottom:1px solid #343434 !important;}
    .st-key-settings_top [data-testid="stHorizontalBlock"] {align-items:center !important;}
    .st-key-settings_heading {font-size:1.35rem;font-weight:650;color:#f1f1f1;padding:2px 0;}
    .st-key-settings_close button {background:transparent !important;border:0 !important;color:#eee !important;
        font-size:1.7rem !important;min-height:2rem !important;padding:0 .4rem !important;}
    .st-key-settings_body {height:calc(92vh - 58px); padding:0 !important; gap:0 !important;}
    .st-key-settings_nav {height:calc(92vh - 58px); overflow-y:auto !important; padding:20px 18px 24px 22px !important;
        border-right:1px solid #343434 !important;}
    .st-key-settings_nav [data-testid="stTextInput"] {margin-bottom:12px !important;}
    .st-key-settings_nav input {background:#292929 !important;border:1px solid #414141 !important;border-radius:11px !important;
        min-height:2.55rem !important;color:#eee !important;}
    .st-key-settings_nav button {width:100% !important;display:flex !important;justify-content:flex-start !important;
        text-align:left !important;background:transparent !important;border:0 !important;color:#e1e1e1 !important;
        border-radius:10px !important;min-height:2.65rem !important;padding:.45rem .8rem !important;font-size:1rem !important;}
    .st-key-settings_nav button p {text-align:left !important;}
    .st-key-settings_nav button:hover {background:#303030 !important;}
    .st-key-settings_nav [data-testid="stBaseButton-primary"] {background:#3b3b3b !important;color:#fff !important;}
    .st-key-settings_content {height:calc(92vh - 58px); overflow-y:auto !important; padding:24px 30px 38px 24px !important;}
    .st-key-settings_content h3 {font-size:1.35rem !important;font-weight:650 !important;margin:0 0 22px !important;color:#f2f2f2 !important;}
    .st-key-settings_content h4 {font-size:1.05rem !important;margin:20px 0 12px !important;}
    .st-key-settings_content [data-testid="stTextInput"], .st-key-settings_content [data-testid="stSelectbox"],
    .st-key-settings_content [data-testid="stTextArea"] {margin:0 !important;}
    .st-key-settings_content input, .st-key-settings_content textarea,
    .st-key-settings_content [data-baseweb="select"] > div {background:#292929 !important;border:1px solid #414141 !important;
        color:#f2f2f2 !important;border-radius:10px !important;}
    .st-key-settings_content label, .st-key-settings_content p {color:#dedede;}
    .st-key-settings_content [data-testid="stCaptionContainer"] p {color:#999 !important;}
    .settings-row {display:grid;grid-template-columns:minmax(230px, 1fr) minmax(240px, 1.2fr);gap:28px;
        align-items:center;padding:15px 0;border-bottom:1px solid #343434;}
    .settings-row-title {font-size:1rem;color:#e6e6e6;font-weight:500;}
    .settings-row-note {font-size:.88rem;color:#999;margin-top:4px;}
    .settings-section-note {color:#999;font-size:.9rem;margin:-12px 0 18px;}
    .settings-profile {display:flex;align-items:center;gap:18px;padding:12px 0 20px;border-bottom:1px solid #343434;margin-bottom:4px;}
    .settings-avatar {width:58px;height:58px;border-radius:50%;background:#383838;display:flex;align-items:center;justify-content:center;
        font-size:23px;color:#eee;flex-shrink:0;}
    @media(max-width:900px){
      [data-testid="stDialog"] [role="dialog"]{width:96vw !important;max-width:96vw !important;min-width:96vw !important;height:94vh !important;max-height:94vh !important;}
      .st-key-settings_nav{padding:14px 10px !important;}
      .st-key-settings_content{padding:18px 14px !important;}
      .settings-row{grid-template-columns:1fr;gap:8px;}
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="settings_shell"):
        with st.container(key="settings_top"):
            head, close = st.columns([12, 1], vertical_alignment="center")
            with head:
                st.markdown("<div class='st-key-settings_heading'>Settings</div>", unsafe_allow_html=True)
            with close:
                with st.container(key="settings_close"):
                    if st.button("×", key="settings_close_button", help="Close settings"):
                        st.session_state["settings_open"] = False
                        st.rerun()
        with st.container(key="settings_body"):
            nav_col, content_col = st.columns([0.92, 3.08], gap="small")
            with nav_col:
                with st.container(key="settings_nav"):
                    st.text_input("Search", key="settings_search", placeholder="Search", label_visibility="collapsed")
                    q = st.session_state.get("settings_search", "").strip().lower()
                    shown = [x for x in sections if not q or q in x.lower()]
                    for section in shown:
                        icons = {"Account":":material/person_outline:","Billing":":material/credit_card:","Appearance":":material/palette:",
                                 "Your Chandlio":":material/psychology:","Capabilities":":material/work:","Notifications":":material/notifications:",
                                 "Privacy":":material/shield:","Wellbeing":":material/favorite_border:","Customize":":material/tune:","Code":":material/code:"}
                        if section in ("Appearance", "Customize", "Code"):
                            st.divider()
                        if st.button(section, key="settings_section_" + section,
                                     icon=icons[section],
                                     type="primary" if st.session_state.get("settings_section") == section else "secondary",
                                     use_container_width=True):
                            st.session_state["settings_section"] = section
                            st.rerun()
            with content_col:
                with st.container(key="settings_content"):
                    section = st.session_state.get("settings_section", "Account")
                    st.subheader("Profile" if section == "Account" else section)
                    if section == "Account":
                        st.markdown("<div class='settings-profile'><div class='settings-avatar'>C</div><div><div class='settings-row-title'>Profile photo</div><div class='settings-row-note'>PNG, JPEG, or WebP up to 10MB.</div></div></div>", unsafe_allow_html=True)
                        for label, key, default in [("Full name", "profile_full_name", "Chandlio User"), ("What should Chandlio call you?", "profile_call_name", "Chandlio User")]:
                            left, right = st.columns([1.35, 1.65], vertical_alignment="center")
                            with left: st.markdown(f"<div class='settings-row-title'>{label}</div>", unsafe_allow_html=True)
                            with right: st.text_input(label, key=key, placeholder=default, label_visibility="collapsed")
                            st.divider()
                        left, right = st.columns([1.35, 1.65], vertical_alignment="center")
                        with left: st.markdown("<div class='settings-row-title'>What best describes your work?</div>", unsafe_allow_html=True)
                        with right: st.selectbox("Work", ["Other", "Student", "Developer", "Researcher", "Business owner", "Designer"], key="profile_work", label_visibility="collapsed")
                        st.divider()
                        left, right = st.columns([1.35, 1.65], vertical_alignment="center")
                        with left: st.markdown("<div class='settings-row-title'>Email</div>", unsafe_allow_html=True)
                        with right: st.text_input("Email", value=ACCOUNT_EMAIL, disabled=True, label_visibility="collapsed")
                        st.divider()
                        st.markdown("**Where you’re logged in**")
                        st.caption("This browser session · Current device")
                        st.markdown("<div class='settings-row-note'>Device　　　　　　　　　　　 Location　　　　　　　　　 Signed in　　　　　　　　 Last active<br>Chrome (current)　　　　　　 Current device　　　　 This session　　　　　　 Active now</div>", unsafe_allow_html=True)
                        st.markdown("**Trusted devices**")
                        st.caption("Device management will be available when Chandlio account sign-in is connected.")
                    elif section == "Billing":
                        st.markdown("**Chandlio · Free**")
                        st.caption("Your current workspace plan")
                        st.divider()
                        st.info("Billing, subscriptions and payment management are not connected in this version.")
                    elif section == "Appearance":
                        st.caption("Choose how Chandlio looks. Your workspace layout and chat structure stay the same.")
                        st.markdown("**Colour theme**")
                        st.selectbox("Colour theme", list(CHANDLIO_THEMES.keys()), key="theme_choice", label_visibility="collapsed")
                        st.caption("Midnight Ember is the default theme. Changing the theme changes colours only.")
                        st.markdown("**Preview**")
                        st.markdown("<div style='display:flex;gap:10px;flex-wrap:wrap;padding:16px;background:#191919;border:1px solid #3d3d3d;border-radius:12px'><span style='background:#1f1f1e;padding:16px 24px;border-radius:8px'>Navigation</span><span style='background:#262626;padding:16px 24px;border-radius:8px'>Workspace</span><span style='background:#d97757;color:#fff;padding:16px 24px;border-radius:8px'>Accent</span></div>", unsafe_allow_html=True)
                    elif section == "Your Chandlio":
                        st.caption("Set instructions that guide Chandlio's responses.")
                        st.text_area("Custom instructions", key="custom_instructions", height=180, placeholder="For example: explain things step by step and keep answers concise.")
                        st.caption("These instructions are applied to new responses in this session.")
                    elif section == "Capabilities":
                        st.toggle("Web search", key="web_search", help="Use the existing web-search setting in this app.")
                        st.caption("Other connected apps and integrations are not configured yet.")
                    elif section == "Notifications":
                        st.toggle("In-app notifications", key="notifications_enabled")
                        st.caption("Browser push notifications are not configured in this version.")
                    elif section == "Privacy":
                        st.markdown("**Your data**")
                        st.write("Chats and preferences are held in the current Streamlit session. Persistent account storage, export and deletion workflows are not connected yet.")
                    elif section == "Wellbeing":
                        st.toggle("Reduce interface motion", key="reduce_motion")
                        st.caption("The current interface uses minimal animation.")
                    elif section == "Customize":
                        st.caption("Choose how Chandlio responds.")
                        st.selectbox("Response style", ["Balanced", "Concise", "Detailed", "Step by step"], key="response_style")
                        st.caption("This preference is applied to new responses.")
                    elif section == "Code":
                        st.markdown("**Model connection**")
                        st.caption("Provider: Groq · Model: openai/gpt-oss-120b")
                        new_key = st.text_input("Groq API Key", value=st.session_state["stored_groq_key"], type="password", placeholder="gsk_...")
                        st.caption("Your key is kept only for this Streamlit session.")
                        if st.button("Save API key", key="save_settings", type="primary"):
                            if new_key.strip():
                                st.session_state["stored_groq_key"] = new_key.strip()
                                st.session_state["toast"] = "Settings saved."
                                st.rerun()
                            else:
                                st.error("Please paste your Groq API key.")

# ---------------- CREATE A PROJECT DIALOG (from the video) ----------------
@st.dialog("Create a project")
def newproject_dialog():
    with st.container(key="np_wrap"):
        name = st.text_input("What are you working on?", key="np_name", placeholder="Name your project")
        desc = st.text_area("What are you trying to achieve?", key="np_desc", height=90,
                            placeholder="Describe your project, goals, subject, etc...")
        _gap, b1, b2 = st.columns([5, 1.4, 2.2])
        with b1:
            with st.container(key="np_cancel"):
                cancel = st.button("Cancel", key="np_cancel_btn", use_container_width=True)
        with b2:
            with st.container(key="np_create"):
                create = st.button("Create project", key="np_create_btn", use_container_width=True)
        if cancel:
            st.rerun()
        if create:
            nm = (name or "").strip()
            if not nm:
                st.error("Please enter a project name.")
            elif nm in st.session_state["projects"]:
                st.error("A project with that name already exists.")
            else:
                st.session_state["projects"][nm] = {"description": (desc or "").strip(), "files": []}
                st.session_state["toast"] = f"Project '{nm}' created."
                st.rerun()

# ---------------- SEARCH POPUP ----------------
SEARCH_TABS = ["All", "Artifacts", "Chats", "Projects", "Sessions", "Tasks", "Scheduled"]

def _search_all():
    st.session_state["search_tab"] = "All"

def _search_row(label, icon, key):
    return st.button(label, icon=icon, key=key, use_container_width=True)

@st.dialog("Search", width="large")
def search_dialog():
    with st.container(key="srch_head"):
        q = st.text_input("Search", key="search_q", placeholder="Search", label_visibility="collapsed")
    with st.container(key="srch_tabs"):
        if hasattr(st, "segmented_control"):
            st.segmented_control("Type", SEARCH_TABS, key="search_tab", label_visibility="collapsed")
        else:
            st.radio("Type", SEARCH_TABS, key="search_tab", horizontal=True, label_visibility="collapsed")
    tab = st.session_state.get("search_tab") or "All"
    ql = (q or "").strip().lower()

    sessions = st.session_state["chat_sessions"]
    chat_hits = [n for n in listed_chats() if
                 (not ql or ql in chat_title(n).lower() or any(ql in m["content"].lower() for m in sessions[n]))]
    proj_hits = [p for p in st.session_state["projects"] if not ql or ql in p.lower()]
    art_hits = [(i, a) for i, a in enumerate(st.session_state["artifact_items"])
                if not ql or ql in a["title"].lower() or ql in a["content"].lower()][::-1]

    chat_rows = tab in ("All", "Chats") and bool(chat_hits)
    # first row is highlighted (that is what Enter opens); when there are no chats, "New chat" is highlighted
    hl_css = ("<style>.st-key-srch_first button { background: #4a4a4a !important; }"
              ".st-key-srch_first button::after { content: \"\\22EF   \\21B5\"; margin-left: auto; color: #cfcfcf; letter-spacing: .08em; white-space: nowrap; }</style>"
              if chat_rows else
              "<style>.st-key-srch_newchat button { background: #4a4a4a !important; }"
              ".st-key-srch_newchat button::after { content: \"\\21B5\"; margin-left: auto; color: #cfcfcf; font-size: 1.4rem; line-height: 1; }</style>")
    body_css = "<style>.st-key-srch_body { min-height: 420px; }</style>" if tab == "All" else ""
    st.markdown(hl_css + body_css, unsafe_allow_html=True)

    with st.container(key="srch_body"):
        shown = False

        if tab in ("All", "Chats") and chat_hits:
            if tab == "All":
                st.markdown(f"<div class='srch-label'>{'Recents' if not ql else 'Chats'}</div>", unsafe_allow_html=True)
            for idx, n in enumerate(chat_hits[:20]):
                if idx == 0:
                    with st.container(key="srch_first"):
                        clicked = _search_row(chat_title(n), ":material/chat_bubble_outline:", f"srch_row_chat_{n}")
                else:
                    clicked = _search_row(chat_title(n), ":material/chat_bubble_outline:", f"srch_row_chat_{n}")
                if clicked:
                    st.session_state["current_chat"] = n
                    st.session_state["page"] = "chat"
                    st.session_state["scroll_bottom"] = True
                    st.rerun()
            shown = True

        if tab in ("All", "Projects") and proj_hits:
            if tab == "All":
                st.markdown("<div class='srch-label' style='padding-top:14px'>Projects</div>", unsafe_allow_html=True)
            for p in proj_hits:
                if _search_row(p, ":material/folder:", f"srch_row_proj_{p}"):
                    link_chat_to_project(p)
                    st.session_state["page"] = "projects"
                    st.rerun()
            shown = True

        if tab in ("All", "Artifacts") and art_hits:
            if tab == "All":
                st.markdown("<div class='srch-label' style='padding-top:14px'>Artifacts</div>", unsafe_allow_html=True)
            for i, a in art_hits[:10]:
                if _search_row(a["title"], ":material/filter_none:", f"srch_row_artifact_{i}"):
                    open_artifact(i)
                    st.rerun()
            shown = True

        if tab == "All" and not ql:
            st.markdown("<div class='srch-label' style='padding-top:14px'>Actions</div>", unsafe_allow_html=True)
            if st.button("New chat", icon=":material/add_comment:", key="srch_newchat", use_container_width=True):
                new_title = f"Chat {len(sessions) + 1}"
                sessions[new_title] = []
                st.session_state["current_chat"] = new_title
                st.session_state["page"] = "chat"
                st.session_state["show_workspace"] = False
                st.rerun()
            shown = True

        if not shown:
            st.markdown(f"<div class='srch-empty'>No results in {_html.escape(tab)}</div>", unsafe_allow_html=True)
            if tab != "All":
                with st.container(key="srch_all"):
                    st.button("Search all", key="srch_all_btn", on_click=_search_all)

    actions_item = "<span class='it'>Actions <kbd>Alt</kbd><kbd>↵</kbd></span>" if chat_rows else ""
    st.markdown(
        "<div class='srch-foot'><div class='grp'>"
        "<span class='it'>Close <kbd>Esc</kbd></span>"
        "<span class='it'>Change type <kbd>←</kbd><kbd>→</kbd></span>"
        "<span class='it'>Filters <kbd>/</kbd></span>" + actions_item + "</div>"
        "<span class='it'>Compose <kbd>Tab</kbd></span></div>",
        unsafe_allow_html=True)

# ---------------- CLAUDE-STYLE SIDEBAR ----------------
FILTER_SVG = ('<svg width="18" height="18" viewBox="0 0 24 24"><line x1="4" y1="7" x2="20" y2="7"/>'
              '<line x1="7" y1="12" x2="17" y2="12"/><line x1="10" y1="17" x2="14" y2="17"/></svg>')

with st.sidebar:
    st.markdown("<div class='brand'>Chandlio</div>", unsafe_allow_html=True)

    _cur_empty = not st.session_state["chat_sessions"][st.session_state["current_chat"]] \
        and st.session_state["pending_prompt"] is None
    if st.button("New", icon=":material/add:", use_container_width=True, key="nav_new",
                 type="primary" if (_page == "chat" and _cur_empty) else "secondary"):
        new_title = f"Chat {len(st.session_state['chat_sessions']) + 1}"
        st.session_state["chat_sessions"][new_title] = []
        st.session_state["current_chat"] = new_title
        st.session_state["page"] = "chat"
        st.session_state["show_workspace"] = False
        st.rerun()

    if st.button("Search", icon=":material/search:", use_container_width=True, key="nav_search"):
        st.session_state["search_q"] = ""
        st.session_state["search_tab"] = "All"
        search_dialog()
    search_q = ""

    # Projects row: opens the Projects page; a + shows on hover (always while on that page) to create a project
    if _page == "projects":
        st.markdown("<style>.st-key-proj_plus { opacity: 1 !important; }</style>", unsafe_allow_html=True)
    with st.container(key="proj_row"):
        st.button("Projects", icon=":material/inventory_2:", use_container_width=True, key="nav_projects",
                  on_click=go_page, args=("projects",), type="primary" if _page == "projects" else "secondary")
        with st.container(key="proj_plus"):
            st.button(" ", icon=":material/add:", key="nav_projects_plus", on_click=go_projects_and_new)

    st.button("Artifacts", icon=":material/filter_none:", use_container_width=True, key="nav_artifacts",
              on_click=go_page, args=("artifacts",), type="primary" if _page == "artifacts" else "secondary")

    st.button("Code", icon=":material/code:", use_container_width=True, key="nav_code",
              on_click=soon, args=("Code is not available yet.",))
    st.button("Customize", icon=":material/work:", use_container_width=True, key="nav_customize",
              on_click=soon, args=("Customize is not available yet.",))

    st.markdown(f"<div class='side-head'><span>Chats and tasks &#9662;</span>{FILTER_SVG}</div>",
                unsafe_allow_html=True)

    names = listed_chats()
    if search_q:
        names = [n for n in names if search_q in chat_title(n).lower()]
    limit = len(names) if (st.session_state["show_all_chats"] or search_q) else 8
    for chat_name in names[:limit]:
        _has_content = bool(st.session_state["chat_sessions"][chat_name]) or \
            (chat_name == st.session_state["current_chat"] and st.session_state["pending_prompt"] is not None)
        is_active = chat_name == st.session_state["current_chat"] and _page == "chat" and _has_content
        if st.button(chat_title(chat_name), use_container_width=True, key=f"btn_{chat_name}",
                     type="primary" if is_active else "secondary"):
            st.session_state["current_chat"] = chat_name
            st.session_state["page"] = "chat"
            st.session_state["scroll_bottom"] = True
            st.rerun()
    if not search_q:
        st.button("Show less" if st.session_state["show_all_chats"] else "View all", key="view_all",
                  use_container_width=True, on_click=toggle_state, args=("show_all_chats",))

    # ---- account row, pinned to the bottom (avatar + name + plan, opens the account menu) ----
    with st.container(key="account_wrap"):
        a1, a2 = st.columns([6, 1], vertical_alignment="center")
        with a1:
            with st.container(key="side_account"):
                with st.popover("Chandlio · :gray[Free]", use_container_width=True):
                    if st.session_state["acct_view"] == "main":
                        st.markdown(f"<div class='acct-email'>{_html.escape(ACCOUNT_EMAIL)}</div>",
                                    unsafe_allow_html=True)
                        st.button("Settings", icon=":material/settings:", key="acct_settings",
                                  use_container_width=True, on_click=open_settings)
                        st.button("Language", icon=":material/language:", key="acct_language",
                                  use_container_width=True, on_click=soon,
                                  args=("Language: only English is available for now.",))
                        st.button("Get help", icon=":material/help:", key="acct_help",
                                  use_container_width=True, on_click=soon,
                                  args=("Help is not available yet.",))
                        st.divider()
                        st.button("Upgrade plan", icon=":material/arrow_circle_up:", key="acct_upgrade",
                                  use_container_width=True, on_click=soon,
                                  args=("Upgrade is not available yet.",))
                        st.button("Get apps and extensions", icon=":material/devices:", key="acct_apps",
                                  use_container_width=True, on_click=soon,
                                  args=("Apps and extensions are not available yet.",))
                        st.button("Learn more", icon=":material/info:", key="acct_learn",
                                  use_container_width=True, on_click=set_acct_view, args=("learn",))
                        st.divider()
                        st.button("Log out", icon=":material/logout:", key="acct_logout",
                                  use_container_width=True, on_click=logout)
                    else:
                        st.button("Back", icon=":material/arrow_back:", key="acct_back",
                                  use_container_width=True, on_click=set_acct_view, args=("main",))
                        st.caption("Chandlio is a personal project built with Streamlit and Groq.")
        with a2:
            st.button(" ", icon=":material/devices:", key="side_devices", use_container_width=True,
                      on_click=soon, args=("Apps and extensions are not available yet.",))

    # open the Settings dialog (from the menu, Ctrl+Shift+, or automatically when no key is set yet)
    _want_settings = st.session_state.pop("open_settings", False)
    _want_newproj = st.session_state.pop("open_newproj", False)
    if _want_settings:
        st.session_state["settings_open"] = True
    if not st.session_state["stored_groq_key"] and not st.session_state["auto_settings_done"]:
        st.session_state["auto_settings_done"] = True
        st.session_state["settings_open"] = True
    if st.session_state.get("settings_open"):
        settings_dialog()
    elif _want_newproj:
        newproject_dialog()

# ---------------- JAVASCRIPT (shortcuts, top-bar offset, auto-grow, auto-scroll) ----------------
KEYS_AND_SCROLL_JS = """
(function () {
  var P = window.parent, doc = P.document;

  /* ---- Search popup helpers ---- */
  function srchHead() { return doc.querySelector('[data-testid="stDialog"] .st-key-srch_head'); }
  function srchInput() { var h = srchHead(); return h ? h.querySelector('input') : null; }
  function srchTab(dir) {
    var dlg = doc.querySelector('[data-testid="stDialog"]');
    if (!dlg) return;
    var btns = Array.prototype.slice.call(dlg.querySelectorAll('.st-key-srch_tabs button'));
    if (!btns.length) return;
    var cur = 0;
    btns.forEach(function (b, i) {
      var tid = b.getAttribute('data-testid') || '';
      if (b.getAttribute('aria-pressed') === 'true' || b.getAttribute('aria-checked') === 'true' || /Active$/.test(tid)) { cur = i; }
    });
    var n = Math.max(0, Math.min(btns.length - 1, cur + dir));
    if (n !== cur) { btns[n].click(); }
    P.setTimeout(function () { var i = srchInput(); if (i) i.focus(); }, 400);
  }

  /* Enter = send, Shift+Enter = new line, Ctrl+U = upload, Ctrl+Shift+, = settings, Ctrl+Shift+O = new chat,
     and inside the search popup: arrows = change type, / = focus search, Tab = compose, Enter = open the highlighted row */
  if (P.__chandlioKeys) { doc.removeEventListener("keydown", P.__chandlioKeys, true); }
  P.__chandlioKeys = function (e) {
    var t = e.target;

    if (srchHead()) {
      var inp = srchInput();
      var inInput = (t === inp);
      if (e.key === "ArrowLeft" && (!inInput || (inp.selectionStart === 0 && inp.selectionEnd === 0))) {
        e.preventDefault(); e.stopPropagation(); srchTab(-1); return;
      }
      if (e.key === "ArrowRight" && (!inInput || (inp.selectionStart === inp.value.length && inp.selectionEnd === inp.value.length))) {
        e.preventDefault(); e.stopPropagation(); srchTab(1); return;
      }
      if (e.key === "/" && (!inInput || !inp.value)) {
        e.preventDefault(); e.stopPropagation(); if (inp) inp.focus(); return;
      }
      if (e.key === "Tab" && !e.shiftKey) {
        e.preventDefault(); e.stopPropagation();
        var x = doc.querySelector('[data-testid="stDialog"] button[aria-label="Close"]');
        if (x) x.click();
        P.setTimeout(function () {
          var ta = doc.querySelector(".st-key-inputbar textarea");
          if (ta) ta.focus();
        }, 400);
        return;
      }
      if (e.key === "Enter" && inInput && !inp.value.trim()) {
        var nb = doc.querySelector(".st-key-srch_first button") || doc.querySelector(".st-key-srch_newchat button");
        if (nb) { e.preventDefault(); e.stopPropagation(); nb.click(); return; }
      }
    }

    if (e.key === "Enter" && !e.shiftKey && !e.isComposing && t && t.tagName === "TEXTAREA"
        && t.closest(".st-key-inputbar")) {
      e.preventDefault(); e.stopPropagation();
      t.blur();
      setTimeout(function () {
        var b = doc.querySelector(".st-key-send_btn button");
        if (b) b.click();
      }, 150);
    }
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === "u" || e.key === "U")) {
      e.preventDefault();
      var h = doc.querySelector(".st-key-hidden_upload button");
      if (h) h.click();
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "," || e.key === "<")) {
      e.preventDefault();
      var s = doc.querySelector(".st-key-hidden_settings button");
      if (s) s.click();
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "o" || e.key === "O")) {
      e.preventDefault();
      var nn = doc.querySelector(".st-key-nav_new button");
      if (nn) nn.click();
    }
  };
  doc.addEventListener("keydown", P.__chandlioKeys, true);

  /* Put the cursor in the search box as soon as the popup opens */
  if (P.__chandlioDlg) { P.clearInterval(P.__chandlioDlg); }
  P.__chandlioDlgOpen = false;
  P.__chandlioDlg = P.setInterval(function () {
    var i = srchInput();
    if (i && !P.__chandlioDlgOpen) { P.__chandlioDlgOpen = true; i.focus(); }
    if (!i) { P.__chandlioDlgOpen = false; }
  }, 200);

  /* Keep the top bar starting exactly where the sidebar ends (so the chat title is never hidden) */
  function setSbw() {
    var sb = doc.querySelector('[data-testid="stSidebar"]');
    var w = 0;
    if (sb) { w = Math.round(sb.getBoundingClientRect().right); }
    if (w < 8) { w = 56; doc.documentElement.setAttribute("data-sbcollapsed", "1"); }   /* collapsed: leave room for the expand button */
    else { doc.documentElement.removeAttribute("data-sbcollapsed"); }
    doc.documentElement.style.setProperty("--sbw", w + "px");
  }
  setSbw();
  if (P.__chandlioSbw) { P.clearInterval(P.__chandlioSbw); }
  P.__chandlioSbw = P.setInterval(setSbw, 300);

  /* Message box grows with the text (up to ~8 lines), shrinks back after sending */
  function grow(t) {
    t.style.setProperty("height", "44px", "important");
    var h = Math.min(Math.max(t.scrollHeight, 44), 200);
    t.style.setProperty("height", h + "px", "important");
  }
  function growAll() {
    var t = doc.querySelector(".st-key-inputbar textarea");
    if (t) { grow(t); }
  }
  if (P.__chandlioGrow) { doc.removeEventListener("input", P.__chandlioGrow, true); }
  P.__chandlioGrow = function (e) {
    if (e.target && e.target.tagName === "TEXTAREA" && e.target.closest(".st-key-inputbar")) { grow(e.target); }
  };
  doc.addEventListener("input", P.__chandlioGrow, true);
  [100, 400, 900].forEach(function (d) { P.setTimeout(growAll, d); });

  var oldBox = doc.getElementById("chandlio-scroll");
  if (oldBox) oldBox.remove();
})();
"""

# Scrolls the chat to the newest message, smoothly, like Claude
SCROLL_JS = """
(function () {
  var P = window.parent, doc = P.document;
  function go() {
    [doc.querySelector('[data-testid="stMain"]'),
     doc.querySelector('section.main'),
     doc.querySelector('[data-testid="stAppViewContainer"]')].forEach(function (el) {
      if (el && el.scrollHeight > el.clientHeight) {
        el.scrollTo({top: el.scrollHeight, behavior: "smooth"});
      }
    });
  }
  [0, 250, 700].forEach(function (d) { P.setTimeout(go, d); });
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
    st.button("hidden settings", key="hidden_settings", on_click=open_settings)
    run_js(KEYS_AND_SCROLL_JS)

    has_msgs = bool(st.session_state["chat_sessions"][st.session_state["current_chat"]])

    with st.container(key="inputbar"):
        with st.container(key="pill"):
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

            # Row 1: the message box
            st.text_area("Message", key="msg_box", placeholder="How can I help you today?",
                         height=68, label_visibility="collapsed")

            # Row 2:  +  |  Chat / Cowork  |  ........  |  model  |  mic  |  send
            c_plus, c_mode, c_gap, c_model, c_mic, c_send = st.columns(
                [0.7, 2.6, 2.6, 2.6, 0.9, 0.8], vertical_alignment="center")

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

            with c_mode:
                with st.container(key="mode_wrap"):
                    if hasattr(st, "segmented_control"):
                        st.segmented_control("Mode", ["Chat", "Cowork"], default="Chat", key="mode_sel",
                                             on_change=on_mode_change, label_visibility="collapsed")
                    else:
                        st.radio("Mode", ["Chat", "Cowork"], key="mode_sel", horizontal=True,
                                 on_change=on_mode_change, label_visibility="collapsed")

            with c_model:
                st.markdown(f"<div class='mdl-in'>{MODEL_LABEL}<b>{MODEL_NOTE}</b></div>", unsafe_allow_html=True)

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

        if has_msgs or st.session_state["pending_prompt"] is not None:
            st.markdown(
                "<div class='input-foot'><span class='dis'>Chandlio is AI and can make mistakes. "
                "Please double-check responses.</span></div>",
                unsafe_allow_html=True)

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

# ---------------- PROJECTS PAGE (from the video) ----------------
_PROJECTS_EMPTY_SVG = ('<svg width="60" height="60" viewBox="0 0 64 64"><rect x="6" y="8" width="20" height="20" rx="1"/>'
                       '<rect x="30" y="8" width="20" height="20" rx="1"/><rect x="6" y="32" width="20" height="20" rx="1"/>'
                       '<rect x="30" y="30" width="22" height="22" rx="2" fill="#3a3a3a"/>'
                       '<path d="M44 58V44a3 3 0 0 1 6 0v6l4-1.5a3 3 0 0 1 3 4.5l-4 6"/></svg>')

def render_projects_page():
    with st.container(key="pj_head"):
        c1, c2, c3, c4 = st.columns([8, 0.7, 0.7, 2], vertical_alignment="center")
        with c1:
            st.markdown("<div class='pg-title'>Projects</div>", unsafe_allow_html=True)
        with c2:
            st.button(" ", icon=":material/search:", key="pj_search_btn", on_click=toggle_state, args=("proj_search_on",))
        with c3:
            st.button(" ", icon=":material/swap_vert:", key="pj_sort_btn", on_click=toggle_proj_sort)
        with c4:
            with st.container(key="pj_new"):
                st.button("New project", key="pj_new_btn", on_click=open_newproject)

    pq = ""
    if st.session_state["proj_search_on"]:
        pq = (st.text_input("Search projects", key="proj_q", placeholder="Search projects",
                            label_visibility="collapsed") or "").strip().lower()

    items = [(n, p) for n, p in st.session_state["projects"].items()
             if not pq or pq in n.lower() or pq in p["description"].lower()]
    if st.session_state["proj_sort"] == "recent":
        items = items[::-1]
    else:
        items = sorted(items, key=lambda x: x[0].lower())

    if not st.session_state["projects"]:
        st.markdown(
            f"<div class='pg-empty'>{_PROJECTS_EMPTY_SVG}<div class='t1'>Looking to start a project?</div>"
            "<div class='t2'>Upload materials, set custom instructions, and organize conversations in one space.</div></div>",
            unsafe_allow_html=True)
        with st.container(key="pj_empty"):
            st.button("New project", key="pj_empty_btn", on_click=open_newproject)
    elif not items:
        st.markdown("<div class='pg-empty'><div class='t1'>No projects match your search.</div></div>",
                    unsafe_allow_html=True)
    else:
        with st.container(key="pj_cards"):
            cols = st.columns(2, gap="medium")
            for i, (name, p) in enumerate(items):
                with cols[i % 2]:
                    with st.container(key=f"pcard_{i}"):
                        desc = _html.escape(p["description"]) if p["description"] else "No description"
                        nfiles = len(p["files"])
                        st.markdown(
                            f"<div class='pcard'><div class='pc-title'>{_html.escape(name)}</div>"
                            f"<div class='pc-desc'>{desc}</div>"
                            f"<div class='pc-meta'>{nfiles} file{'s' if nfiles != 1 else ''}</div></div>",
                            unsafe_allow_html=True)
                        st.button(" ", key=f"pbtn_{i}", on_click=open_project, args=(name,))

# ---------------- ARTIFACTS PAGE (from the video) ----------------
_ARTIFACTS_EMPTY_SVG = ('<svg width="60" height="60" viewBox="0 0 64 64"><path d="M6 56 22 10l16 46z"/>'
                        '<circle cx="42" cy="24" r="12" fill="#3a3a3a"/><rect x="34" y="38" width="22" height="18" rx="1"/></svg>')
_TILE_SVGS = {
    "docs": '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/></svg>',
    "slides": '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 4h16"/><rect x="5" y="4" width="14" height="10" rx="1"/>'
              '<path d="M12 14v4M9 21l3-3 3 3"/></svg>',
    "design": '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 0 18c1.4 0 2-1 1.6-2.2-.4-1.2.3-2.3 1.6-2.3H17a4 4 0 0 0 4-4C21 6.5 17 3 12 3z"/>'
              '<circle cx="8" cy="11" r=".9"/><circle cx="12" cy="7.5" r=".9"/><circle cx="16" cy="10" r=".9"/></svg>',
}
_TILES = [("docs", "Docs", "Help me write a document about "),
          ("slides", "Slides", "Help me create a presentation about "),
          ("design", "Design", "Help me design ")]

def render_artifacts_page():
    st.markdown("<div class='pg-title'>Artifacts</div>", unsafe_allow_html=True)

    with st.container(key="art_bar"):
        t1, t2, t3, t4, t5 = st.columns([8, 0.55, 0.55, 0.55, 0.55], vertical_alignment="center")
        with t1:
            with st.container(key="art_tabs"):
                if hasattr(st, "segmented_control"):
                    st.segmented_control("Artifacts view", ["All", "Yours", "Shared with you"], default="All",
                                         key="art_tab", label_visibility="collapsed")
                else:
                    st.radio("Artifacts view", ["All", "Yours", "Shared with you"], key="art_tab", horizontal=True,
                             label_visibility="collapsed")
        with t2:
            st.button(" ", icon=":material/search:", key="ab_search", on_click=toggle_state, args=("art_search_on",))
        with t3:
            st.button(" ", icon=":material/filter_list:", key="ab_filter", on_click=toggle_state, args=("art_newest_first",))
        with t4:
            st.button(" ", icon=":material/view_list:", key="ab_list", on_click=toggle_state, args=("art_list_view",))
        with t5:
            st.button(" ", icon=":material/add:", key="ab_plus", on_click=go_chat, args=("Help me build ",))

    tab = st.session_state.get("art_tab") or "All"
    aq = ""
    if st.session_state["art_search_on"]:
        aq = (st.text_input("Search artifacts", key="art_q", placeholder="Search artifacts",
                            label_visibility="collapsed") or "").strip().lower()

    st.markdown("<div class='art-label'>Make something new</div>", unsafe_allow_html=True)
    tcols = st.columns([1, 1, 1, 6], gap="small")
    for col, (kind, label, prefill) in zip(tcols, _TILES):
        with col:
            with st.container(key=f"tile_{kind}"):
                st.markdown(f"<div class='tile t-{kind}'>{_TILE_SVGS[kind]}</div><div class='tile-label'>{label}</div>",
                            unsafe_allow_html=True)
                st.button(" ", key=f"tbtn_{kind}", on_click=go_chat, args=(prefill,))

    items = []
    if tab in ("All", "Yours"):
        items = [(i, a) for i, a in enumerate(st.session_state["artifact_items"])
                 if not aq or aq in a["title"].lower() or aq in a["content"].lower()]
        if st.session_state["art_newest_first"]:
            items = items[::-1]

    if items:
        with st.container(key="art_cards"):
            ncols = 1 if st.session_state["art_list_view"] else 3
            cols = st.columns(ncols, gap="medium")
            for n, (i, a) in enumerate(items):
                with cols[n % ncols]:
                    with st.container(key=f"acard_{i}"):
                        snippet = _html.escape(a["content"].replace("```", "").strip()[:110])
                        st.markdown(
                            f"<div class='pcard'><div class='pc-title'>{_html.escape(a['title'])}</div>"
                            f"<div class='pc-desc'>{snippet}</div><div class='pc-meta'>Artifact</div></div>",
                            unsafe_allow_html=True)
                        st.button(" ", key=f"abtn_{i}", on_click=open_artifact, args=(i,))
    elif tab == "All":
        if aq:
            st.markdown("<div class='pg-empty'><div class='t1'>No artifacts match your search.</div></div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='pg-empty'>{_ARTIFACTS_EMPTY_SVG}<div class='t1'>Your artifacts live here</div>"
                f"<div class='t2'>Start from a template above, or ask {AI_NAME} to build something in any chat.</div></div>",
                unsafe_allow_html=True)
    elif tab == "Yours":
        msg = "No artifacts match your search." if aq else "Create your first artifact"
        sub = "" if aq else f"Artifacts you build with {AI_NAME} appear here."
        st.markdown(f"<div class='pg-note'><div class='t1'>{msg}</div><div class='t2'>{sub}</div></div>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<div class='pg-note'><div class='t1'>No shared artifacts yet</div>"
                    "<div class='t2'>When someone shares an artifact with you, it appears here.</div></div>",
                    unsafe_allow_html=True)

# ---------------- MAIN WINDOW ----------------
if st.session_state.get("toast"):
    st.toast(st.session_state.pop("toast"))

active_key = st.session_state["stored_groq_key"]

if not active_key:
    st.markdown(f"<div style='height:14vh'></div><div class='hero'><img src='{STAR_URI}'>Welcome to Chandlio</div>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a1a1aa;'>Open the account menu (bottom-left) → Settings and paste your free Groq API key to unlock the application.</p>", unsafe_allow_html=True)
    st.stop()

# Projects / Artifacts pages replace the chat screen (no top bar, no input bar), like in the video
if st.session_state["page"] in ("projects", "artifacts"):
    run_js(KEYS_AND_SCROLL_JS)
    if st.session_state["page"] == "projects":
        render_projects_page()
    else:
        render_artifacts_page()
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
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3, max_tokens=2048, api_key=active_key)

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
            with st.container(key="plan_wrap"):
                st.button("Free plan · :blue[Upgrade]", key="plan_upgrade", on_click=soon,
                          args=("Upgrade is not available yet.",))
            st.markdown(
                f"<div style='height:9vh'></div>"
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
            st.session_state["scroll_bottom"] = True
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

            # jump down right away so you see your message + "Thinking..." (like Claude)
            run_js(SCROLL_JS)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    lower_prompt = prompt.lower()
                    if "switzerland" in lower_prompt or "swiss" in lower_prompt:
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
                _t = prompt.strip().replace("\n", " ")
                st.session_state["artifact_items"].append(
                    {"title": (_t[:40] + "…") if len(_t) > 40 else (_t or "Artifact"), "content": answer})

            # Generate a short Claude-style title once per chat, then refresh sidebar + top bar
            chat_key = st.session_state["current_chat"]
            if not st.session_state["chat_titles"].get(chat_key):
                new_title = make_title(prompt, answer)
                if new_title:
                    st.session_state["chat_titles"][chat_key] = new_title
                    st.rerun()

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

# Input bar (docked at the bottom) + starter chips on an empty chat
try:
    render_input_bar()
    if not st.session_state["chat_sessions"][st.session_state["current_chat"]] and st.session_state["panel"] is None:
        render_starter_chips()
except Exception as e:
    st.error(f"Input bar failed to load: {e}")

# Scroll to the newest message (after a send, or when switching chats)
if st.session_state.get("scroll_bottom"):
    st.session_state["scroll_bottom"] = False
    run_js(SCROLL_JS)
