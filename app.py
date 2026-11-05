"""Chandlio's AI Bot v3 - an agentic assistant in one file.

Skills: streaming chat, web search, page reading, photo search, weather,
calculator, file reading (PDF/DOCX/text), live HTML/SVG previews, custom
instructions, multi-chat history with export/import.

Run locally:  streamlit run app.py
Deploy:       push app.py + requirements.txt to GitHub -> Streamlit Cloud.
Optional:     add GROQ_API_KEY to the app's Secrets so visitors don't need a key.
"""
import ast
import io
import ipaddress
import json
import math
import operator
import re
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Chandlio's AI Bot", page_icon="⚡", layout="wide")

MODELS = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
MAX_HISTORY = 16          # last N chat messages sent to the model
MAX_TOKENS = 4096
MAX_TOOL_STEPS = 4        # tool rounds per reply
MAX_FILE_CHARS = 12000    # per uploaded file
MAX_TOTAL_FILE_CHARS = 24000
UA = {"User-Agent": "ChandlioAIBot/3.0 (streamlit app)"}

SYSTEM_PROMPT = """You are Chandlio's AI Bot: a capable, direct and honest assistant.

How to work:
- Think step by step on hard problems, but keep answers concise and well organised. Use markdown.
- Put code in fenced code blocks with the language name. When asked to build a web page, app, game or
  visual, write ONE complete self-contained ```html block (inline CSS and JS) so it can be previewed live.
- You have tools. Use web_search for anything recent, factual or that you are unsure about, and cite the
  source URLs you used. Use fetch_url to read a page in full. Use image_search when the user wants photos
  or pictures (the images are shown to the user automatically, so do not paste links). Use weather for
  forecasts and calculator for exact maths.
- Never invent URLs, image links, quotes or statistics. If you do not know, say so or search.
- You cannot run code, generate images or see images. Say so if asked.
- If the user attached files, their text is provided below. Answer from them and mention when something
  is not in them."""

