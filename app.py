import time
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
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: #f0f0f0;
    }
    .title-block {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .title-block h1 {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #CC0000, #FF6F00, #eb5757);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px;
    }
    .title-block p {
        color: #aaa;
        font-size: 1.05rem;
        margin-top: -0.5rem;
    }
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
    .badge-cnn { background: #CC0000; color: #fff; }
    .badge-aj  { background: #FF6F00; color: #fff; }

    .headline-item {
        background: rgba(255,255,255,0.05);
        border-left: 3px solid;
        padding: 0.5rem 0.9rem;
        margin-bottom: 0.45rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .headline-item.cnn { border-color: #FF5252; }
    .headline-item.aj  { border-color: #FFB300; }

    .section-label {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    hr { border-color: rgba(255,255,255,0.1); }

    section[data-testid="stSidebar"] {
        background: rgba(255,255,255,0.04) !important;
    }
    section[data-testid="stSidebar"] * { color: #ddd !important; }

    textarea {
        background: rgba(255,255,255,0.06) !important;
        color: #eee !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 8px !important;
    }
    .metric-card {
        background: rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .metric-card .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
    }
    .metric-card .metric-label {
        font-size: 0.75rem;
        color: #aaa;
        margin-top: 0.1rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="title-block">
  <h1>🌍 Global Insight Lab</h1>
  <p>Compare how CNN and Al Jazeera frame the same topic — powered by live headlines.</p>
</div>
<div class="badge-row">
  <span class="badge badge-cnn">📺 CNN</span>
  <span class="badge badge-aj">📡 Al Jazeera</span>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Search Settings")
    keyword = st.text_input(
        "Enter a keyword",
        placeholder="e.g. Gaza, AI, economy …",
        help="The app will search CNN and Al Jazeera for this topic."
    )
    st.markdown("---")
    st.markdown("**How it works**")
    st.caption(
        "1. Enter a keyword above.\n"
        "2. The app fetches the latest 5 matching headlines from each outlet "
        "via Google News RSS.\n"
        "3. Word clouds are generated from the headline text.\n"
        "4. Shared keywords between both outlets are highlighted.\n"
        "5. Write your PEEL analysis at the bottom."
    )
    st.markdown("---")
    st.caption(
        "⚠️ Headlines are fetched live via Google News RSS. "
        "Results may vary by keyword popularity."
    )

# ─── Constants ──────────────────────────────────────────────────────────────
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
    "up", "out", "not", "more", "about", "what", "how", "who", "why",
    "us", "s", "one", "two", "could", "may",
}


# ─── Fetchers ───────────────────────────────────────────────────────────────
def _google_news_rss(keyword: str, site: str, suffixes: list) -> list:
    """
    Query Google News RSS for `keyword site:<site>`.

    Google pre-renders JS pages before indexing, so this reliably returns
    keyword-accurate headlines even for outlets whose own search pages are
    JavaScript-rendered (CNN, Al Jazeera, etc.).
    Returns up to 5 clean headline strings.
    """
    titles = []
    try:
        encoded = requests.utils.quote(f"{keyword} site:{site}")
        url = (
            f"https://news.google.com/rss/search"
            f"?q={encoded}&hl=en-US&gl=US&ceid=US:en&_t={int(time.time())}"
        )
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item"):
            tag = item.find("title")
            if not tag:
                continue
            text = tag.get_text(strip=True)
            for suffix in suffixes:
                text = text.replace(suffix, "")
            text = text.strip()
            if len(text) > 15 and text not in titles:
                titles.append(text)
            if len(titles) == 5:
                break
    except Exception:
        pass
    return titles


def _rss_fallback(rss_url: str, keyword: str) -> list:
    """
    Pull a public RSS feed and filter titles by keyword.
    If keyword yields nothing, return the 5 most recent items.
    """
    titles = []
    try:
        r = requests.get(
            f"{rss_url}?_t={int(time.time())}",
            headers=HEADERS, timeout=10
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        kw = keyword.lower()
        for item in soup.find_all("item"):
            tag = item.find("title")
            if not tag:
                continue
            text = tag.get_text(strip=True)
            if kw in text.lower() and text not in titles:
                titles.append(text)
            if len(titles) == 5:
                break
        # Keyword too niche → fall back to latest 5
        if not titles:
            for item in soup.find_all("item")[:5]:
                tag = item.find("title")
                if tag:
                    titles.append(tag.get_text(strip=True))
    except Exception:
        pass
    return titles


def fetch_cnn(keyword: str) -> list:
    """
    2-tier fetch for CNN headlines.

    Tier 1 — Google News RSS  : `keyword site:cnn.com`
    Tier 2 — CNN RSS fallback : rss.cnn.com/rss/edition.rss
    """
    CNN_SUFFIXES = [" - CNN", " - CNN International", " | CNN"]
    titles = _google_news_rss(keyword, "cnn.com", CNN_SUFFIXES)
    if len(titles) >= 3:
        return titles[:5]
    titles += _rss_fallback("http://rss.cnn.com/rss/edition.rss", keyword)
    return list(dict.fromkeys(titles))[:5]   # deduplicate, preserve order


def fetch_aljazeera(keyword: str) -> list:
    """
    2-tier fetch for Al Jazeera headlines.

    Tier 1 — Google News RSS  : `keyword site:aljazeera.com`
    Tier 2 — AJ RSS fallback  : aljazeera.com/xml/rss/all.xml
    """
    AJ_SUFFIXES = [" - Al Jazeera English", " - Al Jazeera"]
    titles = _google_news_rss(keyword, "aljazeera.com", AJ_SUFFIXES)
    if len(titles) >= 3:
        return titles[:5]
    titles += _rss_fallback(
        "https://www.aljazeera.com/xml/rss/all.xml", keyword
    )
    return list(dict.fromkeys(titles))[:5]


# ─── Visualisation helpers ───────────────────────────────────────────────────
def make_wordcloud(text: str, colormap: str) -> plt.Figure:
    if not text.strip():
        text = "No headlines found for this keyword"
    wc = WordCloud(
        width=700, height=380,
        background_color=None, mode="RGBA",
        colormap=colormap,
        stopwords=STOPWORDS_EXTRA,
        max_words=60, prefer_horizontal=0.85,
        collocations=False,
    ).generate(text)
    fig, ax = plt.subplots(figsize=(7, 3.8), facecolor="none")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_alpha(0)
    return fig


def word_overlap(titles_a: list, titles_b: list) -> set:
    """Return meaningful words that appear in both sets of headlines."""
    def meaningful_words(titles):
        result = set()
        for t in titles:
            for w in t.lower().split():
                w = w.strip(".,!?\"'();:-")
                if len(w) > 3 and w not in STOPWORDS_EXTRA:
                    result.add(w)
        return result
    return meaningful_words(titles_a) & meaningful_words(titles_b)


# ─── Main ────────────────────────────────────────────────────────────────────
if not keyword:
    st.info("👈  Enter a keyword in the sidebar to get started.", icon="💡")
else:
    with st.spinner(f"Fetching live headlines for **{keyword}** …"):
        cnn_titles = fetch_cnn(keyword)
        aj_titles  = fetch_aljazeera(keyword)

    cnn_text = " ".join(cnn_titles)
    aj_text  = " ".join(aj_titles)
    shared   = word_overlap(cnn_titles, aj_titles)

    # ── Quick stats bar ────────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value" style="color:#FF5252">{len(cnn_titles)}</div>'
            f'<div class="metric-label">CNN Headlines</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value" style="color:#FFB300">{len(aj_titles)}</div>'
            f'<div class="metric-label">Al Jazeera Headlines</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value" style="color:#69F0AE">{len(shared)}</div>'
            f'<div class="metric-label">Shared Keywords</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Headlines ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            '<div class="section-label">📺 '
            '<span style="color:#FF5252">CNN</span> — Top Headlines</div>',
            unsafe_allow_html=True,
        )
        if cnn_titles:
            for t in cnn_titles:
                st.markdown(
                    f'<div class="headline-item cnn">• {t}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.warning("Could not retrieve CNN headlines. Try a different keyword.")

    with col2:
        st.markdown(
            '<div class="section-label">📡 '
            '<span style="color:#FFB300">Al Jazeera</span> — Top Headlines</div>',
            unsafe_allow_html=True,
        )
        if aj_titles:
            for t in aj_titles:
                st.markdown(
                    f'<div class="headline-item aj">• {t}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.warning("Could not retrieve Al Jazeera headlines.")

    # ── Shared keywords callout ────────────────────────────────────────────
    if shared:
        st.markdown("<br>", unsafe_allow_html=True)
        shared_str = "  ·  ".join(sorted(shared))
        st.success(f"🔗 **Words used by both outlets:** {shared_str}")

    # ── Word Clouds ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f'### ☁️ Word Clouds — *"{keyword}"*')
    st.caption("Generated from headline text · stopwords removed")

    wc1, wc2 = st.columns(2)
    with wc1:
        st.markdown(
            '<div class="section-label">📺 '
            '<span style="color:#FF5252">CNN</span> · Reds palette</div>',
            unsafe_allow_html=True,
        )
        fig_cnn = make_wordcloud(cnn_text or keyword, "Reds")
        st.pyplot(fig_cnn, use_container_width=True)
        plt.close(fig_cnn)

    with wc2:
        st.markdown(
            '<div class="section-label">📡 '
            '<span style="color:#FFB300">Al Jazeera</span> · Oranges palette</div>',
            unsafe_allow_html=True,
        )
        fig_aj = make_wordcloud(aj_text or keyword, "Oranges")
        st.pyplot(fig_aj, use_container_width=True)
        plt.close(fig_aj)

    # ── PEEL Analysis ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📝 Media Analysis (PEEL Structure)")
    st.caption(
        "Use the PEEL framework: **P**oint → **E**vidence → **E**xplanation → **L**ink. "
        "Compare how CNN and Al Jazeera frame the topic and what this reveals "
        "about each outlet's perspective."
    )
    peel_placeholder = (
        "Point: State your main analytical claim about how the two outlets differ.\n\n"
        "Evidence: Quote specific words or phrases from the headlines above.\n\n"
        "Explanation: Explain what this language choice suggests about each "
        "outlet's perspective or target audience.\n\n"
        "Link: Connect back to the broader theme of media bias / framing."
    )
    st.text_area(
        label="Your Analysis",
        placeholder=peel_placeholder,
        height=300,
        key="peel_input",
        label_visibility="collapsed",
    )
    col_tip, _ = st.columns([1, 5])
    with col_tip:
        if st.button("💾 Copy to Clipboard Tip"):
            st.info(
                "Select all text in the box above (Ctrl+A / ⌘+A) then copy.",
                icon="📋",
            )
