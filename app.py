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
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&display=swap');
:root { --serif: "Source Sans 3", "Segoe UI", Arial, sans-serif; --ui-font: "Source Sans 3", "Segoe UI", Arial, sans-serif; }
html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], button, input, textarea, select, [data-baseweb], [data-testid="stMarkdownContainer"] { font-family: var(--ui-font) !important; }
[data-testid="stApp"] { font-family: var(--ui-font) !important; }

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
    library_auto_save(name, mime, data)
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
    catalog = dict(CUSTOMIZE_SKILLS)
    catalog.update(st.session_state.get("customize_user_skills", {}))
    for name in st.session_state.get("customize_active_skills", []):
        if name in catalog:
            base += "\n\nSkill guidance (apply when relevant): " + name + "\n" + catalog[name][1]
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

# ---------------- PRIVATE FILE LIBRARY ----------------
# Default: SQLite on server disk. Set CHANDLIO_LIBRARY_DIR to a persistent mount.
# Optional permanent cloud storage: create a PRIVATE Supabase Storage bucket,
# then add the following SERVER-ONLY Streamlit Secrets (never commit the key):
# [library_storage]
# supabase_url = "https://YOUR-PROJECT.supabase.co"
# service_role_key = "YOUR-SERVER-ONLY-KEY"
# bucket = "chandlio-library"
# Access keys are bearer credentials: anyone with a key can open that library.
# This feature does not grant the AI access to files until the user attaches them.


def library_access_key():
    import secrets
    return st.session_state.setdefault("library_access_key", "clib_" + secrets.token_urlsafe(32))


def library_vault():
    return hashlib.sha256(library_access_key().encode()).hexdigest()


def library_cloud_config():
    try:
        cfg = dict(st.secrets.get("library_storage", {}))
    except (FileNotFoundError, KeyError):
        cfg = {}
    if cfg:
        from urllib.parse import urlsplit
        url = urlsplit(cfg.get("supabase_url", ""))
        if url.scheme != "https" or not url.hostname or url.username or url.password or not cfg.get("service_role_key") or not cfg.get("bucket"):
            raise ValueError("Library cloud storage configuration is incomplete.")
        return cfg
    return None


def library_db():
    import sqlite3
    folder = pathlib.Path(os.environ.get("CHANDLIO_LIBRARY_DIR", str(pathlib.Path(__file__).resolve().parent / "chandlio_library_data")))
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    dbpath = folder / "library.sqlite3"
    conn = sqlite3.connect(str(dbpath), timeout=20)
    try:
        os.chmod(dbpath, 0o600)
        conn.execute("CREATE TABLE IF NOT EXISTS files (vault TEXT NOT NULL, id TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL, created TEXT NOT NULL, source TEXT NOT NULL, data BLOB NOT NULL, PRIMARY KEY(vault,id))")
        conn.commit()
    except Exception:
        conn.close()
        raise
    conn.row_factory = sqlite3.Row
    return conn


def library_cloud_request(method, route, **kwargs):
    from urllib.parse import quote
    cfg = library_cloud_config()
    headers = {"apikey":cfg["service_role_key"], "Authorization":"Bearer " + cfg["service_role_key"]}
    headers.update(kwargs.pop("headers", {}))
    url = cfg["supabase_url"].rstrip("/") + "/storage/v1/" + route.format(bucket=quote(cfg["bucket"], safe=""))
    response = requests.request(method, url, headers=headers, timeout=40, allow_redirects=False, **kwargs)
    if not 200 <= response.status_code < 300:
        raise ValueError("The Library storage service could not complete the request.")
    return response


def library_clean_name(name):
    name = str(name).replace("\\", "/").split("/")[-1]
    name = "".join(c for c in name if ord(c) >= 32).strip() or "Untitled file"
    # Bound Unicode byte length, preserving the extension when possible.
    if len(name.encode("utf-8")) > 180:
        ext = pathlib.Path(name).suffix[:20]
        name = name.encode("utf-8")[:140].decode("utf-8", errors="ignore") + ext
    return name


def library_save(name, mime, data, source="Upload"):
    from datetime import datetime, timezone
    import mimetypes
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("File bytes are required.")
    if len(data) > 50 * 1024 * 1024:
        raise ValueError("Library files must be 50 MB or smaller.")
    name = library_clean_name(name)
    mime = (mime or mimetypes.guess_type(name)[0] or "application/octet-stream").split(";")[0]
    if "\r" in mime or "\n" in mime:
        mime = "application/octet-stream"
    digest = hashlib.sha256(name.encode() + b"\0" + data).hexdigest()
    encoded = base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")
    file_id = digest + "--" + encoded
    vault = library_vault()
    seen = st.session_state.setdefault("library_saved_in_session", set())
    marker = vault + ":" + file_id
    if marker in seen:
        return file_id
    if library_cloud_config():
        # Stable names and upsert keep repeated chat uploads from duplicating files.
        library_cloud_request("POST", "object/{bucket}/" + vault + "/" + file_id,
                              data=bytes(data), headers={"Content-Type":mime, "x-upsert":"true"})
    else:
        conn = library_db()
        try:
            with conn:
                conn.execute("INSERT OR IGNORE INTO files VALUES (?,?,?,?,?,?,?,?)",
                             (vault,file_id,name,mime,len(data),datetime.now(timezone.utc).isoformat(),source,bytes(data)))
        finally:
            conn.close()
    seen.add(marker)
    return file_id


def library_list():
    vault = library_vault()
    if library_cloud_config():
        rows = []
        offset = 0
        while True:
            page = library_cloud_request("POST", "object/list/{bucket}", json={"prefix":vault + "/", "limit":100, "offset":offset, "sortBy":{"column":"created_at","order":"desc"}}).json()
            if not isinstance(page, list):
                raise ValueError("Invalid Library storage response.")
            for row in page:
                file_id = row.get("name", "")
                if "--" not in file_id or not row.get("id"):
                    continue
                try:
                    encoded = file_id.split("--",1)[1]
                    name = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
                except (ValueError, UnicodeError):
                    continue
                metadata = row.get("metadata") or {}
                rows.append({"id":file_id,"name":name,"mime":metadata.get("mimetype", "application/octet-stream"),"size":int(metadata.get("size",0)),"created":row.get("created_at", ""),"source":"Library"})
            if len(page) < 100:
                return rows
            offset += len(page)
    conn = library_db()
    try:
        return [dict(row) for row in conn.execute("SELECT id,name,mime,size,created,source FROM files WHERE vault=? ORDER BY created DESC",(vault,))]
    finally:
        conn.close()


def library_get(file_id):
    from urllib.parse import quote
    # IDs never accept a caller-controlled directory or a different vault.
    import re
    if not re.fullmatch(r"[0-9a-f]{64}--[A-Za-z0-9_-]+", file_id):
        raise ValueError("Invalid Library file.")
    if library_cloud_config():
        r = library_cloud_request("GET", "object/authenticated/{bucket}/" + library_vault() + "/" + quote(file_id, safe=""))
        return r.content
    conn = library_db()
    try:
        row = conn.execute("SELECT data FROM files WHERE vault=? AND id=?",(library_vault(),file_id)).fetchone()
        if row is None:
            raise ValueError("This file is no longer in your Library.")
        return bytes(row["data"])
    finally:
        conn.close()


def library_delete(file_id):
    # Listing first verifies the file belongs to the active library.
    if not any(row["id"] == file_id for row in library_list()):
        raise ValueError("File not found in this Library.")
    if library_cloud_config():
        library_cloud_request("DELETE", "object/{bucket}", json={"prefixes":[library_vault() + "/" + file_id]})
    else:
        conn = library_db()
        try:
            with conn:
                conn.execute("DELETE FROM files WHERE vault=? AND id=?",(library_vault(),file_id))
        finally:
            conn.close()
    st.session_state.setdefault("library_saved_in_session",set()).add(library_vault() + ":" + file_id)


def library_auto_save(name, mime, data, source="Chat upload"):
    try:
        library_save(name, mime, data, source)
    except Exception:
        st.session_state["library_save_error"] = "A file could not be saved to Library. Keep a downloaded copy and check Library storage."


def library_import_session():
    # Bring files already uploaded in this running session into Library, too.
    for f in st.session_state.get("attachments", []):
        library_auto_save(f["name"], f.get("type", ""), f["data"])
    for project in st.session_state.get("projects", {}).values():
        for f in project.get("files", []):
            library_auto_save(f["name"], f.get("type", ""), f["data"], "Project")
    for messages in st.session_state.get("chat_sessions", {}).values():
        for message in messages:
            for f in message.get("files", []):
                library_auto_save(f["name"], f.get("type", ""), f["data"])
            for image_data in message.get("images", []):
                if isinstance(image_data, bytes):
                    library_save_photo(image_data)
    for artifact in st.session_state.get("artifact_items", []):
        library_auto_save(artifact.get("title", "Artifact") + ".md", "text/markdown", artifact["content"].encode(), "Artifact")


def library_save_photo(data):
    mime = _sniff_mime(data) or ("image/gif" if data[:3] == b"GIF" else "application/octet-stream")
    ext = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp","image/gif":"gif"}.get(mime,"bin")
    library_auto_save("Photo_" + hashlib.sha256(data).hexdigest()[:12] + "." + ext, mime, data, "Chat photo")