st.markdown(
    """
<style>
.stApp { background-color: #191919; color: #ffffff; }
[data-testid="stSidebar"] { background-color: #1e1e1e; border-right: 1px solid #2a2a2a; }
[data-testid="stChatMessage"] { border-radius: 12px; border: 1px solid #2a2a2a; }
.stTextInput input, .stTextArea textarea { background-color: #252525 !important; color: #ffffff !important; }
h1, h2, h3 { color: #ffffff !important; }
.hero { text-align: center; margin-top: 10vh; }
.hero p { color: #a1a1aa; }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------------
def _schema(name, desc, props, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


TOOL_SCHEMAS = [
    _schema("web_search", "Search the web for current information, news, facts, or anything you are unsure about.",
            {"query": {"type": "string", "description": "Short search query"}}, ["query"]),
    _schema("fetch_url", "Download and read the text of a web page. Use after web_search to read a result in full.",
            {"url": {"type": "string", "description": "Full http(s) URL"}}, ["url"]),
    _schema("image_search", "Find real photos on Wikimedia Commons. They are displayed to the user automatically.",
            {"query": {"type": "string", "description": "What to find photos of"},
             "count": {"type": "integer", "description": "How many photos, 1-12 (default 6)"}}, ["query"]),
    _schema("weather", "Get the current weather and 3-day forecast for a city.",
            {"location": {"type": "string", "description": "City name, e.g. 'Riyadh'"}}, ["location"]),
    _schema("calculator", "Evaluate a maths expression exactly. Supports + - * / ** % //, sqrt, sin, cos, tan, log, pi, e.",
            {"expression": {"type": "string", "description": "e.g. '(12.5*8)/3 + sqrt(49)'"}}, ["expression"]),
]

TOOL_LABELS = {
    "web_search": "Searching the web",
    "fetch_url": "Reading page",
    "image_search": "Finding photos",
    "weather": "Checking weather",
    "calculator": "Calculating",
}

# --- calculator (safe: no eval) ---
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_FUNCS = {n: getattr(math, n) for n in
          ("sqrt", "sin", "cos", "tan", "log", "log10", "exp", "floor", "ceil", "fabs", "radians", "degrees", "factorial")}
_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max})
_CONSTS = {"pi": math.pi, "e": math.e}


def _calc(node):
    if isinstance(node, ast.Expression):
        return _calc(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _calc(node.left), _calc(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS and not node.keywords):
        args = [_calc(a) for a in node.args]
        if node.func.id == "factorial" and (not args or args[0] > 500):
            raise ValueError("factorial too large")
        return _FUNCS[node.func.id](*args)
    raise ValueError("unsupported expression")


def tool_calculator(expression):
    return str(_calc(ast.parse(expression.strip(), mode="eval")))


# --- web ---
def is_safe_url(url):
    """Block localhost / private network targets (SSRF protection)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except Exception:
        return False
    return True


def tool_web_search(query):
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    results = list(DDGS().text(query, max_results=6))
    if not results:
        return "No results found."
    return "\n\n".join(
        f"{i}. {r.get('title', '')}\n{r.get('href', '')}\n{(r.get('body') or '')[:300]}"
        for i, r in enumerate(results, 1)
    )


def tool_fetch_url(url):
    import requests
    from bs4 import BeautifulSoup

    for _ in range(4):  # follow a few redirects manually, re-checking each hop
        if not is_safe_url(url):
            return "Blocked: that URL is not allowed."
        r = requests.get(url, headers=UA, timeout=15, allow_redirects=False)
        if r.is_redirect and r.headers.get("location"):
            url = requests.compat.urljoin(url, r.headers["location"])
            continue
        break
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        t.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    return text[:6000] or "The page had no readable text."


def tool_weather(location):
    import requests

    g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": location, "count": 1}, headers=UA, timeout=15).json()
    if not g.get("results"):
        return f"Couldn't find a place called '{location}'."
    place = g["results"][0]
    w = requests.get("https://api.open-meteo.com/v1/forecast", headers=UA, timeout=15, params={
        "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto", "forecast_days": 3,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    }).json()
    c, d = w["current"], w["daily"]
    lines = [f"Weather for {place['name']}, {place.get('country', '')}:",
             f"Now: {c['temperature_2m']}°C, humidity {c['relative_humidity_2m']}%, "
             f"wind {c['wind_speed_10m']} km/h, precipitation {c['precipitation']} mm"]
    for i, day in enumerate(d["time"]):
        lines.append(f"{day}: {d['temperature_2m_min'][i]}°C to {d['temperature_2m_max'][i]}°C, "
                     f"rain chance {d['precipitation_probability_max'][i]}%")
    return "\n".join(lines)


@st.cache_data(ttl=3600, show_spinner=False)
def search_images(query, count):
    import requests

    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=15, params={
        "action": "query", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": count, "prop": "imageinfo", "iiprop": "url",
        "iiurlwidth": 800, "format": "json",
    })
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}
    out = []
    for p in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        info = (p.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if url:
            title = re.sub(r"^File:|\.\w{3,4}$", "", p.get("title", "")).replace("_", " ")
            out.append({"url": url, "title": title, "page": info.get("descriptionurl", "")})
    return out


def run_tool(name, args):
    """Return (text_for_model, images_for_user)."""
    try:
        if name == "web_search":
            return tool_web_search(args["query"]), []
        if name == "fetch_url":
            return tool_fetch_url(args["url"]), []
        if name == "weather":
            return tool_weather(args["location"]), []
        if name == "calculator":
            return tool_calculator(args["expression"]), []
        if name == "image_search":
            count = min(max(int(args.get("count", 6) or 6), 1), 12)
            found = search_images(args["query"], count)
            if not found:
                return "No photos found for that search.", []
            titles = "; ".join(f["title"][:50] for f in found)
            return f"Found {len(found)} photos (shown to the user automatically): {titles}", found
        return f"Unknown tool: {name}", []
    except Exception as e:
        return f"Tool error: {e}", []


# ----------------------------------------------------------------------------
# Files, rendering, helpers
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=50)
def extract_text(name, data):
    lower = name.lower()
    try:
        if lower.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if lower.endswith(".docx"):
            import docx

            return "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
        return data.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"[Could not read this file: {e}]"


def render_images(images):
    cols = st.columns(3)
    for i, img in enumerate(images):
        with cols[i % 3]:
            st.image(img["url"], use_container_width=True)
            st.caption(f"[{img['title'][:60]}]({img['page']})" if img.get("page") else img["title"][:60])
    st.caption("Photos from Wikimedia Commons. Open a photo's page to check its license.")


EXT = {"python": "py", "py": "py", "javascript": "js", "js": "js", "typescript": "ts", "html": "html",
       "css": "css", "json": "json", "markdown": "md", "md": "md", "svg": "svg", "bash": "sh", "sh": "sh",
       "sql": "sql", "yaml": "yml", "java": "java", "cpp": "cpp", "c": "c", "text": "txt"}


