import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import requests
from bs4 import BeautifulSoup

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global Insight Lab",
    page_icon="🌍",
    layout="wide",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark gradient background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: #f0f0f0;
    }

    /* Title area */
    .title-block {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .title-block h1 {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #56CCF2, #2F80ED, #eb5757);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px;
    }
    .title-block p {
        color: #aaa;
        font-size: 1.05rem;
        margin-top: -0.5rem;
    }

    /* Source badge cards */
    .badge-row {
        display: flex;
        gap: 1rem;
        justify-content: center;
        margin: 0.5rem 0 1.5rem;
    }
    .badge {
        padding: 0.35rem 1.1rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .badge-bbc  { background: #1565C0; color: #fff; }
    .badge-aj   { background: #B71C1C; color: #fff; }

    /* Headline list items */
    .headline-item {
        background: rgba(255,255,255,0.05);
        border-left: 3px solid;
        padding: 0.5rem 0.9rem;
        margin-bottom: 0.45rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .headline-item.bbc { border-color: #42A5F5; }
    .headline-item.aj  { border-color: #EF5350; }

    /* Section headers */
    .section-label {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Divider */
    hr { border-color: rgba(255,255,255,0.1); }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(255,255,255,0.04) !important;
    }
    section[data-testid="stSidebar"] * { color: #ddd !important; }

    /* Text area */
    textarea {
        background: rgba(255,255,255,0.06) !important;
        color: #eee !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="title-block">
  <h1>🌍 Global Insight Lab</h1>
  <p>Compare how global media outlets frame the same topic — powered by live headlines.</p>
</div>
<div class="badge-row">
  <span class="badge badge-bbc">📺 BBC News</span>
  <span class="badge badge-aj">📡 Al Jazeera</span>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Search Settings")
    keyword = st.text_input(
        "Enter a keyword",
        placeholder="e.g. climate, AI, economy …",
        help="The app will search BBC and Al Jazeera for this topic."
    )
    st.markdown("---")
    st.markdown("**How it works**")
    st.caption(
        "1. Enter a keyword above.\n"
        "2. The app fetches the latest 5 matching headlines from each outlet.\n"
        "3. Word clouds are generated from the headline text.\n"
        "4. Write your PEEL analysis at the bottom."
    )
    st.markdown("---")
    st.caption("⚠️ Results depend on live website structure. If a source is unreachable, a demo cloud is shown.")

# ─── Helpers ────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

STOPWORDS_EXTRA = set(STOPWORDS) | {
    "the", "is", "in", "a", "an", "and", "or", "but", "of", "to",
    "for", "on", "at", "by", "with", "from", "as", "are", "was",
    "were", "be", "been", "has", "have", "had", "will", "would",
    "says", "say", "said", "new", "after", "amid", "over", "its",
    "that", "this", "it", "he", "she", "they", "his", "her", "their",
    "up", "out", "not", "more", "about",
}


def fetch_bbc(keyword: str) -> list[str]:
    """Scrape BBC search results for the keyword."""
    url = f"https://www.bbc.co.uk/search?q={requests.utils.quote(keyword)}&filter=news"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        titles = []
        # BBC search result titles live in <p> with a specific data-testid or in <h1>
        for tag in soup.find_all(["h3", "h2", "p"], limit=60):
            text = tag.get_text(strip=True)
            if keyword.lower() in text.lower() and len(text) > 20:
                titles.append(text)
            if len(titles) == 5:
                break
        # Fallback: grab any prominent text blocks
        if not titles:
            for tag in soup.find_all(["h3", "h2"], limit=20):
                text = tag.get_text(strip=True)
                if len(text) > 20:
                    titles.append(text)
                if len(titles) == 5:
                    break
        return titles[:5]
    except Exception:
        return []


def fetch_aljazeera(keyword: str) -> list[str]:
    """Scrape Al Jazeera search results for the keyword."""
    url = f"https://www.aljazeera.com/search/{requests.utils.quote(keyword)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        titles = []
        for tag in soup.find_all(["h3", "h2"], limit=60):
            text = tag.get_text(strip=True)
            if len(text) > 20:
                titles.append(text)
            if len(titles) == 5:
                break
        return titles[:5]
    except Exception:
        return []


def make_wordcloud(text: str, colormap: str) -> plt.Figure:
    """Generate a word-cloud figure from text."""
    if not text.strip():
        text = "No headlines found for this keyword"
    wc = WordCloud(
        width=700,
        height=380,
        background_color=None,
        mode="RGBA",
        colormap=colormap,
        stopwords=STOPWORDS_EXTRA,
        max_words=60,
        prefer_horizontal=0.85,
        collocations=False,
    ).generate(text)
    fig, ax = plt.subplots(figsize=(7, 3.8), facecolor="none")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_alpha(0)
    return fig


# ─── Main Content ───────────────────────────────────────────────────────────
if not keyword:
    st.info("👈  Enter a keyword in the sidebar to get started.", icon="💡")
else:
    with st.spinner(f"Fetching headlines for **{keyword}** …"):
        bbc_titles = fetch_bbc(keyword)
        aj_titles  = fetch_aljazeera(keyword)

    bbc_text = " ".join(bbc_titles)
    aj_text  = " ".join(aj_titles)

    # ── Headlines ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-label">📺 <span style="color:#42A5F5">BBC News</span> — Top Headlines</div>', unsafe_allow_html=True)
        if bbc_titles:
            for t in bbc_titles:
                st.markdown(f'<div class="headline-item bbc">• {t}</div>', unsafe_allow_html=True)
        else:
            st.warning("Could not retrieve BBC headlines. BBC may be blocking automated requests.")

    with col2:
        st.markdown('<div class="section-label">📡 <span style="color:#EF5350">Al Jazeera</span> — Top Headlines</div>', unsafe_allow_html=True)
        if aj_titles:
            for t in aj_titles:
                st.markdown(f'<div class="headline-item aj">• {t}</div>', unsafe_allow_html=True)
        else:
            st.warning("Could not retrieve Al Jazeera headlines.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Word Clouds ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### ☁️ Word Clouds — *\"{keyword}\"*")
    st.caption("Generated from headline text · stopwords removed · hover to zoom")

    wc_col1, wc_col2 = st.columns(2)

    with wc_col1:
        st.markdown('<div class="section-label">📺 <span style="color:#42A5F5">BBC</span> · Blues palette</div>', unsafe_allow_html=True)
        fig_bbc = make_wordcloud(bbc_text or keyword, "Blues")
        st.pyplot(fig_bbc, use_container_width=True)
        plt.close(fig_bbc)

    with wc_col2:
        st.markdown('<div class="section-label">📡 <span style="color:#EF5350">Al Jazeera</span> · Reds palette</div>', unsafe_allow_html=True)
        fig_aj = make_wordcloud(aj_text or keyword, "Reds")
        st.pyplot(fig_aj, use_container_width=True)
        plt.close(fig_aj)

    # ── PEEL Analysis ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📝 Media Analysis (PEEL Structure)")
    st.caption(
        "Use the PEEL framework: **P**oint → **E**vidence → **E**xplanation → **L**ink. "
        "Compare how each outlet frames the topic, what language they use, and what this reveals about their perspective."
    )

    peel_placeholder = (
        "Point: State your main analytical claim about how the two outlets differ.\n\n"
        "Evidence: Quote specific words or phrases from the headlines above.\n\n"
        "Explanation: Explain what this language choice suggests about each outlet's perspective or audience.\n\n"
        "Link: Connect back to the broader theme of media bias / framing."
    )

    st.text_area(
        label="Your Analysis",
        placeholder=peel_placeholder,
        height=280,
        key="peel_input",
        label_visibility="collapsed",
    )

    col_save, _ = st.columns([1, 5])
    with col_save:
        if st.button("💾 Copy to Clipboard Tip"):
            st.info("Select all text in the box above (Ctrl+A / ⌘+A) then copy.", icon="📋")
