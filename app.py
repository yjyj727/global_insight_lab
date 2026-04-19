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
    """
    Fetch BBC headlines for a keyword via a 2-tier RSS strategy.

    Why not scrape bbc.co.uk/search directly?
    → BBC's search page is JavaScript-rendered. requests+BeautifulSoup only
      receives the pre-JS shell, which always contains generic strings like
      'Search results for [keyword]' regardless of what was searched.

    Tier 1 — Google News RSS (primary)
      Queries Google News with `keyword site:bbc.com`.
      Google pre-renders JS pages before indexing, so results are keyword-
      accurate and returned as plain XML — no JS engine needed.

    Tier 2 — BBC RSS feed (fallback)
      Pulls BBC's public News RSS and filters titles by keyword locally.
    """
    import time
    titles: list[str] = []

    # ── Tier 1: Google News RSS ─────────────────────────────────────────────
    try:
        encoded = requests.utils.quote(f"{keyword} site:bbc.com")
        gnews_url = (
            f"https://news.google.com/rss/search"
            f"?q={encoded}&hl=en-US&gl=US&ceid=US:en&_t={int(time.time())}"
        )
        r = requests.get(gnews_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            if not title_tag:
                continue
            text = title_tag.get_text(strip=True)
            # Strip Google News source suffix e.g. " - BBC News"
            for suffix in [" - BBC News", " - BBC", " - BBC Sport"]:
                text = text.replace(suffix, "")
            text = text.strip()
            if len(text) > 15 and text not in titles:
                titles.append(text)
            if len(titles) == 5:
                break
    except Exception:
        pass

    if len(titles) >= 3:
        return titles[:5]

    # ── Tier 2: BBC RSS feed, filtered by keyword ───────────────────────────
    try:
        rss_url = (
            f"https://feeds.bbci.co.uk/news/rss.xml?_t={int(time.time())}"
        )
        r = requests.get(rss_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        kw_lower = keyword.lower()
        # First pass: keyword-matched titles only
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            if not title_tag:
                continue
            text = title_tag.get_text(strip=True)
            if kw_lower in text.lower() and text not in titles:
                titles.append(text)
            if len(titles) == 5:
                break
        # Second pass: keyword too niche → return latest 5 headlines
        if not titles:
            for item in soup.find_all("item")[:5]:
                title_tag = item.find("title")
                if title_tag:
                    titles.append(title_tag.get_text(strip=True))
    except Exception:
        pass

    return titles[:5]


def fetch_aljazeera(keyword: str) -> list[str]:
    """
    Fetch Al Jazeera headlines for a keyword via a 2-tier RSS strategy.

    Why not scrape aljazeera.com/search directly?
    → The page is JavaScript-rendered (React/Next.js). requests+BeautifulSoup
      only receives the pre-JS HTML shell, which always shows the same generic
      placeholder text regardless of the keyword.

    Tier 1 — Google News RSS (primary)
      Queries Google News with `keyword site:aljazeera.com`.
      Google pre-renders JS pages before indexing, so results are keyword-
      accurate and returned as plain XML — no JS engine needed.

    Tier 2 — Al Jazeera's own RSS feed (fallback)
      Pulls the full AJ RSS feed and filters titles by keyword locally.
      Less precise (limited to ~20 recent items) but always reachable.
    """
    import time
    titles: list[str] = []

    # ── Tier 1: Google News RSS ─────────────────────────────────────────────
    try:
        encoded = requests.utils.quote(f"{keyword} site:aljazeera.com")
        gnews_url = (
            f"https://news.google.com/rss/search"
            f"?q={encoded}&hl=en-US&gl=US&ceid=US:en&_t={int(time.time())}"
        )
        r = requests.get(gnews_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            if not title_tag:
                continue
            text = title_tag.get_text(strip=True)
            # Strip Google News source suffix e.g. " - Al Jazeera English"
            for suffix in [" - Al Jazeera English", " - Al Jazeera"]:
                text = text.replace(suffix, "")
            text = text.strip()
            if len(text) > 15 and text not in titles:
                titles.append(text)
            if len(titles) == 5:
                break
    except Exception:
        pass

    if len(titles) >= 3:
        return titles[:5]

    # ── Tier 2: Al Jazeera RSS feed, filtered by keyword ───────────────────
    try:
        rss_url = (
            f"https://www.aljazeera.com/xml/rss/all.xml?_t={int(time.time())}"
        )
        r = requests.get(rss_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        kw_lower = keyword.lower()
        # First pass: keyword-matched titles only
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            if not title_tag:
                continue
            text = title_tag.get_text(strip=True)
            if kw_lower in text.lower() and text not in titles:
                titles.append(text)
            if len(titles) == 5:
                break
        # Second pass: keyword too niche → return latest 5 headlines
        if not titles:
            for item in soup.find_all("item")[:5]:
                title_tag = item.find("title")
                if title_tag:
                    titles.append(title_tag.get_text(strip=True))
    except Exception:
        pass

    return titles[:5]


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