def extract_blocks(text):
    return [(lang.lower() or "text", code.strip("\n"))
            for lang, code in re.findall(r"```([\w+-]*)\n(.*?)```", text, re.S)]


def render_workspace(blocks, cid):
    for i, (lang, code) in enumerate(blocks):
        st.markdown(f"**Artifact {i + 1}** · `{lang}`")
        previewable = lang in ("html", "svg", "markdown", "md")
        if previewable:
            tab_prev, tab_code = st.tabs(["Preview", "Code"])
            with tab_prev:
                if lang == "html":
                    components.html(code, height=520, scrolling=True)
                elif lang == "svg":
                    components.html(f"<div style='background:#fff'>{code}</div>", height=520, scrolling=True)
                else:
                    st.markdown(code)
            with tab_code:
                st.code(code, language=lang if lang != "md" else "markdown")
        else:
            st.code(code, language=lang)
        st.download_button("⬇️ Download", data=code, file_name=f"artifact_{i + 1}.{EXT.get(lang, 'txt')}",
                           key=f"dl_{cid}_{i}")


def friendly_error(e):
    name, msg = type(e).__name__, str(e)
    low = msg.lower()
    if "401" in msg or "invalid_api_key" in low or "authentication" in name.lower():
        return "Your Groq API key looks invalid. Check it in the sidebar."
    if "429" in msg or "ratelimit" in name.lower() or "rate limit" in low:
        return "Rate limit reached (free tier). Wait a minute and retry, or switch to a smaller model."
    if "413" in msg or "too large" in low or "tokens" in low and "limit" in low:
        return "That request is too big for the model's limit. Use fewer or smaller files, or start a new chat."
    if "connection" in name.lower() or "timeout" in name.lower():
        return "Couldn't reach the server. Check your connection and retry."
    if "model" in low and ("not found" in low or "decommissioned" in low):
        return "That model isn't available on Groq right now. Pick another one in the sidebar."
    return f"Something went wrong: {msg}"


def is_tool_error(e):
    low = str(e).lower()
    return "tool" in low or "function" in low or "400" in low


@st.cache_resource(show_spinner=False)
def get_llm(api_key, model, temperature):
    from langchain_groq import ChatGroq

    return ChatGroq(model=model, api_key=api_key, temperature=temperature, max_tokens=MAX_TOKENS)


def build_messages(history, system_text):
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    msgs = [SystemMessage(content=system_text)]
    for m in history[-MAX_HISTORY:]:
        msgs.append(HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]))
    return msgs


def run_agent(llm, lc_messages, use_tools):
    """Stream a reply, running tools as the model asks. Returns (answer, images)."""
    from langchain_core.messages import ToolMessage

    runner = llm.bind_tools(TOOL_SCHEMAS) if use_tools else llm
    images = []
    for step in range(MAX_TOOL_STEPS + 1):
        box, text, full = st.empty(), "", None
        for chunk in runner.stream(lc_messages):
            full = chunk if full is None else full + chunk
            if chunk.content:
                text += chunk.content
                box.markdown(text + "▌")
        calls = (getattr(full, "tool_calls", None) or []) if use_tools else []
        if not calls or step == MAX_TOOL_STEPS:
            box.markdown(text)
            return text, images
        box.empty()
        lc_messages.append(full)
        for call in calls:
            args = call.get("args") or {}
            detail = args.get("query") or args.get("url") or args.get("location") or args.get("expression") or ""
            with st.status(f"🔧 {TOOL_LABELS.get(call['name'], call['name'])}: {detail}"[:120], expanded=False):
                result, imgs = run_tool(call["name"], args)
                st.write(result[:1500])
            images.extend(imgs)
            lc_messages.append(ToolMessage(content=result[:6000], tool_call_id=call["id"]))
    return "", images