def render_library_page():
    st.markdown("""<style>
    .st-key-library_page .lib-title {font-size:2rem;font-weight:400;margin:10px 0 6px;}
    .st-key-library_page .lib-note {color:#999;margin-bottom:20px;}
    .st-key-library_page [data-testid="stExpander"] {border-color:#383838;border-radius:14px;}
    </style>""",unsafe_allow_html=True)
    with st.container(key="library_page"):
        st.markdown("<div class='lib-title'>Library</div><div class='lib-note'>Your files and photos, together in one place.</div>",unsafe_allow_html=True)
        try:
            cloud = bool(library_cloud_config())
        except Exception:
            st.error("Library cloud storage is not configured correctly. Check the app’s storage settings.")
            return
        if cloud:
            st.caption("Cloud storage · Chat uploads, displayed photos, and code artifacts save automatically.")
        else:
            st.info("Files are saved on this server’s disk. Streamlit Cloud can reset that disk. For permanent cloud storage, configure a private storage bucket in the app’s settings.")
        with st.expander("Keep access to your Library"):
            st.write("Download your private access key once. Use it to reopen this Library after a refresh or on another browser. Anyone with this key can access its files.")
            st.download_button("Save my Library access key", data=library_access_key(), file_name="Chandlio_Library_Access_Key.txt", mime="text/plain", key="lib_download_key")
            with st.form("lib_restore_form"):
                restore = st.text_input("Open an existing Library", type="password", placeholder="Paste your Library access key")
                if st.form_submit_button("Open Library"):
                    import re
                    if not re.fullmatch(r"clib_[A-Za-z0-9_-]{43}",restore.strip()):
                        st.error("Enter the complete Library access key.")
                    else:
                        st.session_state["library_access_key"] = restore.strip()
                        st.session_state.pop("lib_selected",None)
                        st.session_state["lib_upload_nonce"] = st.session_state.get("lib_upload_nonce",0) + 1
                        st.rerun()
        uploads = st.file_uploader("Add files or photos", accept_multiple_files=True, key="lib_upload_" + str(st.session_state.get("lib_upload_nonce",0)), help="Up to 50 MB per file. Files are stored without being executed.")
        for f in uploads or []:
            try:
                library_save(f.name,f.type,f.getvalue(),"Library upload")
            except Exception:
                st.error("Could not save " + f.name + ". Check file size and storage configuration.")
        if st.session_state.get("library_save_error"):
            st.warning(st.session_state["library_save_error"])
        try:
            rows = library_list()
        except Exception:
            st.error("Could not open Library storage. Your files have not been cleared; check the storage connection.")
            return
        search, filter_col, sort_col = st.columns([2,1,1])
        query = search.text_input("Search Library", placeholder="Search files and photos", label_visibility="collapsed").casefold().strip()
        kind = filter_col.selectbox("Type",["All files","Photos","Documents","Other"])
        sort = sort_col.selectbox("Sort",["Newest first","Oldest first","Name"])
        def category(r):
            if r['mime'].startswith('image/') or r['name'].lower().endswith(('.png','.jpg','.jpeg','.gif','.webp','.bmp')):
                return 'Photos'
            if r['mime'].startswith('text/') or r['name'].lower().endswith(('.pdf','.doc','.docx','.xlsx','.csv','.pptx','.txt','.md')):
                return 'Documents'
            return 'Other'
        visible = [r for r in rows if (not query or query in r['name'].casefold()) and (kind=='All files' or category(r)==kind)]
        if sort=='Oldest first': visible.reverse()
        if sort=='Name': visible.sort(key=lambda r:r['name'].casefold())
        st.caption(str(len(rows)) + " saved items · " + f"{sum(r['size'] for r in rows)/1024/1024:.1f} MB")
        if not visible:
            st.write("No matching files." if rows else "Your Library is ready. Upload a file or photo to start.")
        # Paginate the list and load file bytes only when opening an item.
        pages = max(1,(len(visible)+19)//20)
        page = int(st.number_input("Page",min_value=1,max_value=pages,value=1,step=1,key="lib_page_" + hashlib.sha256((query+kind+sort+str(pages)).encode()).hexdigest()[:12]))
        for row in visible[(page-1)*20:page*20]:
            col, action = st.columns([5,1],vertical_alignment="center")
            with col:
                st.write(row['name'])
                st.caption(category(row) + " · " + f"{row['size']/1024:.0f} KB" + " · " + row['created'][:10])
            if action.button("Open",key="lib_open_"+row['id'],use_container_width=True):
                st.session_state["lib_selected"] = row['id']
        selected = next((r for r in rows if r['id']==st.session_state.get('lib_selected')),None)
        if selected:
            st.divider()
            st.write("**" + _html.escape(selected['name']) + "**")
            try:
                data = library_get(selected['id'])
                if category(selected)=='Photos':
                    try:
                        from PIL import Image
                        with Image.open(io.BytesIO(data)) as im:
                            if im.width*im.height>30_000_000:
                                raise ValueError('Large image')
                            im.thumbnail((1200,900))
                            st.image(im.copy(),caption=selected['name'])
                    except Exception:
                        st.caption("A preview is unavailable. Download the original file below.")
                elif selected['mime'].startswith('text/') or selected['name'].lower().endswith(('.py','.json','.js','.html','.css','.csv','.md','.txt')):
                    st.code(data[:30000].decode('utf-8',errors='replace'),language=None)
                elif selected['name'].lower().endswith(('.pdf','.docx')):
                    text=file_to_text({'name':selected['name'],'type':selected['mime'],'data':data})
                    if text: st.text(text)
                st.download_button("Download original",data=data,file_name=selected['name'],mime=selected['mime'],key='lib_download_'+selected['id'])
                if st.button("Attach to chat",key='lib_attach_'+selected['id']):
                    add_attachment(selected['name'],selected['mime'],data)
                    st.session_state['page']='chat'
                    st.rerun()
                with st.expander("Delete file"):
                    confirmed=st.checkbox("Delete this file from Library",key='lib_confirm_'+selected['id'])
                    if st.button("Delete permanently",disabled=not confirmed,key='lib_delete_'+selected['id']):
                        library_delete(selected['id'])
                        st.session_state.pop('lib_selected',None)
                        st.session_state['lib_upload_nonce']=st.session_state.get('lib_upload_nonce',0)+1
                        st.rerun()
            except Exception:
                st.error("This file could not be opened. Check the storage connection and try again.")



# ---------------- CUSTOMIZE CATALOG ----------------
# Catalog entries are visible without a model key. External services require
# provider-specific authorization before Chandlio can access their data.
CUSTOMIZE_APPS = [
    ("Google Workspace", "Mail, documents, calendars, and files in one place.", "Everyday tools", "GW", "#4285f4"),
    ("Search services", "Find information across your search services.", "Everyday tools", "G", "#4285f4"),
    ("Google Photos", "Organize and find your photos.", "Creative expressions", "P", "#ea4335"),
    ("YouTube", "Discover videos and channels.", "Media streaming", "▶", "#ff0033"),
    ("Adobe", "Create and refine visual designs.", "Creative expressions", "A", "#eb1000"),
    ("Canva", "Explore designs and creative projects.", "Creative expressions", "C", "#8b3dff"),
    ("Dropbox", "Find and organize your files.", "Everyday tools", "D", "#0061ff"),
    ("Granola", "Work with meeting notes and summaries.", "Business essentials", "G", "#9eae34"),
    ("Hootsuite", "Plan and manage social content.", "Business essentials", "H", "#ff5148"),
    ("Picsart", "Create and edit visual media.", "Creative expressions", "P", "#b322df"),
    ("VistaPrint", "Prepare print designs and business materials.", "Creative expressions", "V", "#238cba"),
    ("Webflow", "Work with website projects.", "Creative expressions", "W", "#146ef5"),
    ("Wispr", "Work with recordings and transcriptions.", "Everyday tools", "W", "#56594b"),
    ("Wix", "Manage and build your website.", "Business essentials", "Wix", "#233946"),
    ("monday.com", "Organize projects, tasks, and teamwork.", "Business essentials", "m", "#ee4873"),
    ("Contacts", "Find and organize contact information.", "Everyday tools", "C", "#1967d2"),
    ("YouTube Music", "Discover music, artists, and playlists.", "Media streaming", "♫", "#ff0033"),
    ("AndroidDevSummit", "Explore Android developer event information.", "Business essentials", "A", "#368f55"),
    ("Fever", "Explore live events and entertainment.", "Dining and entertainment", "F", "#555555"),
    ("Shopify", "Work with store products and business tasks.", "Business essentials", "S", "#779e38"),
    ("Xero", "Organize accounting and invoice workflows.", "Business essentials", "X", "#1377d4"),
    ("Chandlio Notebook", "Organize notes and reference material.", "Everyday tools", "N", "#7b8ff5"),
    ("Google Ads", "Plan advertising campaigns.", "Business essentials", "A", "#4285f4"),
    ("Google Business Profile", "Organize your business profile information.", "Business essentials", "B", "#4285f4"),
    ("Verify AI", "Explore media provenance workflows.", "Creative expressions", "✓", "#616674"),
]
CUSTOMIZE_SKILLS = {
    "Match your writing style": ("Use your writing samples to shape new drafts.", "For writing tasks, ask for a representative writing sample if none is available. Match its tone, vocabulary, sentence length, and structure without inventing personal facts."),
    "Focus your energy": ("Plan your workload around your time and energy.", "For planning tasks, help prioritize a manageable workload based on the user's available time and energy. Suggest focused work blocks and realistic breaks."),
    "Get more perspectives": ("Explore 3–5 useful viewpoints before deciding.", "When evaluating a decision or idea, offer 3 to 5 distinct perspectives, explain their tradeoffs, and identify assumptions."),
    "Generate fresh ideas": ("Turn a starting point into five fresh directions.", "For brainstorming requests, generate five distinct, practical ideas with a short explanation of each. Avoid superficial variations."),
    "Prep for meetings": ("Prepare an agenda, key questions, and a brief.", "For meeting preparation, use the context provided to draft a concise brief, objectives, agenda, key questions, and follow-up actions. Ask for missing meeting context when needed."),
}


CUSTOMIZE_LOGOS = {'Google Workspace': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAADN0lEQVQ4jZ2US2icVRTHf+d+r3k0GZXYGAwzbRBFlDYQcCNIFbFUUExLXVTqA6QI3SSFUlAQEXQjqbgtWVSkokELPgo2YhMEpWIXQZSWWkiMFpOaNI/JZOab7373uJgkbZKRUg/czeF/fpz/PedeoUnooZ6AP/K9pGYv0I3QBSYGueZMdN6QniGOh2R01G6slU2w/Y/0kngDWLONenBDpgLigwQ4L0TFjGPkiP/VZ1/8J1Bfe+g4sd9HHMBSCPWwAVJpSCUEE64CQTxAXvG/PPXhKsOswT7YOkDbch9hCq0xZBPwLKgDtAJcRxzKutJhbzH49OamDICeDZ/jnmo/7VXIptBWg9Z6max7G9/bLsMjLTL8XRth1CFijoEsgDvjRcmzMnqyts6yDuHRGl1hISxxLd+wWon+ZCq7SwZ/GW86tGf2F+m48285cSLZNBT9OXoaK1+zbGA+gGW/TlV2yKGZy81gtwqfIDiA78AHwgRmdVAOLv4vGICvWn8Y8RFfIAfYdLCZsPtddc3yRh1uZVkyWu8z6upFFBCDGoHOysXb6cghII0Tm6BkNimqhdztAJEbq+wwvg9MovaOVJU6ik3TB4Efm5SOKgqkgNdgQRdQXH0fAtN+Cr86Z3fUcCwqVFQPNAOOvS5PbMztfMedFqG4llAmjHN8PK9Qdo45VWZUXv3kp+j+Wzl94L3qduvFe6xYEhPjcE6Eb0WH8M4XuTKtlCoqJPhcVX/y93ph18nHpyaawToHf7vLxuZsKtITJVsI0wxRkj938Vj2SSPPk6rQDzCjhnHn8Y8GxVmTH9t57tE37x3Z07lGGnlrS3j6/RdmspculPN/9cTh4ppZMfrGyj02YuAHMzDpcv3zRCxohsu2iyXNs0QLqYZl6/LXnYYlTQpQ64SkgNhWgqRArtoxMHX4vqPrgAD7vm8/vqi5viVyXLUl6uSINYNiUDxSF6JpHhe3g22BtAWJt360fPCplxFRuOn7Avj8sekjVc3sm3MtExYh1nBleAZVQcRiTA0RC+rPitQOL7+4+6VV2KYOV6PnQk8wPretN5XcXpBukC7AojKFRmMuLXxTNnefYvfRysbafwFOiFhxqOMpZwAAAABJRU5ErkJggg==', 'Search services': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAt1BMVEVHcEz9/v7w8PHz8/T29/f29vf19fb8+/vr7O38/f329/f19fX29vf6+vr+/v755uX////x8vI5iBT///85qldGiPX7wBQ8rFpJivTrUELrTUDsUUTrSz7rT0I+hPTu8vIvqFBMjPWUtvj8vgbN3fz5y8fuZFXT69lVtGrrQzTzmpG84MVzwYaUzqPxfXD2rqn83IN+qff+7L38zkZpnfb2nCY9npTMuyqWtD4zgPRCkc5/tdRHcEwgFdBcAAAAPXRSTlMA8C0eiU6g/g3jdcBiO9H9qdH///////////////////////////////////////////////////////8AWkw1vQAAB9FJREFUeJztW+l2okgYHVkscOeoEAWExKiIolk6nXTP+7/XVAFGKL5aQJIfc3LTSTrniPf67VUU//zzg2YwVGU4HOop8H8U1fhG7qE+6HX7I7PTQVMM1OmYo363N9CH36BCGWiTUWcKojOaaAPlK9nVHpO8IKKnfhG9PjEF7LkGc6J/Ab1mIhn2DMjstctu9Gqw5xp67UWk0pMyPY1OS8GgDkZN6AlGgxYk6JOm9AQ3h6OqmbfwT6emdpMRhv3b6An6w+b8gxs/fgZz0JDe6NbOPQa0RhmptmD+C/oNAkFpnHwQRrV71LAV919h1lSgt8yPFdSqCO3zYy/UUDCU8H+w2ZzPcYrzebMJJBRIFwRh/KFNfNput+7C87y95/ku/uN03oiyti8ZB6L828SEekng+376Gwvxlu423vCvnEhlo8HtPkHs7j1MvCDwLwJyEfu9e+aaoStTkXrs69E49vYZ94X/KiDX4J/HHA0Sg9KQffn4vPUW7oItIJOwPY+Zb9ERBqLBTEB0PmE/u0IBGCd2PJoiJzADYBy7hL7Azxawd2OmEbp8/gFL+uaErQ8IWEIClt7+xEwIbj0yWBUAe991KQGAAXIBaSSwFIx4TtAYF8WuX+HnC8AKGF5AGpuf0QJQnJtf0gNZGDB9YDIzgVGCgvhifnkDcPg55Qg2ACrwywpgR0BqAkYcGl3w5eelNP9Sip9pAngI2rgLiJ8ISPn2ad7V4mdEgQGmwHjLMADOdW97OuFx4LTFXcgrlCERP2NMVqEVKDrBAYBZ4s14HKQYjzcn0iOXsvzTDtSXB9Arzy7A7xMSVKyZCM8o231mAF78fwJYq4BFcLz1K/z+cnECawyu1rL8UDlUgJeheAnwM8s8Om+5+V9EdTqDcnDzGYGf5l/67EZHjCDJDzRFIASvJejK7/FnLunVZEfGAy/2iTShYvJ5Z1kGEWgfQJPg03r95vpF/n1r/JXpEBjFg1fbtt9c7ypgH7e1YMeLBGEIoJc1FmCvt97FCB6cfs1ABYFe/WjoNRVAjJApWEqUOHmgcksE+kBgX/C2JQsR3+cnQF2UByNgFHlZFxQs/HYdgDEpCajWYfR0FWDjbFgu4lb5p6MivwqMAnYRWEGrETCllijALILWJQX2G8MAzw9iPEO7B6WpZFDNwhdKgP0EC/gzn6+yLxh/yPcjcGGn2JKB3fgnWsALLGB1n+OugPndPEP2GxZQrIWaWMArzP8p4O6urCD/kQpYPQAJXFqgAGXgtZ4Amn6ea8gEgEFQFAAMA5SANSMEcgF3FQOkCuY8AV2+ACoCagmYfzohF/BLJAAohLUE3FUsUDTAfA4KmPAFUCGwZiRBKqDKXzIAwwICATUsQPNTISgjAApCaQFV/osMvgsEQSidBRL84jQEChEt4JUh4E9TAUggoFKKGdMIU8C8IACshMVSXL01iirNiJEGLAFzkYBSM9Jv6IZQC5yXBcDNqDgUKsJ5YP1xhH3wCOF5XsIKElC6iQMsjVEpCtcfTnSATQAgeF6VBNxDAsoLZKv6gmsUru115DhhIi3g8b5sAbAMWEV+qBAUguDdmTlODRM8lA0AxiC1PgaWhsjOVka2/eGkmB0lbgwR0B4AYxCVF4cKsDLKffD+MXNySJrgofz54RBA1PIYmMtTH6zfo09+J9rJ8Ae/KA/AQ3GZHwqC4DU1/5XfcWScgKgIwCEAvYzeIoH2yJ7W7x9OCSGjGBT5yymAx/VfkAcqtw0M4J1f3iOHwkyogE5B7AHoElTZJoN26ZIZLQDHAd8Lj1QA4ioEesCi+UEf7I6QAl4u0P4n0xBos+pOpQFtkx2q/LPZLNnBfkC7f2l6lgE6wGYxtFEYQCZwwugASAh2iRP+Lo0B+B/DANC9M2CXZjoFTECMEEZJWUOwOyRRiK3z+2/ZAGAVpPdnMqhAQ8JxGEISnFnoHJPkcNhhHA6H5BiFhL6oYJWlAPSmUwu8iw3fMzzCCogZZk6UYXZhzyRc3bC6B3MGwQd7FNAEQQSFQaaBRGQalmUQBausCIEOmFqMgwTwmb1dCCuo8Bbw91KEwXdErHvosAlwIAIKePSZghWLn2kAlgmmh4oXBPQ4PogbwC7IMQD78AalQEifKvjL4OceqwLG84oCGXosIEwY/B3u7XP43iXpCiEU7w34BQcIgAVChiAJxbRX/tmB1bZNwUka5gkG3JikJYQRo10xa5CEE0hnCqUkcMwvPMFBABeDFLujMAxC3CQ4o2t1DqmCe5DvcMSFn0cf8eglD/UBG8dFCcnRgV1BPnzCHdw7cqdLDcFB6iDrvkUV5K/omBz482Ige9rbADZMSkBk/jgeIydlxmPiEZPvRGsGJH+2VZU5TxsEu08EgfgCJHWS7WID6RO18vex+vXO9rZ4pjcTSt+oFKK1U80Zv0QBoqE1eqgARsA5PcVGr7WjtU0f+NCtVtyArMYPGShtBALq3vDokdGT3BZi00uXP5YR+jdJCGTPEnOMMOCdkhV8/PGgjWd9DE2i0EL0QbMHGwAo3TqPWeX05i3BV5WgjVANDQiNtBuebQEx1PqyZkBmv3V6AlXXLHE0oMDS9K964M9QdK3P6f0oCPqarnzpc5eGquhda1xRgbkDq6t/07OnhqHqvW7fstITjWPL6nd7ump843OvP/jBD/5P+A/yWoK0uPJ8MwAAAABJRU5ErkJggg==', 'Google Photos': 'data:image/jpeg;base64,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', 'YouTube': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAMFBMVEVHcEz/ADP/ADP/ADP/ADP/ADP/ADP/ADP/ADP/////hpT/2uH/Smj/s8D/JEv/b4eB3bNwAAAACHRSTlMAQB+z1GXri3bBstgAAAKRSURBVHic7ZrpduMwCIUrGW1xMn3/t602J25s59RARGeG+zd1+Y4QaLsfHyqVSqVSqVSqv0C2yCxyxh0r/9pVP7L4kKaGCSFMVTBBke+KO/Jx+bX+af6kKP+HUMnMD2mscSVmC7YXB6UKVXCceYlhQonLFnYXBSCYo/DTW0OvNO0h2GHhK8ImE/a9I7+RfxoEMzj+M4GB0fFjhBXB2PwvWs2DIBE/xiCZgKJ7EoQGIEbXZ4DQAOQhaLPASMWP0chmoOdApgabghWdAn0SWLn4MVrZOdhmoZMEcLJF0LqxYBHkBSkDCBZBLoMMMHwrspbPAJLxY0S1geuVD8Bi2sBlvv2RBUgpfTIBGEwfKgBp5smDQwOkdONAcJhG2AHSfKEjBApAQaADIDrxA4Ceh4kKkIglSQcg5mHCrEVPAKSSBBaAPBWweeACSOmCQwDMarwLkOZPDILnA8h5QCwQHrMdOALIJXl+NrICYEqSGeB8SbIDnC3JNwCcGwR+gJOLAzvA2UL4t6pgRvRj1k6IWBQZW/HtilsLuFZD5EGBazlGb4qAYUtG2pmy7AkpxzSGXTFyK8QFQD8XkE5GmD3Qd5GOZrhd4DMA/nRMS34X/nh+Y4heAXA3JKTSW8vg7ojIp/K7rPwtmfg9ofxNqfhdsfhtufh7gfiLifibkeSrmf8d74bSL6fib8fyr+dyOVhcJNIOCjkPyd1GI9QMlwH4BT4ikWYE3/xso71sWzfbcDfd1lk5tBjDJnydioNGwe86KitCmADeSuEBpkNPaWMwzcsLnPbWbqotDt/XrtoHRjUyd2dx9xYDPKzFR3EWU3HzFN9Nxa4ZnX8UeheneavX9upXst1VXT5Dx1SpVCqVSqX6j/QFgvdUtSxW0v0AAAAASUVORK5CYII=', 'Adobe': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAALVBMVEVHcEzrDwDsDwDrDwDrEADrEAD////rAADzgHzvQTn+8O/829n5vrvxX1j2n5t6hMp4AAAABXRSTlMALHjF4orkj4AAAAOHSURBVHic7ZvbloIwDEW5CAjI/P/nDi0uQHPaXFw0L+RxcMzuyWlTkFbVZ9R10z66i+LRNnVd5aJuLku+QzRphLq9OvsWLUaomzLpI4Lj8N8ERISCw9+icc7/ReCQf50Op/o75F/j8EFR/x3RehYgRuNagBC1ZwFCtM4CbBK4OSDE6oL68v6Xi0ftW4FQA9cKhBo4zoEQbeVqgdUElW/+rrsBboAb4Aa4AYwAA4iSAMNfT+JlIzACTBSgLwgwLCB//zQR2BR4IYDZ9FUWgGFBFeinxSKBCQBY0GxDUwmgAGt0BgIDwPBM5DfZ0AIwpwCmIgAJC0YAgwQGADgH3zZUf5seYBiTAqwSjGoJ9ABJC4b4KwCQEcBiQy0AbgNHqFdDNUDGgiHUDUEJkLVgrIFWAi1Aog0cobWhFoARYJVA94VKAM6CIZSroRKAtAGqyHwhAGgD1BNKG+oASLoZ7M50+xINwDCSCryAK3QNQQVA28ACoHQ2VAGQXKvhwMqgaggKgGFEYwV/VTUEDQDxW6w26A4aG8oBQBuIyy6yoUIChQLIgvECtaGiISgUQBaMF36yoRgAWzBeAdtkeQ3kANRrQ/qSvCFIAYAFd6//ZEMxAC30kQPsEsQ2FAKAFfe0+wN0s7QhSAGoyqcx/mJDKQDdiXzci9ttKAMAc/BjuUW3S8IaCAHoCD8lBjYUNgQRQN6C8RNmG8oAqMJf0wxtl2X7EhkAtSAZntWGEgDOgvEz4JZJVAMRAGfBDt80imwoAADfTdvtAChF22MJAFUXrPRobyhpCJISUAuidRY8vZM8LOABwAyDxUWroaAhCACQBcEvJegWRWBDFgDUdhqXc2RIBTORBwATfDrHrjNaDXkbcgBI2JTOyIasBCxA9rnkpsf+YfBZtiGwAKwARxK0GrINgfUAn//kdYMNGQD+sVx/KjSqF2fDPAD7XHKLvQbgNpFrCAwAb8EQxzwAgjE2ZEogsGCIIwe9xjSELADqcDD2UepXwzwA82j8GOUOAGqWbwg5AKEF+1N/Rgtn3oZZAMkc3OKZs2F2JuYA+Dawx/5zGbLNPBoBuqc8DtlyF7UA6EWNRGT/yQxQIm6AG+AGuAH8X2x2f7Xb/eV299f73Q84uB/x8D/k4n7Mx/+gk/tRL//Dbv7H/XyK4H3k0vvQ6Vd+/2O/ZUUgwy8rQuLod0TwPfweEUof//8HsgFKEjMrYHwAAAAASUVORK5CYII=', 'Canva': 'data:image/jpeg;base64,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', 'Dropbox': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAFKklEQVRYhdWXfYiUVRTGf+f9nNHdVSlzSwPNiDUj0RY/yD7Mj9JcybSEkkpCjczQIi22TBILrE2EEP8okkyQxI0sNbUySf8og8VKyqiMtCy1VmfcnXm/7u2PO+vu7BdjBFsPDDMvc7jnuec857n3Feap40AFPYOMA/QH/B4i4FtA0EPJAQKrB5MD8D8gIEAokBVQhefuYmMgI+a7u9iSCCRAVhh0WcKcCaFZ8HyBSHtooAl699bcNymkvKxApLPYkgg0C0RCzdiYj5fm2LIwYPeSHKOHxRAC+cL2pPA7J4yuStjxWI7NCwIOLGtm8g0xBGLW6gLCPHWOFh9oKWFWuPQKRe30kEUTIlxfQyzgaDJZYe0el7q9HtnTFijw+moenxxSOz2kb0VrbJgX1n/qsvoDjzMnLSjXYBeqZZApJpAIvquYMybh6WkBwwYqdCgEcSvjlAfY0HDMYuV7HjoUnpgecuvwGGIhH7bG+g6IpzlywuKF933qv3SIYwH7AoNMcQuU+YwZEjNsoAINUVJcsigCRHP9QEW/Mk3lgIRbrkla/2sbm5hNDR+UMKnKEGyvieIKUGhBLNRUR6y6O2DEYAUK8nkh1UuDhvpDDsu2+fx4zAYNI6oSXr4nz+TrErAg3yykfFPub362Wb7NY8/XLrHS4BTlz3Qk0DJ2EQy4TLH4tojFk0IqyjQnTlm8uMtjwz4XnRNIG0LkhXQfxfzxEcunRlzRX9GYEV77xOXVPR5nz1jG7D3dtv9dEGiBLlSjURg3NqZuVsCcN9Ic/8GCPgUxtUUCnBMuH6J4Z0GOFdt99u134BINbofVLxDoegyVqUTlYEXNiBjbh4XjQ5x+2oyWbhcbCOlLFffcEGO78OC4iMrByoxo0kUOOhtDBeQESWkeujHm2ZqAqypblKM59IPDU1t99jc4rVWwNFNGxKyeFVI9tDXbT79brHzXZ9NnriHRSxvn6XIMFdgCo4YkPDMt5K6RMWJDlBfiBFwHHF+TD4S6nS6b93uIB49OCpl/U4iXBhUKQQSWBX5aoxS8fcBh3Yceh/+wSRLa2l+mWJOxYLmaJRMjZlZHoIVckyACIhAnEDUJ6d6a2pkBjaGgElg0xQx/rkmgEKu1eU6n4IGbQ1K+MHeDQxJjxFhAMQFPE0WwaGOKI79aLJ8aUFEOUR4SBa4Ntq8502jx5FaPt/Z6oOD4XxZrZgcMqVSoUAhjsC1wUxAHsGZHirU7feMTXvEYdD6GzeY0qx4es6ImpGZkApaGSNh40GHpVp+zpyyWzAjxbM2a7T5lfRWvzA5YeHNcGDdh71c2L3zgcuCwa8reu9QxbDkTmgW7QvPcnQGzqxNW1HvU73MZdLXi9bl5bh9pPHr3YYcFm3x+OWpz7x0hz88I2fK5y0s7POLzBb9waZ+8GwJFusCovUmwUpplNSGrakKclGkNgJvS/HnWYsV2j/UfucbIXEA6ON8/IICpxJiqmDcfDhh2ZXJB6VI4ZbWGtA84moYfbR7Z5PPFUcfsvHt0Y0Rt4Wp+ywoHv7cJ8oLlaRzbJNbaiBNHoyPh25MWJ7PmOC4FpVVAMHfnWBh/bcy6+wNGDU1ar2gCB7+zWb3dZ9dXBXfy6azn7VFiC1qggCbBKdesnBFSe1dAkkDdLp/aepc4axmll37VvUgCYHYcAVlh4tiIMBE+a3AgpcGjlF0XEeheo51BY5TdT/Px564hVNHB40vGxRNoi75tMv6D5PAfeTHpqRdTMPdWTvPvvJ5fbBMEyPwNHVM4PSt2deUAAAAASUVORK5CYII=', 'Granola': 'data:image/png;base64,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', 'Hootsuite': 'data:image/png;base64,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', 'Picsart': 'data:image/png;base64,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', 'VistaPrint': 'data:image/png;base64,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', 'Webflow': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAbFBMVEUUbvX///8AY/TO4f3c6v0AavUAZvVlmvjC2PwAYPQLbPUAXfTj7v7I2vyrxvszf/Zxo/hbk/fr9P+yy/uKsPmSt/ry+P9onfhBhfceePb4/P+z0PzX5/2oyftXkPeowfpIi/d/qvkAV/QAc/WHiV8fAAACqUlEQVR4nO2Y0YKiMAxFodhCQVFRUWFm0OX//3Gh6DpCUmnJ2+Y8WiGngV4KQcAwDMMwDMMwDMMwDMMwDI4SAK/h8YiyH/j70Jn162jK17/TiPHQ99NAnYADu0Olo4BYhQD6WeU4Htk83NItdFwYnhRaykcgnYwkDwG9AetXGq3kIvA8jThMhuphhvIHbsDO9QpYOwC1+TAIZGuw/jpzrW8VgNqcGwG5gxuwd26ATUDugZHGCOgKrL9xvgMQgcKcCGyzEVAnuAHblFIAbvOxF5guDsPBOYWsAnCbewFgcRg85m8RQNp8l2gGHV0zCBdYCbTN3UInyyCrANbmWMoYVSMUwNoc3qQgyyCbgI4wAXXHzAgFogxpc7fUM7oMsgj8gdvc0TaImNcaxAQ2SNT3AvDPuU8GWQRKVCCBf/adP/YwcsUvgwzqO5niKlX63oHGYLKvzbAMQDl7LkHE6OJa3zeDYAS0DbFzIWyAzJB1bsE7g6ak4oImEM7Vfw2+I0Vbu5dfkEFvpCq7+ZQPQ4riUunrqfAqvySDBpTQ1/vhc/UC/suiDDL183mxVyHPp3jpEpz5LKhS+Pm0PIPmCVTB5D19wHsb4CZQBhIeSJYvwTkCRaBzeKRdnkEzBCItr/AIRQZ9FsizFHsVUQQh/FFgpwOJPKAXZ9AMgXKr0M8hBclDwC5Qiy5n5BkeXJxBHwWqve4vMvI5ZEWzD7IINMpMcfqtcGB5BtkFoqsYKiDv6QQZZBP4uunHBLH3dIIMwgWSm37eYNh7OtE+CBIom1a87m8sgwTVRnAsUMf6d76B3wpDogyaCKzzrvr74sY+yVJdgJdAlJ+DcfWuAXe4ATQZZFB10hx/2kwoCVxVuY9ByC5Ab9CBz0fCENZnGIZhGIZhGIZhGIZhmP+Ev3VQITEIk1H+AAAAAElFTkSuQmCC', 'Wispr': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAY1BMVEUaGhr///8AAAAXFxcfHx/7+/vr6+sODg4SEhLKysoICAj39/enp6fv7+/c3NyZmZljY2NFRUVeXl5NTU02Njaurq7T09N2dnZZWVkoKCiNjY3AwMCCgoJpaWmgoKC1tbU9PT387BrXAAAB80lEQVR4nO2a7W6CMBSG4VRpKQJTQEEd2/1f5YbQqlhcqLYm833+nTQtT9KPcNoTBAAAAAAAAAAAwB9wImHbVxDxhz//scrXxGz6Mlq3q81jCrJIw1+yhYUBC7Kub1JI+++LMuxJaX5nSobOjfUUBhQPY4T5bAPKVd/Ywl4NosYIt/MFMt3ZWoAt9Bjz50DPQBjarKCxQDRfYAmBNxFgU4P7ESAqS5po8iDAqO3aKqOBDwHa9o3GU8qDAO1Vq+mg9iEQ3W31IKBbTac9BCAAAQhAAAIQcCTAifR9wa2A6Fq5SwEq4ig6lGQWoOIQRXFN7gRUxnskkwAd+6D/QXMhID9VWPBbAbFW0U46Ejhn3KeUfyRwvkzIyJWADpcmgeQ69C+wnAohAAEIQAACEIAABJwJ6H+w+DUColBhKV4iEFDdR/X4P9yXQCBle4hz2T8MehVQb1isy8WG4Sl1L6BXnemGnr5U63hNPk1ANEOUSMOQjKlPNqM1+cTcsD4lH2ljfJDmi9P1+fBY7CY75rSrqs+p93xBm6raDfm5qwsKebckgBOpt/J/8Wx3se+y+QJPeLy+2Hf7+QLt1a60Q3wPY1gVMKiDqbGeAb3vttymhIOfJiFaP1DC0RextPZFLHm+sa/B0QovLeMBAAAAAAAAAPAG/ADd5xuq3C5QuwAAAABJRU5ErkJggg==', 'Wix': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAJFBMVEUAAAD////////FxcV6enrr6+vX19cnJyeTk5NFRUWsrKxdXV05CmcmAAADQklEQVR4nO2Y3ZbdIAiFHeNPNO//vp0TUTcKmfRqulbxphlr5IMNSo77+t3hnQEYgAEYgAEYgAEYgAEYgAEYgAEYgAEYgAEYgAEYgAEYwDqTQgjVL5PxDOGMwmRI7fH7KXwejnCPtBmK7T+OFwDZfQ+2QyzuHoEhHJ+pEsfjvZO/2tJzcSG0abd6JgDEe4sMtrp95y6YTY3pfnYD4CvS0so2PWh2C4CUAw32mhPZjQGz5OlkoZ1OWorRShlW/whw4nZA75g0EVw68I0uQoBoX5oAIkBcTF0IEPpshS0ZwBBhultVAeQy5CJSBuQWxas7gXHiAJsII4cF+yJAYctJ4NSsZAoMBTpIAJ5SvsOS/SzZFwGaB4UcIMOxg5BXGYK6ACyVoFeABpCYr1QUngJZEYtwVoAh+seHhwpQAdA7KsKTB51MUJQ2gF4JHxGuJwFkAG5qRJOVJ8uTDQAqgYKR98NZB6CoN+YpPZnxgHVqAKMSankUQAGosOH0G48enpECQK8EGkWzLwPgUQTRAF8qMykADBEY6VsAMEW5f1uF1ECRZIBRCbcQqn0FYJrCipjnA09TGcDPI1yrAB1gFhmef1N4XqgywBQhr53MzwDzmMF6n2Z5DioAQwS1AnSAaQrrfQa+iTHaEwWg9zHX30dgmmI+tNQr63WlAMwsfAqB0hWflDxY+1B87d+R2yJAcnPoVagBdFO83mnP5WJUAAoAPIigAHjyvEeCBnleF4MSwOlw6CJoHyb0XuBi0824YEkA1C+43tCqImgALQsL6wHGUQSnowZAhq/+QVA0ETQAPEg3sUmfB4B5Ce8t6jsAzOFJj7Nww28AfV0FaEUEFQC/RkY7HyG1IbM3AFp2X8L+WQQNAK4SjB7c8tBkrwBUAf0O2F94AYBlVMVZwFoAegX093o+iSKoAJBv8eVs/3NUwIItiqACQEfz4ywH2NvQ/pYkgv4LychCVkAjNbDLYwC9Ao59gfRtogN0U7ydSBIWdS3tj7IDPlWCDnBI9md9pnVpbu7Jevuy5sVbgLoxp1MEyOwrLey/Jyki/IO/khmAARiAARiAARiAARiAARiAARiAARiAARiAARiAARjA/wfgf3n8ATnERXDyYfFdAAAAAElFTkSuQmCC', 'monday.com': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAArlBMVEX/////zAD7J10AynL/yQD7AEr//fH7AE37IVoAyW//5o/7AEj7DFIAxmT/+vz/+eH9nbP/5u3/7K7/9Pj8cZIAyGr/1kn7P2////j/3F78XID+t8f/4Hf+3eT8hqH+vcv/8Ln/0iDp+/Rb2Zz/1Df7NGf7T3j/88j/9thA1I71/vv8fZkAznyU5b3+1N7+ydb9k6r8aIv9prgr0oeB4bOj6cfe+Ox13ai27dLN9OGPKRn9AAAD90lEQVR4nO1Z2VbqQBDMhkkkcUHCIiB7FCEKqFf5/x+7A4bJ1t0jk3j1njP1wkufU0VXZ1I90TQFBQUFBQUFBQUFBQUFBQWF/wjP69BwvPlmey2qHPXHuq6Pu41OhfRbw/YcwzAcx6uFz0Rhp69bln6AZXUvK6IfzA/sMZxa8wKrbBzZYw3nlfD36in6PTzjBq7sZuj3ClqV8Bt5OA6ooMDPFMxK8w/sAj9TMAcqz4v8TEG3rADDAQQY3l2h8BLiZwruy/HfeRC/YdQKJsxAfoZS/IPiAMQtWOcqG3ADyrZgDhpwGINs4RnGr+v9EvxXiAEMdvZIbKH8ZTy4hp6AowfDdCVqwN4D+TO5jRrABPRShYQBTID0iUwYkBNAGSAvgDIgawFlQAkLQsIANoQDXtih6HXpIeyRDTC8pBJ4B6QheRjf1Eh+Z8krRzS/NZITcEsaYNT5MSAyQNIBgQFOk1cKDJBsgMAAw+Gh6J7m1yUjyYY2wE6eQUH/rTMp/qHAgA2v7AsMaEjxX9D/PxUGHr7HgKbAgOQU/hkDbnnlbzdAMhI3qZfgSQbIvQafBGdwyCvBHJ7il9yL4ByeNICfwUgO5xjL8WM5PIZ3xSvH32IAmsNjA9q88rcbIPkSrM6AByn+geAJSHZSOgbqluQ2gi9CB9R5DiRzuLwBZA7PrMRkDi8Y8Dh5/BI/ncPZePLKEwyYRC/+Hi/RH6EAahGSNGCy8APX3MMN/IVAQnUG8IU88j/ZP+H6r//GAL4ITH0zi2BBCKAXIaPGrwc7IgOOq9g0MPMgFFSfw9/y//+gAHPh6zlctAgdDXiE+E3TRyaxshyeGOCCAlzYBFEKSQwQvQSPBiANYC2YQAKWdAO85HZY8P95Dn8rTmA8BREkQBADEwMEm1iSwxEHEA/A+9jEgCSHiy5Dkhy+wgSYASBgSHYgfStKbwKpRQhzgA0BIKBHCbDT11HdrxmgadgMMgHAq5ESkDaAFpBZhE7rwDMhIHstTT2FmUXoBZ0BExBAnIPeNlNJDGF2E31Hn4IpIADPYqkcfgAeBXI5/AM9B94gAWgWsPOf6dDPAvlFCBMAzSDbiBEBqRweA3sXFRahCFYQvEP8mrYFj6K8AXgLgEXolAZoyL1gHfhOCk8BcBWwg44C/wPh1y6Apaz+BFWC1xLQXUxUVOCDb6JYQZibA8cG+ZmCQv/H8F1QNpMK+BnWdvoLrR0i30eZC610Eyx8D9uZ6UkMgh3Jz4Lx0vY8Zw+vFg6pyvuZ9fmZmP30qYuAyGSLgWu6bhDAQSCP4XrTbofLnvAr/VmjPxuPW+cjUeEuWqxWq8UrOn0KCgoKCgoKCgoKCgoKCgo/iL9r20j/KMrhTQAAAABJRU5ErkJggg==', 'Contacts': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAEGklEQVR4Ae2bA5AcXRSF+7dt22bpN8JCPIht21yjsqXYmulCbBbCmY2dFGLbejfvpmaNmVeZzO3ZnK/qrLdf1Tndj7ctxwIAAAAAAAAANe2HLHfgL8sVHKq1TGuX1vmQdoV+NpT/5s7fRglQe82z2tQEbe4pLRWhTvH/3PnfuwC4Am0sd/BEjrHG4v/laxgCaq56Qhs3jU2MivhafE0QAQ02PK+7jwAbF1XxNfnaYcBA6wosNjLWQHxtDNClUSuYZW6qobiNYgDewK/aoFv3PABug9sqBHAHVrBBMRG3lQ/gXvcvGxNTcZshgCswPOYBcJtAQ/SAHhgPxzwAbpPbxlZD8Bs2RETcNvr/YGWxALht9P/BJmIBcNtY/QZ7iAXAbd/X4AnAGIAAMAvCOgBgJYy9IIDdUJwHAJyI4UwYoCoCdUEAlXGoDQVlujoaAAAAAAAAMGQavZPgo3qJfspKsmleoo/2dhxz5VjFwUfV5x32qLeab1fPNdgc8Qr4yTqb1YuNtqs3m+9R33U5qioPuapc6VSiaqXTflcardOfZ7pTqYsrlT6yyjrJNr2b7Kc+ST7aoY1XrCE+paqmnFCvNtka9Z3QZxtsVb90P6FqpSk2PbzSaJs7jRoPGEAPli3jffRdok22NvymlspRvayz0TM+TBC/9znLJpsEEf/lK9r0V5L8ND7H8Hx3vTbkQMxLUj5vf4CfBpMgUvlpiNc+3qXNPl3Y/P6Tb6pP2+1hQ0T0RrM9qnrKTZMQ5tYcQE9b8cKIEfRIgo+Gs9mFlaD1WXsJ8wuF0HwPD8IRh1ArjeZQPNQTpU2kp7TRi7RUMSqt2xHpjthck+7I+ebbtKYE83nALWSCvEwGZhYPzI7tdrT5C0synwfdV5tudVwAPDsyGJRZWx05KOf0+SWI5/lhzBATrxNMn4LGTpztqFJkcPeLPAVsrIm2Wk6h/0R6NWeqWZI6j7lqYIiMKiVcNQqhThJ9bDmBnEVWaao45KjjA+C9I5MAPJnUWb7fn0Lfa4NvhQvgiw57HR/AW833GgVQM4NmWNKE9nZUOPGuptMD4F1UwzXBOtmBdwq9l7OxFk7P1t/k+ACeqLPJdCA+KNv329SbzY1ED7qzHR/AA+5s0wBuSM/7t0cYgIERsjIMQImeZLGxCECI0DEiApCCz3AlA0AANi2QDQBPwB7JADAG+Om4YACYhmpTrwgGgIUYmyoQALYiBALAZpxkANiOlg8ABzLyAeBIUj4AHMrLB4CyFPkAUJglHwBKE+UDQHGu+VbEw96oHkmiPD3RpnU55gpUReAFjQSbupoEUGHwkWiaiFeU+I5ItGlZpAFwZfSHrXcZmoaX9MKH4KcuWkGtq5GEwK+fvqm7owc92TcNTIz711QBAAAAAAAAAABwGzu2xPmLj8HiAAAAAElFTkSuQmCC', 'YouTube Music': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAATlBMVEVHcEz/ADP/ADP/ADP/ADP/ADP/ADP/ADP/ADP/ADP/////AC3/ACT/9vj/FEH/vsn/LFD/Q2T/mqn/5Or/0Nn/boP/hZP/rb3/fpL/WnW/2FXlAAAACnRSTlMAHrP/CTPrzFaN+kAlMwAABShJREFUeJzFW4nSoyAMtmq9QvFAq77/i66A7favBNCiyc7O7LaFfOQGQhTtpzS93YsyzvMsUZTleVwW91uaHphsL2/JemEMyTeBBKJgnMhdMt9w/iIpi3Mw+HDXJAURmnvqzV2rY8EQUgxpEWf+7DVlcTgIRb6bvYKQF4HYH+GuKQCE2w/sFYTbb+zL39hLKo9DSH+R/n/Kj1rjrTxke1vKjgkhzPI1HTHGUMtfEZS7+YdkL2kfgjQOzX/JUjtM8R5Q/f8p985Q5/D3R3AWf18E5/H3Q3Amfx8E6an8FwQuX9jlf7DSnjGxnb9n/AFgCyW8VcQT+T9PHGCNSF78AThvh1FUHyTGoeXcD4MFQeGO/wv3b+Z/QHhgyNDM5K5+AJqhM3JfMXRD44YQI9k5dSkAWPOs38weoq9X6sXj/XH9bJgDApRmV3ApAPhUr4we/dhNc9tw+Tlv2nnqxv71XT1xBwKzElwKYPOLfd9JZbO3/y3/YNI0uv4FYXYgMJaqdgUAdCv7cW4Sk56Xz5p5XCF0DksweMLNOoAl6+rqxmbowJvVSPpliI22IrApAGDWy+9dBrYoo9FQH7NVCPnGAm2z8knxF5NPpAGYlKM+7Lb4bYcWAUCj1V+3dqm+ibW1NoTGgiD3FsDK/9G5nOtjCF+H2BD8EYElCb8m8xL/exBMTtB/ErMlBumpxOAp/hexQWjY6C8+o5GlCmez5r8r50sCjWDGgX/U6bgAIFGi3M9fIlBDDQdqK32IAA+C0CtB7pS/JqaU1+PY3+EQr0Ohk/7UHVi/z+h3hYr6oA6Atb//fQ3ntQ6J2A9WHaB1gJ5AtAf5LxO0wrqAtS5ANaCVaDIAX0hssprQqgNMA6Ay29aIYOgaX6tURlyjAbGwa+ApBbAdzJ4PMbnKrtccjRTB06oDrBLSAqi3a2USmOB+EFhtE4EqT+/IUBgqowA0gKUyanxMQYmgQgPZ3WICXHrxyLdfrAAq8fQowYHLKq0zTKOowMOgdiGTD78ALAY6uEMEzDZXLvFMrDTQm5T3H0D1GAenKagSDdPBkpNTJBFp0Zm++QAg92POfQimSklZilXDwAWWBf8AWKT0tBfAKisKTFc3zAmglXMbVfcFYNkmzTYhQCt1gBnBHXMCNqCC+wagfmiBoJSJVFRQYE7ARjSTGgBU1RPfr6isPCJqKpEzGWACzSJGAJWYsXCncppAAMTYhoCpOf0lIBc5my0NZhlREAA5uiNBbRAFUImuNe5alRUibPLIHAaAV2gOQQHIjTvfrlRnNcQPs8gMTHlhbY4eFgBml1SFFeaHVgDm72wA5OnEtlo5ACA5DEBtyH4HcFwCgQAcl0AgFVxohFg2rq5yQ/JAZAYA14Vi5GjgumR0fjpm9nRMW5AsdTlxSVbQF6XkZfnZGxNwbUzO3polrq3ZyZvTxL05Jd+eUx5QqKsb9IiGXXREQ35IhR/TwUXHdOQHlSn1Ua3lsJpdc1hNflxPf2Fhady45sqG/NKK/tqO/OLS2j7Erri6pb+8DnR9nxy+vg/SwAC/NDCQt3DQN7GEauOpjrbxXNfIlCCNTJe1cuEN79TNbNe082W/NxT+1NDoarH2b+mUDNVf+cc/UzpaOumbWsnbeukbm6OUurWbvrmdvr2f/oFDRP7EIwr9yMUef80U8plPfOjNGfVDJ/qnXhH5YzcFgfa5nyTiB4+RMgXSJ58R/aNXSbue/Sahn/0qon34LCklfvqtQayP381qP/vx+xtFyOf//wCi/f6b/HpoRAAAAABJRU5ErkJggg==', 'AndroidDevSummit': 'data:image/png;base64,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', 'Fever': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAP1BMVEVHcEz///8CFCIABBcRIi4SIS4SIi4SIS4SIi4SIi4AAATt7u/Z29xETVW5vcAuN0CGi5CcoaVeZGpwdnx8gofwi2ikAAAACnRSTlMA////16X/MHHuspYALQAABMpJREFUeJztW+uSqyAMXqFSi9xE3/9ZTxAIiHZP29k1+8PMmTNdIOQjN4IDX19HdL/fh76/PR7iB+jxuPX9AFMeijqSPvS3nxDc0g1QvCL9V4QjiP9guPc/ovTv6NF/A2H4dfErhOHZ8n9V+TXdDpVwzvITHShhOFG8eOwRnCo/0EAsv3HF+5n2zwhqTzzN/2u6URpgpYHSAIHQCD2NfCF6WgWgCog8INBAFwKR1kC408kX4k5rgWgDshgI1J9ZBRwRVAakLhCcgBwAqQ8GLyT1weCF5ABIgyDkQrKdKNKDHgCtfCEuABeAC8AF4AJwAbgA/FEAjDNCAIxb7/RZCPYApDWq68xJ8ncAmDBdoNGepIIGANeqSwDOkd8AYLbrKAEwOxYAtQkYe9sgTzkgwvhTACbL7xRqgEnJ8/+RuATazs9CE9+y8HZQ5PVGmUq9NQA+4/qVZ3khelrdYjSzXSUw6yYgv9GQD00uTSP8tGpyhEENTuHWHld0UAOQyQE74/NquC1K6dQsi5rGamqmo+mmwAVLLCxGy3qFOnUdA+A+c2Ee5PPY1WSgg+8nkVNsmiRof9pwdL4M4zrP9gRAmlmJLF+6riEDIvyYhhXO1BsYTcuCwrjet20A2GSBBTl8O9m6yGypGcctWXOiXX8gnccpbDoEgCvLndmy4H/Omfwb/CqtRKF548yjZghZ1SzRE2XRzVh5cAGQY8DkefNqwJE4lyL/xQVPS0mpolIASz2TCCzZ5VbfLDlOTfVOVwFwW/Uwluddh6N3wTqzxATVtB1L7GDJq9acggowYrPX7wFACK4ZJP2tMCWm6YJY1PlqOrQIKyMigpRZwVswyZomO+0BqMkYA1KToieJ5JNJcWiM+7Q0kJKE6MIyZUSZZWwLjT2AOA4gp2VWFBvAg2T6CTjRJYsu9iwSY3yS4jUAFmNgR65Em4OZJ2wtqbwllsuMbldmPAXA/TMAoPiMbuT4i5Vw2JPmOcm0CvgEgAk7Haqg6OIbADO3aIzXABj+3ATB9XKvqbzhGxPoDEC9AMAJa20Yl6LA6obqvDZuck3yR99yALo3AMwy1j85i0DeyMRDV/QiVnaWDoMrGdpI5GCSR5Z3AORSIKfmsjnrKohZve2l1JPbZsxELLGwDwDgJjuxkLyglINqxuEEG4PnXSG1jU4G1AyOGKicDwDg1qoWMINd1KrrUviV3RWn5aWmAsB6rczW8uIjDWCBcGDtrQpwdy1bHoxE+/APNXBYkMTpooayiLo2OihI1grnIwBCHgR2KWawYKs4MOfXSvOfRUFE0GSjcal6k4lU1bQvSjsVylL2RiasAQi+9QOjN51R1rKdtMnhzr4aBQyO5UCmPfJoo+IxQ022PeqYPUM4/CwmnmVG5ViSyFyYXPl2cF0VQ8KCf7wdEb5XLMsya7H/bAL74p4Bmrn2i1u8rr60hIx4dGB86RsR45y/dzxlL7P80Y9UF4ALwAXgAnABuABcAM4EQH6JhRwA+UUm8qtc5ADIr/ORX2ikB0B9qZX8Wi/9xWbyq93kl9vpr/eTP3Agf+JB/8iF/JkP/UMnGiNsHh0SGIH6uR31g8OjJ5cn+sHxu1fqR6+nKeHps98v+ofPX+RPvxMGysfvCcN5z///ARSdaN9zCihLAAAAAElFTkSuQmCC', 'Shopify': 'data:image/png;base64,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', 'Xero': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAY1BMVEUTter///8As+ru+f0AselkzfEkuOvZ9Pz7/v+A0PFbxO7n9/3r+f04vezy+/625/hFxO7G6/mk4vd50/KD1PLN7/pZye+w4vfV8PuE2PNsyvCf3PW96/lr0fJ30PLe8/yS3PV9NtvVAAAE4ElEQVR4nO1b2bajKhBFgqhRFI1TkqPx/7+yoQCn2I3ddyXcB/ZTJEBta2AqQcGC+PJzDzlFHwTl4b3M45VQNP9KO44JxviT8hESAghqu/SNgBT/YdlrFnymoAk07dekaw5tsyZQtt8VL9GWC4GSf18+Qrw0BCIn8gWDSBHIxi/b3wCPGRDoiBv5CJFOEkgdGUCCp4JA5UwBwghdgGLmTr5QQYxSl/KREO/SAsINKzQ4ikEFPCDulgBHzC0Bhj66/rDDsXgPDw8PDw8PDw8PDw8PD48DYHR0ar8rlVkFfJBa0CXiz7emm7I/gD6S8e3MBIvSZC7FiIlHgSvbdApN5Q8+Jok5/MSYXhNVm57JR+A6D4JuxwDTOhOl5rF9lrnKcZTPx4rCKEorilEiEwGROn3ELCkilReIuoTZtUBeMnVUbBgI+VJgzFWP3WuV8Ek7bk75qDx8z69kUuxuWOoq0VwBeZlQGwPSB3sGGIH8IJZlmDfBFmlINE140yvXCam7MDqdLtvK+WRjgENVs1jOjvBNdVmB/CjYIxvJmkCvi4W66TPeV44rmwoMgx/jMWTQlKR8pt8/K+5De9dkUjhp1AQqJbMJpeaM2KaqZsUNtoNZohk0QADjWb5UqcrypDdI72Gi+bzYQkDq/DUgIlrrjvIBE4k2U8/Wg1E8xNoKMnRva5MoZ2iWgKQ/oNfnQkAIfCKlEWAXl8bqmCrtRBb5s5xAeCKtoU3cQVAxUEC08iOtk54vBOKaKN0Ns+UMtE/crCpAtXLegmv/VwMDfuRvKsQcIrTGMwFz+E5AAT0wN2OmeoPeqgEd+EHcZ0YVUD6BAcD8M0ghCztqCORz+gN6SJTgcVSOOl7Aae0MUL0KIC0fM5BVtOEarWLF5igwfXAoB1mPPsteA0SRDNLcagO0OJ92RkUAlJpftgBdRVdDYDQ9DHNb1S6WP3EJPntmTjDjgRgQTBl7H4QMFgJX08Ed9CGD56rqhKIjAm5YnsjR/CWBTsx0RwS6HQF8lsCxCcojE0g0V/ymgXB2n7UJinMmOHZC2h04ITgi9L0loJwwgsfFCSk4YW0dCEwYNumagQrDaBuGCuidwHEYyri+2AZjy0AU7pqbZdiOAIFRejMQ4bMD0W+GYsygz9dmtUL41B4S0F5cLIsgMz3fbRYYLZNRz8k8G+EpjdPpyAR6ogoKUxmjCTpOLWuS30zH1Wo6zitKpCeIKbaRffZHTijCT71I1OrpWEexJVF6bkESN9VtuBd6vdezQwJoNHG0XpBYMsX/sCQTCwByYAJ0uCQLGpsB/npRGqRPehiGsmjKt3XzzpanPLEsL9J1l3EZamOB0+VrAvtledDX1jwplgvJ441JYR4fXWN6vZT1UleaqtppeLUxyX6e/MT2jCbWrRmiXG3NkuSx3utApbc3WrZmJ/ZFps1BGdq0NkPbtuof97Uf/0rOw8PDw8PDw8PDw8PDw8Pj3+H843bnn/c7v+Dg/IqH80suzq/5xC6dAPMYBdaM+icJdP+Hy25B4e66XwH3DS8ncqkfAXwyI7NbLwdXXiVaeTavLr26GI91/kVd+y2+H4uYr679BkE0ftkTyajzCObqd/ZkX6RA2NN8YjRffo/TjpGzn5z9BwgRhHXpnM9abt8LDq+pZfSz1/8pa6fXOpv2C/DiOnhwZisWAAAAAElFTkSuQmCC', 'Google Ads': 'data:image/png;base64,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', 'Google Business Profile': 'data:image/jpeg;base64,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', 'Gmail': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAEkklEQVR4Ae2ZA5BkSRRFc23bv7H2Fta72V7btm3bDq3tsdkY27b9a9xmTr6IyXB0Z1W/6j8/+56IGzOB1jsdpzp+CQMAAAAAAAAAAAAAAACAEZ53xvDMoz8ekXXMqBGZxyyiDc88pnhExjHvj/S8E0Q7pW7gTtH64h0/ry/ZcVhDyQ6LaPT/+tIdX68ZtEu2aC2js484Uh+7l55qZvUjM4/+btBxhx8o2gnVg3b16kp2+k8fWzU3LeQ3NUjsK1JB/8ZfoI+7QU9ZLjHS84qE4+ij3qyPW66nLLesdsDOyVViZNaR2Toxq+iwyY6yNEiKHYVjqEFi14biHb6joyY7naRZapCwL8TW1qtUR68PYz3vUOEI1HN9yEl6KtVRsoQNw7I9aQ7ZSgmr9GtDnvPJsV+91QuzPl4nPcW1NXmRd5WUoUvSIil3XXvVGX/T8bhGfzHZCJjGKcDPi6lEXqzYl7HQJMmXZ2Xr73uSHh2Oc71sBFQzCzBbtbogts0nSX+fN/t58XL6nrkF0IuxjQCVJgG0+kRu9G2eJPEnJ5Ef/c58r9wCzIIWwJwk/uS4LoA1SfzJcV8Aa5L4k+O+AIYk8SYHAhiSxJAcCEh3knx58p768/9kvhYEtGGSVhdGT/FzY9Poc2/zAp58oMvYYVlZAQngT5LOzd0mOUEKqCzeRd3fRY4ULZH7YYW6+cVJS/qeenYAAtiSZJLzm/lcQQpYNGAfVdjh8uXR/69XVgJol7zrV/1+0W0sAhg2aJ08+8j0J4dfQL8+x6hzO1xbQ8dPSoDZezd+oShJAQugJdbkx4v4k8MvwCTnw+4RZQ6fsgDag48Xq/6nRBgEMCw39jEliS85/AIoObd2yqeD8wigXf36YvXnBTdzCGBYfBgliSE57AIoORd1uJqOzSuAlv/BRvXB9Z9RkngEMCSp2eQwrBXJ4Rdgdt+TgxT9lWQpINRrZXL4BZhd8dYyRX8luS/APjn8Aiz2zk3fUJJcFWCbnOAE0O55aiglyUUBFskJXIBJ0opGSpJjAmyTE7wAs7dv/qaRkuSUAPvkBC+AdssLkxOUJFcEUHKu71RYRQcMhQBawQcbN/4s75kfdgFde2cuOuf/66rpeKESYEZPM+mpZgiPX53Iiz5sDhdaAUJDz/Xp+X5ojp8fn+cXxM4QGicEEPQOF73TFQIB/9GDPUG4JICgp5j8SeJNjjC4KIDgTxJvctwXwJ8k1uS4L4A/SazJcV8AZ5IYkgMBDEliSA4EpD9J8XK9+4UBAtouSfR+Mb1vLAgIaPMk/WafHAjgSpJJzt3CAAGpk8iPSn3UZezJgQB7VsrIgfq4/ZJNDgQw4+fGX6YkWScHAvjx8yMXUJIYkgMBDEliTQ4E8AMBEAABEAABEAABEAABEAABEAABQQEBEDDLQkDlPAhIk4D/rv+rZQEflL8PAekREPv/httFS8h3NuyrD7eMUwAE0PGv7yVskR9tPiHvw4pJbAIgYFqs442HimSQ76gd9evB6zkfVg7T/5ZDQGqHj3S47nn52z27CgAAAAAAAAAAAAAAAAAAtFu2AJlqODQM4+yVAAAAAElFTkSuQmCC', 'Drive': 'data:image/png;base64,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', 'Docs': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAMAAADVRocKAAAAV1BMVEUAAABAgP9DhvVBhvRChfRChfQZZ9FAivRDhfQZZ9JBhvRDhfNChfT///9ChfRChfVChfRChPNDhPRAgO9ChfRChPRAhvJChfRChfVBhfVChfVDhfRAgP9O/W5MAAAAHXRSTlMABGO73/9vGM//v2vv/9fbo4NbEOOzKNN7w/NzCOs5sLwAAAC5SURBVHgB7dS3FUJBFAPRhc8avPf0Xycxkd4ZPGgK0M2U3CfW63eDHKgkVm051hAKoxwFmDDOcQAJXRxgwiQOMCHHASAAQAscQAIAtMABIhBACxgAAgO0AAEgQEALAAACALTAASZwQAkcEAIHmJDvzIABAwYeD0wDGfhSgGfAgL/IgL/IgL/oJgO/AYgMGDBgwIABA7yZBOb5rhYSWOa7Wklgvcl3tE26Xcu4fU2Beofjic2fL+kDc1fZmn1XbYcA1AAAAABJRU5ErkJggg=='}

# Connection broker contract (configure in Streamlit secrets, never in the UI):
# [connector_auth."Google Workspace"]
# start_url = "https://YOUR-BACKEND/connect/start"
# status_url = "https://YOUR-BACKEND/connect/status"
# disconnect_url = "https://YOUR-BACKEND/connect/disconnect"
# api_key = "SERVER-ONLY-SECRET"
# POST JSON: {app, session_id, attempt_id}. Start returns authorization_url.
# Status returns {app, session_id, attempt_id, connected: true, account: "..."}
# only after verified provider authorization. Disconnect returns connected:false.
# The broker must implement OAuth state/PKCE, provider tokens, authorization,
# revocation, and service API calls. Tokens must remain on the backend.


def connector_auth_config(name):
    try:
        return dict(st.secrets.get("connector_auth", {}).get(name, {}))
    except (FileNotFoundError, KeyError):
        return {}


def connector_https(url):
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(url)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except (TypeError, ValueError):
        return False


def connector_request(name, action):
    import secrets
    config = connector_auth_config(name)
    url = config.get(action + "_url", "")
    if not connector_https(url) or not config.get("api_key"):
        raise ValueError("Sign-in for this app has not been configured by the Chandlio owner.")
    session_id = st.session_state.setdefault("cu_auth_session", secrets.token_urlsafe(32))
    attempts = st.session_state.setdefault("cu_auth_attempts", {})
    if action == "start":
        attempts[name] = secrets.token_urlsafe(32)
    attempt_id = attempts.get(name)
    if not attempt_id:
        raise ValueError("Start a new connection before checking its status.")
    response = requests.post(url, json={"app": name, "session_id": session_id, "attempt_id": attempt_id},
                             headers={"Authorization": "Bearer " + config["api_key"]}, timeout=20, allow_redirects=False)
    if not 200 <= response.status_code < 300:
        raise ValueError("The connection service could not complete this request. Please try again.")
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("The connection service returned an invalid response.")
    if action == "start":
        if not connector_https(data.get("authorization_url", "")):
            raise ValueError("The connection service did not provide a valid sign-in link.")
    elif any(data.get(key) != value for key, value in {"app": name, "session_id": session_id, "attempt_id": attempt_id}.items()):
        raise ValueError("The connection response could not be verified. Please reconnect.")
    return data


def dismiss_connector_dialog():
    st.session_state.pop("cu_edit_connector", None)


def connector_logo(name, skill=False):
    if skill:
        return '<span class="cu-logo cu-skill-logo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 3h10l3 3v15H6z M9 8h6 M9 12h7 M9 16h5"/></svg></span>'
    if name == "Google Workspace":
        suite = [CUSTOMIZE_LOGOS.get(k) for k in ("Gmail", "Drive", "Docs")]
        if all(suite):
            return '<span class="cu-logo" style="position:relative"><img src="' + suite[0] + '" alt="Gmail" style="position:absolute;left:11px;top:0;width:24px;height:24px"><img src="' + suite[1] + '" alt="Drive" style="position:absolute;left:0;bottom:0;width:24px;height:24px"><img src="' + suite[2] + '" alt="Docs" style="position:absolute;right:0;bottom:0;width:24px;height:24px"></span>'
    if name == "Google Business Profile":
        return '<span class="cu-logo"><svg viewBox="0 0 48 48"><rect x="8" y="17" width="32" height="27" rx="3" fill="#4285f4"/><path d="M6 5h36l5 15H1z" fill="#7ba5f7"/><path d="M6 5h9l-2 15H1zM24 5h9l2 15H24z" fill="#4b79d4"/><path d="M1 20h12a6 6 0 0 1-12 0M24 20h11a5.5 5.5 0 0 1-11 0" fill="#3d68bd"/><path d="M13 20h11a5.5 5.5 0 0 1-11 0M35 20h12a6 6 0 0 1-12 0" fill="#90b4fa"/><text x="24" y="39" text-anchor="middle" font-family="Arial" font-weight="bold" font-size="16" fill="white">G</text></svg></span>'
    uri = CUSTOMIZE_LOGOS.get(name)
    if name == "Chandlio Notebook":
        return '<span class="cu-logo"><svg viewBox="0 0 48 48" fill="none"><path d="M7 38V22a17 17 0 0 1 34 0v16M14 38V22a10 10 0 0 1 20 0v16M21 38V22a3 3 0 0 1 6 0v16" stroke="#8ea4ff" stroke-width="5"/></svg></span>'
    if name == "Verify AI":
        return '<span class="cu-logo"><svg viewBox="0 0 48 48" fill="none" stroke="#ddd" stroke-width="3"><path d="M24 4L7 11v12c0 10 8 17 17 21 9-4 17-11 17-21V11z"/><path d="m15 24 6 6 12-13"/></svg></span>'
    if uri:
        return '<span class="cu-logo"><img src="' + uri + '" alt="' + _html.escape(name, quote=True) + ' logo"></span>'
    return '<span class="cu-logo cu-skill-logo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M8 3v5M16 3v5M6 8h12v5a6 6 0 0 1-12 0zM12 19v4"/></svg></span>'


@st.dialog("Connect an app", width="large", dismissible=True, on_dismiss=dismiss_connector_dialog)
def connector_connect_dialog(name):
    st.markdown("""<style>
    /* Center the native OUTER panel as well as its inner role=dialog.
       Newer Streamlit versions put the panel outside role=dialog. */
    [data-testid="stDialog"]:has(.st-key-cu_connect_modal) {
        position:fixed !important;inset:0 !important;display:flex !important;
        align-items:center !important;justify-content:center !important;
        padding:16px !important;box-sizing:border-box !important;
        overflow:hidden !important;background:rgba(0,0,0,.56) !important;
    }
    [data-testid="stDialog"]:has(.st-key-cu_connect_modal) > :has(.st-key-cu_connect_modal) {
        position:relative !important;flex:0 1 620px !important;
        width:min(620px,calc(100vw - 32px)) !important;
        min-width:0 !important;max-width:620px !important;
        height:auto !important;min-height:0 !important;
        max-height:calc(100dvh - 32px) !important;
        margin:0 auto !important;padding:0 !important;
        background:transparent !important;border:0 !important;
        border-radius:28px !important;box-shadow:0 18px 60px rgba(0,0,0,.45) !important;
        overflow:hidden !important;
    }
    [data-testid="stDialog"] [role="dialog"]:has(.st-key-cu_connect_modal) {
        position:relative !important;flex:0 1 auto !important;
        width:100% !important;min-width:0 !important;max-width:620px !important;
        height:auto !important;min-height:0 !important;max-height:calc(100dvh - 32px) !important;
        margin:0 !important;box-sizing:border-box !important;
        padding:24px !important;background:#202020 !important;border:1px solid #353535 !important;
        border-radius:28px !important;box-shadow:none !important;overflow-y:auto !important;
    }
    [data-testid="stDialog"] [data-testid="stDialogContent"]:has(.st-key-cu_connect_modal) {
        padding:0 !important;height:auto !important;min-height:0 !important;
        max-height:none !important;background:transparent !important;
    }
    [data-testid="stDialog"]:has(.st-key-cu_connect_modal) button[aria-label="Close"] {
        top:12px !important;right:12px !important;transform:none !important;
    }
    .st-key-cu_connect_modal .cu-connect-logos {display:flex;align-items:center;justify-content:center;gap:18px;margin:10px 0 22px;}
    .st-key-cu_connect_modal .cu-logo {width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;}
    .st-key-cu_connect_modal .cu-logo img,.st-key-cu_connect_modal .cu-logo svg {width:44px;height:44px;object-fit:contain;}
    .st-key-cu_connect_modal .cu-connect-title {font-size:1.7rem;line-height:1.25;font-weight:400;text-align:center;margin-bottom:24px;}
    .st-key-cu_connect_modal [data-testid="stButton"] button,
    .st-key-cu_connect_modal [data-testid="stLinkButton"] a {border-radius:24px !important;}
    </style>""", unsafe_allow_html=True)
    with st.container(key="cu_connect_modal"):
        safe = _html.escape(name)
        st.markdown('<div class="cu-connect-logos"><img src="' + STAR_URI + '" width="44" height="44" alt="Chandlio"><span style="color:#777">│</span>' + connector_logo(name) + '</div><div class="cu-connect-title">Connect ' + safe + ' to Chandlio?</div>', unsafe_allow_html=True)
        connected = st.session_state.get("cu_connected_apps", {}).get(name)
        if connected:
            st.success("Connected" + (" as " + connected["account"] if connected.get("account") else ""))
        st.markdown("**What this connection allows**")
        descriptions = {a[0]:a[1] for a in CUSTOMIZE_APPS}
        st.write(descriptions.get(name, "Use this service with Chandlio."))
        st.markdown("- Choose the account you want to use.\n- Review the exact permissions on the provider’s sign-in page.\n- Approve access before any account data is available.")
        st.markdown("**Things to know**")
        st.write("Your password is entered only on the provider’s website. Connecting an app does not change your subscription. You can disconnect it here or revoke access through the provider.")
        config = connector_auth_config(name)
        ready = all(connector_https(config.get(k, "")) for k in ("start_url", "status_url", "disconnect_url")) and bool(config.get("api_key"))
        if not ready:
            st.info("Sign-in for this app is not available yet. The Chandlio owner needs to enable its provider connection.")
        pending = st.session_state.setdefault("cu_pending_auth", {}).get(name)
        if pending and not connected:
            st.link_button("Continue to " + name, pending, type="primary", use_container_width=True)
            st.caption("Finish sign-in in the new tab, then return here to check the connection.")
            if st.button("Check connection", key="cu_check_auth"):
                try:
                    data = connector_request(name, "status")
                    if data.get("connected") is True:
                        st.session_state.setdefault("cu_connected_apps", {})[name] = {"account":str(data.get("account", ""))}
                        st.session_state["cu_pending_auth"].pop(name, None)
                        dismiss_connector_dialog()
                        st.rerun()
                    else:
                        st.info("Authorization is still pending. Complete the provider’s sign-in first.")
                except (requests.RequestException, ValueError, KeyError):
                    st.error("Unable to verify this connection. Please try again.")
        _, cancel, connect = st.columns([1, 1, 1])
        if cancel.button("Cancel" if not connected else "Close", key="cu_cancel_connect", use_container_width=True):
            dismiss_connector_dialog()
            st.rerun()
        if connected:
            if connect.button("Disconnect", key="cu_disconnect", disabled=not ready, use_container_width=True):
                try:
                    data = connector_request(name, "disconnect")
                    if data.get("connected") is not False:
                        raise ValueError("Disconnect was not confirmed.")
                    st.session_state["cu_connected_apps"].pop(name, None)
                    st.session_state.get("cu_pending_auth", {}).pop(name, None)
                    st.session_state.get("cu_auth_attempts", {}).pop(name, None)
                    dismiss_connector_dialog()
                    st.rerun()
                except (requests.RequestException, ValueError, KeyError):
                    st.error("Could not confirm disconnection. You can also revoke access through the provider.")
        elif connect.button("Connect" if not pending else "Restart", key="cu_begin_connect", type="primary", disabled=not ready, use_container_width=True):
            try:
                data = connector_request(name, "start")
                st.session_state["cu_pending_auth"][name] = data["authorization_url"]
                st.rerun(scope="fragment")
            except (requests.RequestException, ValueError, KeyError):
                st.error("Unable to start sign-in. Please try again.")



def render_customize_page():
    st.session_state.setdefault("customize_active_skills", [])
    st.session_state.setdefault("customize_user_skills", {})
    st.session_state.setdefault("cu_connected_apps", {})
    st.markdown("""<style>
    .st-key-customize_page {padding:8px 0 40px;}
    .st-key-customize_page .cu-title {font-size:2rem;font-weight:400;margin:42px 0 4px;line-height:1.2;}
    .st-key-customize_page .cu-sub {color:#999;font-size:1.05rem;margin-bottom:26px;}
    .st-key-customize_page .cu-category {color:#aaa;font-size:1.15rem;font-weight:500;margin:28px 0 16px;}
    .st-key-customize_page .cu-item {display:flex;align-items:center;gap:14px;min-height:76px;padding:10px 0;}
    .st-key-customize_page .cu-icon {display:flex;align-items:center;justify-content:center;width:44px;height:44px;flex:0 0 44px;border-radius:13px;color:white;font-size:20px;font-weight:600;}
    .st-key-customize_page .cu-copy {min-width:0;}
    .st-key-customize_page .cu-name {color:#e5e5e5;font-size:1.05rem;line-height:1.4;}
    .st-key-customize_page .cu-desc {color:#999;font-size:.9rem;line-height:1.45;}
    .st-key-customize_page [data-testid="stHorizontalBlock"] {align-items:center;}
    .st-key-customize_page [data-testid="stButton"] button {background:transparent;border:0;border-radius:24px;}
    .st-key-cu_tabs button {padding:8px 20px !important;border-radius:28px !important;}
    .st-key-cu_tabs button[kind="primary"] {background:#303030 !important;}

    .st-key-customize_page .cu-logo {width:40px;height:40px;flex:0 0 40px;display:inline-flex;align-items:center;justify-content:center;}
    .st-key-customize_page .cu-logo img,.st-key-customize_page .cu-logo svg {width:40px;height:40px;object-fit:contain;display:block;}
    .st-key-customize_page .cu-skill-logo {background:#242424;border-radius:50%;padding:10px;box-sizing:border-box;color:#ddd;}
    .st-key-customize_page .cu-skill-logo svg {width:22px;height:22px;}
    .st-key-customize_page [class*="st-key-cu_action_"] {width:36px !important;min-width:36px !important;margin-left:auto;}
    .st-key-customize_page [class*="st-key-cu_action_"] button {
        width:36px !important;height:36px !important;min-height:36px !important;
        padding:0 !important;border:0 !important;display:flex !important;align-items:center !important;
        justify-content:center !important;background:transparent !important;box-shadow:none !important;
    }
    .st-key-customize_page [class*="st-key-cu_action_"] button p {
        font:400 26px/1 Arial,sans-serif !important;margin:0 !important;padding:0 !important;
    }
    .st-key-customize_page [class*="st-key-cu_action_"] button:hover {background:#303030 !important;}
    .st-key-customize_page [class*="st-key-cu_card_installed_"] {
        background:#242424;border:1px solid #555;border-radius:22px;padding:6px 14px;
    }
    .st-key-customize_page [class*="st-key-cu_card_installed_"]:focus-within {outline:2px solid #a8c7fa;outline-offset:2px;}
    </style>""", unsafe_allow_html=True)
    skills = dict(CUSTOMIZE_SKILLS)
    skills.update(st.session_state["customize_user_skills"])
    with st.container(key="customize_page"):
        with st.container(key="cu_tabs"):
            tab = st.segmented_control("Customize sections", ["Discover", "Connectors", "Skills"], default="Discover", key="cu_tab", label_visibility="collapsed") or "Discover"
        titles = {"Discover": ("Customise Chandlio", "Add apps and skills to make Chandlio work better for you."), "Connectors": ("Connected apps", "Connect your tools to get more done."), "Skills": ("Skills", "Add or create skills to extend what Chandlio can do.")}
        title, subtitle = titles[tab]
        st.markdown(f"<div class='cu-title'>{title}</div><div class='cu-sub'>{subtitle}</div>", unsafe_allow_html=True)
        h1, h2 = st.columns([3, 1])
        with h1:
            query = st.text_input("Search " + tab.lower(), placeholder="Search", key="cu_search_" + tab, label_visibility="collapsed").strip().casefold()
        with h2:
            if tab == "Connectors":
                if st.button("＋ Custom", key="cu_custom"):
                    st.session_state["cu_edit_connector"] = "Custom connector"
            elif tab == "Skills":
                if st.button("Create", key="cu_create"):
                    st.session_state["cu_create_skill"] = True
        if tab == "Skills":
            st.caption("Added skills guide new chat replies. Selections and custom skills are kept for this session.")
        if tab == "Skills" and st.session_state.get("cu_create_skill"):
            with st.form("cu_skill_form"):
                name = st.text_input("Skill name", max_chars=80)
                description = st.text_input("Description", max_chars=240)
                instructions = st.text_area("Instructions", help="Describe how Chandlio should respond when this skill applies.")
                save, cancel = st.columns(2)
                submitted = save.form_submit_button("Save skill")
                cancelled = cancel.form_submit_button("Cancel")
                if submitted:
                    if not name.strip() or not instructions.strip():
                        st.error("Enter a skill name and instructions.")
                    elif name.strip() in skills:
                        st.error("A skill with this name already exists.")
                    else:
                        st.session_state["customize_user_skills"][name.strip()] = (description.strip(), instructions.strip())
                        st.session_state["customize_active_skills"].append(name.strip())
                        st.session_state["cu_create_skill"] = False
                        st.rerun()
                if cancelled:
                    st.session_state["cu_create_skill"] = False
                    st.rerun()
        def show_items(items, group):
            if not items:
                return
            for offset in range(0, len(items), 2):
                cols = st.columns(2, gap="large")
                for col, item in zip(cols, items[offset:offset + 2]):
                    name, description, kind, mark, color = item
                    with col, st.container(key="cu_card_" + group + "_" + name):
                        text_col, action_col = st.columns([7, 1], vertical_alignment="center")
                        added = name in st.session_state["customize_active_skills"]
                        with text_col:
                            esc = _html.escape
                            st.markdown(f"<div class='cu-item'>{connector_logo(name, kind == 'skill')}<div class='cu-copy'><div class='cu-name'>{esc(name)}</div><div class='cu-desc'>{esc(description)}</div></div></div>", unsafe_allow_html=True)
                        with action_col, st.container(key="cu_action_" + group + "_" + name):
                            installed = name in st.session_state["cu_connected_apps"]
                            label = "✓" if kind == "skill" and added else ("⋯" if installed and kind != "skill" else "+")
                            if st.button(label, key=f"cu_item_{group}_{name}", help=("Remove skill" if added else "Add skill") if kind == "skill" else ("Manage connection" if installed else "Connect " + name), use_container_width=True):
                                if kind == "skill":
                                    if added:
                                        st.session_state["customize_active_skills"].remove(name)
                                    else:
                                        st.session_state["customize_active_skills"].append(name)
                                else:
                                    st.session_state["cu_edit_connector"] = name
                                st.rerun()

        def matches(item):
            return not query or query in (item[0] + " " + item[1]).casefold()

        skill_items = [(name, value[0], "skill", "≡", "#292929") for name, value in skills.items()]
        if tab == "Discover":
            for category in ["Everyday tools", "Business essentials", "Creative expressions", "Media streaming", "Dining and entertainment"]:
                items = [a for a in CUSTOMIZE_APPS if a[2] == category]
                if category == "Everyday tools":
                    items += [s for s in skill_items if s[0] in ("Focus your energy", "Generate fresh ideas", "Get more perspectives")]
                if category == "Business essentials":
                    items = [s for s in skill_items if s[0] in ("Generate fresh ideas", "Get more perspectives", "Prep for meetings")] + items
                items = [i for i in items if matches(i)]
                if items:
                    st.markdown(f"<div class='cu-category'>{category}</div>", unsafe_allow_html=True)
                    show_items(items, category)
            if not any(matches(a) for a in CUSTOMIZE_APPS + skill_items):
                st.info("No matching apps or skills.")
        elif tab == "Connectors":
            installed = [a for a in CUSTOMIZE_APPS if matches(a) and a[0] in st.session_state["cu_connected_apps"]]
            if installed:
                st.markdown("<div class='cu-category'>Installed</div>", unsafe_allow_html=True)
                show_items(installed, "installed")
            st.markdown("<div class='cu-category'>All</div>", unsafe_allow_html=True)
            items = [a for a in CUSTOMIZE_APPS if matches(a) and a[0] not in st.session_state["cu_connected_apps"]]
            show_items(items, "all")
            if not items and not installed:
                st.info("No matching connectors.")
        else:
            st.markdown("<div class='cu-category'>Recommended</div>", unsafe_allow_html=True)
            items = [i for i in skill_items if matches(i) and i[0] in CUSTOMIZE_SKILLS]
            show_items(items, "recommended")
            custom = [i for i in skill_items if matches(i) and i[0] not in CUSTOMIZE_SKILLS]
            if custom:
                st.markdown("<div class='cu-category'>Your skills</div>", unsafe_allow_html=True)
                show_items(custom, "custom")
            if not items and not custom:
                st.info("No matching skills.")


    editing = st.session_state.get("cu_edit_connector")
    if editing and not st.session_state.get("settings_open"):
        connector_connect_dialog(editing)


# ---------------- SETTINGS DIALOG (account menu entry; full Claude-style layout) ----------------
def dismiss_settings():
    st.session_state["settings_open"] = False
    st.session_state["open_settings"] = False


@st.dialog("Settings", width="large", dismissible=True, on_dismiss=dismiss_settings)
def settings_dialog():
    sections = ["Account", "Billing", "Appearance", "Your Chandlio", "Capabilities",
                "Notifications", "Privacy", "Wellbeing", "Customize", "Code"]
    st.markdown("""
    <style>
    /* Large, centered settings surface matching the supplied reference */
    /* Use ONE native Streamlit dialog frame: no nested window or duplicate close control. */
    [data-testid="stDialog"] { align-items:center !important; justify-content:center !important; background:rgba(0,0,0,.54) !important; }
    /* Streamlit adds an inner content wrapper; keep it transparent so it cannot look like a second black window. */
    [data-testid="stDialog"] div:has(.st-key-settings_shell):not([role="dialog"]) {
        background:transparent !important; border:0 !important; outline:0 !important; box-shadow:none !important;
    }
    [data-testid="stDialog"] [role="dialog"] {
        width:min(1024px, calc(100vw - 48px)) !important;
        max-width:min(1024px, calc(100vw - 48px)) !important;
        position:relative !important;
        min-width:0 !important; height:min(82vh, 820px) !important;
        max-height:min(82vh, 820px) !important; margin:auto !important;
        padding:0 !important; overflow:hidden !important; background:#1f1f1f !important;
        border:1px solid #303030 !important; border-radius:14px !important;
        box-shadow:0 18px 60px rgba(0,0,0,.55) !important;
    }
    /* Keep the native title and close button inside the settings frame. */
    [data-testid="stDialog"] [role="dialog"]:has(.st-key-settings_shell) h2 {
        display:block !important; margin:0 !important; padding:14px 60px 14px 16px !important;
        min-height:48px !important; box-sizing:border-box !important;
        border-bottom:1px solid #343434 !important;
        font-size:1rem !important; font-weight:600 !important; line-height:20px !important;
    }
    [data-testid="stDialog"]:has(.st-key-settings_shell) button[aria-label="Close"],
    [data-testid="stDialog"]:has(.st-key-settings_shell) button[aria-label="Close dialog"],
    [data-testid="stDialog"]:has(.st-key-settings_shell) button[data-baseweb="modal-close"] {
        position:absolute !important; top:8px !important; right:12px !important;
        left:auto !important; bottom:auto !important; margin:0 !important;
        width:32px !important; height:32px !important; min-height:32px !important;
        padding:6px !important; transform:none !important; z-index:10 !important;
        color:#eee !important; background:transparent !important; border:0 !important;
    }
    /* Natural text metrics; leave the dedicated icon font intact. */
    [data-testid="stDialog"] [role="dialog"]:has(.st-key-settings_shell) {
        font-family:"Segoe UI", Arial, sans-serif !important;
        font-weight:400; line-height:1.5; letter-spacing:normal;
        -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
    }
    .st-key-settings_shell p, .st-key-settings_shell input,
    .st-key-settings_shell textarea, .st-key-settings_shell label {
        font-family:inherit !important; letter-spacing:normal !important;
        line-height:1.5 !important;
    }
    /* Set the classic UI font on the dialog itself and let child icon widgets
       retain Streamlit's dedicated Material Symbols font. */
    [data-testid="stDialog"] [role="dialog"] { font-family: var(--ui-font) !important; }
    [data-testid="stDialog"] [role="dialog"] :not(span[data-testid="stIconMaterial"]) { font-family: inherit; }
    [data-testid="stDialog"] span[data-testid="stIconMaterial"],
    [data-testid="stDialog"] .material-symbols-rounded,
    [data-testid="stDialog"] .material-symbols-outlined {
        font-family: "Material Symbols Rounded" !important;
        font-weight: normal !important;
        font-style: normal !important;
        font-size: 20px !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-smoothing: antialiased !important;
        font-feature-settings: "liga" !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex: 0 0 20px !important;
    }
    .st-key-settings_nav button [data-testid="stIconMaterial"] { margin-right: 10px !important; }
    .st-key-settings_nav button [data-testid="stMarkdownContainer"] p { margin: 0 !important; }
    [data-testid="stDialog"] [data-testid="stDialogHeader"] {
        display:flex !important; align-items:center !important; min-height:48px !important;
        padding:8px 18px !important; background:#1f1f1f !important;
        border-bottom:1px solid #343434 !important; color:#f1f1f1 !important;
    }
    [data-testid="stDialog"] [data-testid="stDialogHeader"] button {
        color:#eee !important; background:transparent !important; border:0 !important;
    }
    [data-testid="stDialog"] [data-testid="stDialogContent"] {
        padding:0 !important; height:calc(100% - 48px) !important;
        max-height:calc(82vh - 48px) !important; overflow:hidden !important;
    }
    [data-testid="stDialog"] [data-testid="stVerticalBlock"] {gap:.35rem !important;}
    .st-key-settings_shell {height:100%; padding:0 !important; gap:0 !important; background:#1f1f1f !important;}
    .st-key-settings_body {height:100%; padding:0 !important; gap:0 !important; background:#1f1f1f !important;}
    .st-key-settings_nav {height:100%; overflow-y:auto !important; padding:16px 14px 20px 16px !important;
        border-right:1px solid #343434 !important; background:#191919 !important;}
    .st-key-settings_nav [data-testid="stTextInput"] {margin-bottom:12px !important;}
    .st-key-settings_nav input {background:#292929 !important;border:1px solid #414141 !important;border-radius:11px !important;
        min-height:2.55rem !important;color:#eee !important;}
    .st-key-settings_nav button {width:100% !important;display:flex !important;justify-content:flex-start !important;
        text-align:left !important;background:transparent !important;border:0 !important;color:#e1e1e1 !important;
        border-radius:10px !important;min-height:2.65rem !important;padding:.45rem .8rem !important;font-size:1rem !important;}
    .st-key-settings_nav button p {text-align:left !important; margin:0 !important;}
    .st-key-settings_nav button > div {justify-content:flex-start !important; width:100% !important; align-items:center !important; gap:10px !important;}
    .st-key-settings_nav [data-testid="stMarkdownContainer"] {text-align:left !important;}
    .st-key-settings_nav [data-testid="stDivider"] {margin:10px 0 !important;}
    .st-key-settings_nav button:hover {background:#303030 !important;}
    .st-key-settings_nav [data-testid="stBaseButton-primary"] {background:#3b3b3b !important;color:#fff !important;}
    .st-key-settings_content {height:100%; overflow-y:auto !important; padding:18px 24px 30px 18px !important; background:#1f1f1f !important;}
    .st-key-settings_content h3 {font-size:1.35rem !important;font-weight:600 !important;margin:0 0 22px !important;color:#f2f2f2 !important;}
    .st-key-settings_content h4 {font-size:1.05rem !important;margin:20px 0 12px !important;}
    .st-key-settings_content [data-testid="stDivider"] {margin:0 !important;}
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
    .settings-profile {display:flex;align-items:center;justify-content:space-between;gap:18px;padding:12px 0 18px;border-bottom:1px solid #343434;margin-bottom:0;}
    .settings-avatar {width:58px;height:58px;border-radius:50%;background:#383838;display:flex;align-items:center;justify-content:center;
        font-size:23px;color:#eee;flex-shrink:0;}
    @media(max-width:760px){
      [data-testid="stDialog"] [role="dialog"]{width:calc(100vw - 20px) !important;max-width:calc(100vw - 20px) !important;height:90vh !important;max-height:90vh !important;}
      .st-key-settings_nav{padding:12px 8px !important;}
      .st-key-settings_content{padding:14px 10px !important;}
      .settings-row{grid-template-columns:1fr;gap:8px;}
    }
    /* Give both panes a definite scroll height, independent of wrapper heights. */
    [data-testid="stDialog"]:has(.st-key-settings_shell) {
        --settings-pane-height:calc(min(82vh, 820px) - 80px);
    }
    .st-key-settings_shell, .st-key-settings_body {
        height:auto !important; min-height:0 !important;
    }
    .st-key-settings_body > [data-testid="stHorizontalBlock"] {
        align-items:flex-start !important; gap:0 !important;
    }
    .st-key-settings_body > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-height:0 !important; min-width:0 !important;
    }
    .st-key-settings_nav, .st-key-settings_content {
        height:var(--settings-pane-height) !important;
        max-height:var(--settings-pane-height) !important;
        min-height:0 !important; box-sizing:border-box !important;
        overflow-y:scroll !important; overflow-x:hidden !important;
        scrollbar-width:auto; scrollbar-color:#666 #1f1f1f;
        scrollbar-gutter:stable; overscroll-behavior:contain;
    }
    .st-key-settings_nav::-webkit-scrollbar,
    .st-key-settings_content::-webkit-scrollbar {width:9px;}
    .st-key-settings_nav::-webkit-scrollbar-thumb,
    .st-key-settings_content::-webkit-scrollbar-thumb {background:#666;border-radius:8px;}
    .st-key-settings_nav [data-testid="stVerticalBlock"],
    .st-key-settings_content [data-testid="stVerticalBlock"] {
        min-height:0 !important; height:auto !important;
        justify-content:flex-start !important; gap:8px !important;
    }
    .st-key-settings_nav button {min-height:36px !important; padding:6px 10px !important;}
    .st-key-settings_nav button p {white-space:normal !important; overflow:visible !important;}
    .st-key-settings_nav [data-testid="stDivider"] {margin:6px 0 !important;}
    .st-key-settings_nav [data-testid="stDivider"] hr {margin:6px 0 !important;}
    .st-key-settings_content h3 {font-size:1.1rem !important; margin:0 0 14px !important;}
    .st-key-settings_content > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        min-height:52px !important; align-items:center !important;
    }
    .st-key-settings_content [data-testid="stDivider"] hr {margin:4px 0 !important;}
    @media(max-width:760px) {
        [data-testid="stDialog"]:has(.st-key-settings_shell) {
            --settings-pane-height:calc(90vh - 80px);
        }
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="settings_shell"):
        with st.container(key="settings_body"):
            nav_col, content_col = st.columns([0.92, 3.08], gap="small")
            with nav_col:
                with st.container(key="settings_nav", height=600, border=False):
                    st.text_input("Search", key="settings_search", placeholder="Search", label_visibility="collapsed")
                    q = st.session_state.get("settings_search", "").strip().lower()
                    shown = [x for x in sections if not q or q in x.lower()]
                    for section in shown:
                        icons = {"Account":":material/person_outline:","Billing":":material/credit_card:","Appearance":":material/palette:",
                                 "Your Chandlio":":material/psychology:","Capabilities":":material/work:","Notifications":":material/notifications:",
                                 "Privacy":":material/shield:","Wellbeing":":material/favorite_border:","Customize":":material/tune:","Code":":material/code:"}
                        if section in ("Appearance", "Customize"):
                            st.divider()
                        if st.button(section, key="settings_section_" + section,
                                     icon=icons[section],
                                     type="primary" if st.session_state.get("settings_section") == section else "secondary",
                                     use_container_width=True):
                            st.session_state["settings_section"] = section
            with content_col:
                with st.container(key="settings_content", height=600, border=False):
                    section = st.session_state.get("settings_section", "Account")
                    st.subheader("Profile" if section == "Account" else section)
                    if section == "Account":
                        st.markdown("<div class='settings-profile'><div><div class='settings-row-title'>Profile photo</div><div class='settings-row-note'>PNG, JPEG, or WebP, up to 10MB.</div></div><div class='settings-avatar'>C</div></div>", unsafe_allow_html=True)
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

    st.button("Library", icon=":material/folder_open:", use_container_width=True, key="nav_library",
              on_click=go_page, args=("library",), type="primary" if _page == "library" else "secondary")

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
              on_click=go_page, args=("customize",), type="primary" if _page == "customize" else "secondary")

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

if st.session_state["page"] == "library":
    library_import_session()
    render_library_page()
    st.stop()

if st.session_state["page"] == "customize":
    render_customize_page()
    st.stop()

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
            for photo_bytes in found_images:
                if isinstance(photo_bytes, bytes):
                    library_save_photo(photo_bytes)

            # Keep the latest code answer for the Artifacts button, but do NOT split the screen automatically
            if "```" in answer:
                st.session_state["workspace_content"] = answer
                _t = prompt.strip().replace("\n", " ")
                st.session_state["artifact_items"].append(
                    {"title": (_t[:40] + "…") if len(_t) > 40 else (_t or "Artifact"), "content": answer})
                library_auto_save(st.session_state["artifact_items"][-1]["title"] + ".md", "text/markdown", answer.encode(), "Artifact")

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
