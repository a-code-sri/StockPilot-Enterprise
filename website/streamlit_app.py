"""
Serves the StockPilot project website (index.html + screenshots) as a Streamlit app,
so it can be hosted for free on Streamlit Community Cloud.

Run locally:   streamlit run website/streamlit_app.py
Deploy:        share.streamlit.io -> Create app -> main file path: website/streamlit_app.py
"""

import base64
import re
from pathlib import Path

import streamlit as st

HERE = Path(__file__).parent

st.set_page_config(page_title="StockPilot Enterprise", page_icon="📦", layout="wide")


@st.cache_data
def build_page() -> str:
    html = (HERE / "index.html").read_text(encoding="utf-8")

    # The page runs inside an iframe, which can't load files next to this script,
    # so the screenshots are inlined as data URIs.
    def inline(match: re.Match) -> str:
        data = base64.b64encode((HERE / match.group(1)).read_bytes()).decode()
        return f"data:image/webp;base64,{data}"

    html = re.sub(r"(screenshots/[\w-]+\.webp)", inline, html)

    # Outside links open in a new tab; most sites (GitHub included) refuse to load in an iframe.
    # In-page links (#setup) stay as they are.
    html = re.sub(r'<a (class="[^"]*" )?href="(https?://)', r'<a target="_blank" rel="noopener" \1href="\2', html)

    # Inside the embedded frame, "#setup" resolves against the Streamlit app's URL and would
    # load the app again inside the frame. Scroll to the section instead.
    anchor_fix = """<script>
document.addEventListener("click", function (e) {
  var a = e.target.closest('a[href^="#"]');
  if (!a) return;
  e.preventDefault();
  var id = a.getAttribute("href").slice(1);
  var el = id ? document.getElementById(id) : null;
  if (el) el.scrollIntoView({ behavior: "smooth" }); else window.scrollTo({ top: 0, behavior: "smooth" });
});
</script>"""
    return html.replace("</body>", anchor_fix + "\n</body>")


# Hide Streamlit's own header and padding and let the site fill the window.
st.markdown(
    """
    <style>
      header[data-testid="stHeader"], #MainMenu, footer { display: none !important; }
      .block-container, [data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: 100% !important; }
      [data-testid="stAppViewContainer"] .main, [data-testid="stMain"] { overflow: hidden; }
      [data-testid="stVerticalBlock"] { gap: 0 !important; }
      [data-testid="stElementContainer"]:has(style) { display: none; }
      iframe { height: 100vh !important; display: block; border: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

if hasattr(st, "iframe"):  # Streamlit 1.50+
    st.iframe(build_page(), height=900)
else:
    import streamlit.components.v1 as components

    components.html(build_page(), height=900, scrolling=True)