# ----------------------------------------------------------------------------
# State
# ----------------------------------------------------------------------------
def new_chat():
    cid = st.session_state.next_id
    st.session_state.next_id += 1
    st.session_state.chats[cid] = {"title": "New chat", "messages": [], "blocks": [], "error": ""}
    st.session_state.current = cid
    st.session_state.show_workspace = False
    st.session_state.pending = False


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
    use_tools = st.toggle("Web & tools", value=True, help="Search, read pages, photos, weather, calculator")
    custom = st.text_area("Custom instructions", placeholder="e.g. Answer in Arabic. Keep replies short.",
                          height=90, key="custom")

    st.markdown("---")
    st.caption("Files for this chat")
    uploads = st.file_uploader(
        "Attach files", accept_multiple_files=True, label_visibility="collapsed",
        type=["pdf", "docx", "txt", "md", "csv", "json", "py", "js", "html", "css", "sql", "yaml", "yml"],
        key=f"up_{st.session_state.current}",
    )

    st.markdown("---")
    st.caption("Backup")
    export = {str(k): v for k, v in st.session_state.chats.items()}
    st.download_button("⬇️ Export chats", data=json.dumps(export, ensure_ascii=False, indent=2),
                       file_name="chandlio_chats.json", mime="application/json", use_container_width=True)
    imp = st.file_uploader("Import chats", type="json", label_visibility="collapsed", key="import_box")
    if imp is not None and st.session_state.last_import != imp.file_id:
        st.session_state.last_import = imp.file_id
        try:
            for item in json.loads(imp.getvalue()).values():
                if isinstance(item.get("messages"), list):
                    cid = st.session_state.next_id
                    st.session_state.next_id += 1
                    msgs = []
                    for m in item["messages"]:
                        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
                            entry = {"role": m["role"], "content": m["content"]}
                            if isinstance(m.get("images"), list):
                                entry["images"] = m["images"]
                            msgs.append(entry)
                    st.session_state.chats[cid] = {"title": str(item.get("title", "Imported chat"))[:40],
                                                   "messages": msgs, "blocks": [], "error": ""}
            st.rerun()
        except Exception:
            st.error("That file isn't a valid chat export.")

# ----------------------------------------------------------------------------
# Gate: need a key
# ----------------------------------------------------------------------------
if not api_key:
    st.markdown("<div class='hero'><h1>⚡ Welcome to Chandlio's AI Bot</h1>"
                "<p>Enter your free Groq API key in the sidebar to get started.</p></div>",
                unsafe_allow_html=True)
    st.stop()

try:
    llm = get_llm(api_key, model, temperature)
except Exception as e:
    st.error(f"Could not start the model client: {e}")
    st.stop()

# ----------------------------------------------------------------------------
# System prompt with date, custom instructions and file context
# ----------------------------------------------------------------------------
system_text = SYSTEM_PROMPT + f"\n\nCurrent date and time (UTC): {datetime.now(timezone.utc):%A %d %B %Y, %H:%M}."
if custom.strip():
    system_text += f"\n\nUser's custom instructions (follow them):\n{custom.strip()}"
if uploads:
    budget, parts, truncated = MAX_TOTAL_FILE_CHARS, [], False
    for f in uploads:
        text = extract_text(f.name, f.getvalue())
        take = text[:min(MAX_FILE_CHARS, budget)]
        truncated = truncated or len(take) < len(text)
        budget -= len(take)
        parts.append(f"### File: {f.name}\n{take}")
        if budget <= 0:
            break
    system_text += "\n\nAttached files:\n" + "\n\n".join(parts)
    if truncated:
        st.sidebar.warning("Large files were shortened to fit the free-tier limits.")

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
            "<p>Try: <i>What's the latest news on SpaceX?</i> · <i>Show me photos of Switzerland</i> · "
            "<i>Weather in Riyadh</i> · <i>Build a snake game</i></p></div>",
            unsafe_allow_html=True)

    for m in messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("images"):
                render_images(m["images"])

    if st.session_state.pending and messages and messages[-1]["role"] == "user":
        st.session_state.pending = False
        with st.chat_message("assistant"):
            try:
                try:
                    answer, imgs = run_agent(llm, build_messages(messages, system_text), use_tools)
                except Exception as e:
                    if use_tools and is_tool_error(e):
                        st.caption("Tools didn't work on this model, answering without them.")
                        answer, imgs = run_agent(llm, build_messages(messages, system_text), False)
                    else:
                        raise
                entry = {"role": "assistant", "content": answer or ("Here you go:" if imgs else "(no response)")}
                if imgs:
                    entry["images"] = imgs
                messages.append(entry)
                chat["error"] = ""
                chat["blocks"] = extract_blocks(answer)
                st.session_state.show_workspace = bool(chat["blocks"])
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
        render_workspace(chat["blocks"], st.session_state.current)

# Chat input last, outside columns, so it stays pinned to the bottom
if prompt := st.chat_input("Message Chandlio..."):
    messages.append({"role": "user", "content": prompt})
    if chat["title"] == "New chat":
        chat["title"] = prompt.strip().replace("\n", " ")[:30] or "New chat"
    chat["error"] = ""
    st.session_state.pending = True
    st.rerun()
