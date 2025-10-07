import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from typing import Optional


st.set_page_config(
    page_title="Cruise Reviews Insights",
    page_icon="🛳️",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def read_csv_smart(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")


@st.cache_data(show_spinner=False)
def load_all_data(base: Path):
    out = {}
    out_dir = base / "outputs"
    out["has_outputs"] = out_dir.exists()
    # Primary enriched dataset
    enriched = out_dir / "master_with_topics.csv"
    if enriched.exists():
        out["df"] = read_csv_smart(enriched)
    else:
        # Fallback to master if available
        master = base / "master_data.csv"
        out["df"] = read_csv_smart(master) if master.exists() else pd.DataFrame()

    # Optional artifacts
    for name, rel in [
        ("topic_summary", "topic_summary.csv"),
        ("topic_top_words", "topic_top_words.csv"),
        ("aspect_drivers", "aspect_drivers.csv"),
        ("recommendations", "recommendations.csv"),
        ("impact_estimates", "impact_estimates.csv"),
    ]:
        p = (out_dir / rel) if out_dir.exists() else None
        out[name] = read_csv_smart(p) if p and p.exists() else pd.DataFrame()
    return out


def metric_card(label: str, value, help_text: Optional[str] = None):
    m = st.metric(label, value)
    if help_text:
        st.caption(help_text)
    return m


def overview_tab(df: pd.DataFrame):
    st.subheader("Overview")
    if df.empty:
        st.info("No data found. Ensure outputs/master_with_topics.csv or master_data.csv exists.")
        return

    cols = df.columns
    has_rating = "rating" in cols
    has_sentiment = "sentiment" in cols
    has_label = "sentiment_label" in cols

    total_reviews = len(df)
    avg_rating = float(df["rating"].mean()) if has_rating else None
    avg_sent = float(df["sentiment"].mean()) if has_sentiment else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Reviews", f"{total_reviews:,}")
    with c2:
        metric_card("Average Rating", f"{avg_rating:.2f}" if avg_rating is not None else "—")
    with c3:
        metric_card("Average Sentiment", f"{avg_sent:.3f}" if avg_sent is not None else "—")
    with c4:
        if has_label:
            shares = df["sentiment_label"].value_counts(normalize=True).reindex(["negative","neutral","positive"]).fillna(0)
            metric_card("% Positive", f"{shares.get('positive',0)*100:,.1f}%")
        else:
            metric_card("% Positive", "—")

    st.divider()

    st.markdown("Filters")
    fcols = st.columns(3)
    filtered = df.copy()
    with fcols[0]:
        if has_rating:
            rmin = float(np.nanmin(df["rating"])) if df["rating"].notna().any() else 0.0
            rmax = float(np.nanmax(df["rating"])) if df["rating"].notna().any() else 5.0
            rsel = st.slider("Rating", min_value=float(np.floor(rmin)), max_value=float(np.ceil(rmax)), value=(float(np.floor(rmin)), float(np.ceil(rmax))), step=0.5)
            filtered = filtered[filtered["rating"].between(rsel[0], rsel[1])]
    with fcols[1]:
        if has_label:
            labs = st.multiselect("Sentiment Label", options=sorted(df["sentiment_label"].dropna().unique().tolist()), default=None)
            if labs:
                filtered = filtered[filtered["sentiment_label"].isin(labs)]
    with fcols[2]:
        q = st.text_input("Search text contains")
        if q:
            ql = q.lower()
            filtered = filtered[filtered.get("review_text","").astype(str).str.lower().str.contains(ql, na=False)]

    st.caption(f"Showing {len(filtered):,} reviews after filters")

    left, right = st.columns(2)
    with left:
        if has_rating:
            ch = alt.Chart(filtered.dropna(subset=["rating"])) \
                .mark_bar() \
                .encode(
                    x=alt.X("rating:Q", bin=alt.Bin(maxbins=10), title="Rating"),
                    y=alt.Y("count():Q", title="Count"),
                    tooltip=[alt.Tooltip("count():Q", title="Count")],
                ).properties(height=300, title="Rating Distribution")
            st.altair_chart(ch, use_container_width=True)
    with right:
        if has_sentiment:
            ch = alt.Chart(filtered.dropna(subset=["sentiment"])) \
                .mark_area(opacity=0.6) \
                .encode(
                    x=alt.X("sentiment:Q", bin=alt.Bin(maxbins=30), title="Sentiment"),
                    y=alt.Y("count():Q", title="Count"),
                    tooltip=[alt.Tooltip("count():Q", title="Count")],
                ).properties(height=300, title="Sentiment Distribution")
            st.altair_chart(ch, use_container_width=True)

    if has_rating and has_sentiment:
        st.markdown("Correlation: Rating vs Sentiment")
        ch = alt.Chart(filtered.dropna(subset=["rating","sentiment"])) \
            .mark_circle(size=50, opacity=0.35) \
            .encode(
                x=alt.X("rating:Q", title="Rating"),
                y=alt.Y("sentiment:Q", title="Sentiment"),
                color=alt.value("#1f77b4"),
                tooltip=["rating","sentiment","review_text"],
            ).properties(height=360)
        st.altair_chart(ch, use_container_width=True)


def topics_tab(df: pd.DataFrame, topic_summary: pd.DataFrame, topic_words: pd.DataFrame):
    st.subheader("Topics")
    if topic_summary.empty:
        st.info("No topic_summary.csv found. Run topic modelling first.")
        return

    sel = alt.selection_point(fields=["topic_id"], on="click", nearest=True, empty="all")
    ch = alt.Chart(topic_summary).mark_circle(size=180).encode(
        x=alt.X("review_count:Q", title="Review Count"),
        y=alt.Y("avg_sentiment:Q", title="Average Sentiment"),
        color=alt.Color("avg_sentiment:Q", scale=alt.Scale(scheme="blueorange"), legend=None),
        tooltip=["topic_id","review_count","avg_sentiment"],
        opacity=alt.condition(sel, alt.value(0.95), alt.value(0.35)),
    ).add_params(sel).properties(height=420, title="Topic Volume vs Sentiment")

    st.altair_chart(ch, use_container_width=True)

    st.markdown("Details")
    # Determine selected topic(s)
    selected_ids = []
    try:
        selected_ids = [int(v.get("topic_id")) for v in sel.get("values", [])]  # type: ignore[attr-defined]
    except Exception:
        pass

    # Fallback: UI selector
    if not selected_ids:
        selected_ids = [int(topic_summary.sort_values(["review_count","avg_sentiment"], ascending=[False, True]).iloc[0]["topic_id"])]

    tcol1, tcol2 = st.columns([1, 2])
    with tcol1:
        chosen = st.selectbox(
            "Topic",
            options=topic_summary["topic_id"].tolist(),
            index=max(0, topic_summary.index[topic_summary["topic_id"] == selected_ids[0]][0]) if selected_ids else 0,
        )
        st.dataframe(
            topic_summary[topic_summary["topic_id"] == chosen],
            use_container_width=True,
            hide_index=True,
        )
        if not topic_words.empty:
            row = topic_words[topic_words["topic_id"] == chosen]
            if not row.empty:
                words = str(row.iloc[0]["top_words"]).split(",")
                st.markdown("Top Words")
                st.write(", ".join([w.strip() for w in words]))

    with tcol2:
        if not df.empty and "topic_id" in df.columns:
            samples = df[df["topic_id"] == chosen].copy()
            if len(samples) > 0:
                samples = samples.sample(min(10, len(samples)), random_state=42)
                show_cols = [c for c in ["review_text","rating","sentiment","sentiment_label"] if c in samples.columns]
                st.dataframe(samples[show_cols], use_container_width=True, hide_index=True)


def drivers_tab(drivers: pd.DataFrame):
    st.subheader("Aspect Drivers")
    if drivers.empty:
        st.info("No aspect_drivers.csv found. Run aspect driver mining first.")
        return

    drivers = drivers.copy()
    drivers["avg_sentiment"] = pd.to_numeric(drivers["avg_sentiment"], errors="coerce")
    pos = drivers.sort_values("avg_sentiment", ascending=False).head(15)
    neg = drivers.sort_values("avg_sentiment", ascending=True).head(15)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("Top Positive-Associated Phrases")
        ch = alt.Chart(pos).mark_bar().encode(
            x=alt.X("avg_sentiment:Q", title="Avg Sentiment"),
            y=alt.Y("ngram:N", sort="-x", title="Phrase"),
            color=alt.value("#2ca02c"),
            tooltip=["ngram","count","avg_sentiment"],
        ).properties(height=420)
        st.altair_chart(ch, use_container_width=True)
    with c2:
        st.markdown("Top Negative-Associated Phrases")
        ch = alt.Chart(neg).mark_bar().encode(
            x=alt.X("avg_sentiment:Q", title="Avg Sentiment"),
            y=alt.Y("ngram:N", sort="x", title="Phrase"),
            color=alt.value("#d62728"),
            tooltip=["ngram","count","avg_sentiment"],
        ).properties(height=420)
        st.altair_chart(ch, use_container_width=True)


def recs_tab(recs: pd.DataFrame, impact: pd.DataFrame):
    st.subheader("Recommendations")
    if recs.empty:
        st.info("No recommendations.csv found. Run selection step first.")
        return

    st.markdown("Priority Topics & Actions")
    st.dataframe(recs, use_container_width=True, hide_index=True)

    st.markdown("Estimated Impact")
    if not impact.empty:
        ch = alt.Chart(impact).mark_bar().encode(
            x=alt.X("projected_visitation_uplift_%:Q", title="Projected Visitation Uplift %"),
            y=alt.Y("topic_id:N", sort="-x", title="Topic"),
            color=alt.value("#1f77b4"),
            tooltip=list(impact.columns),
        ).properties(height=300)
        st.altair_chart(ch, use_container_width=True)
        st.dataframe(impact, use_container_width=True, hide_index=True)
    else:
        st.info("No impact_estimates.csv found.")


def explore_tab(df: pd.DataFrame):
    st.subheader("Explore Reviews")
    if df.empty:
        st.info("No data to explore.")
        return

    cols = df.columns
    c1, c2, c3 = st.columns(3)
    filtered = df.copy()
    with c1:
        if "rating" in cols:
            rmin = float(np.nanmin(df["rating"])) if df["rating"].notna().any() else 0.0
            rmax = float(np.nanmax(df["rating"])) if df["rating"].notna().any() else 5.0
            rsel = st.slider("Rating", min_value=float(np.floor(rmin)), max_value=float(np.ceil(rmax)), value=(float(np.floor(rmin)), float(np.ceil(rmax))), step=0.5)
            filtered = filtered[filtered["rating"].between(rsel[0], rsel[1])]
    with c2:
        if "sentiment_label" in cols:
            labs = st.multiselect("Sentiment Label", sorted(df["sentiment_label"].dropna().unique().tolist()))
            if labs:
                filtered = filtered[filtered["sentiment_label"].isin(labs)]
    with c3:
        if "topic_id" in cols:
            topics = [int(t) for t in sorted(pd.unique(df["topic_id"].dropna()))]
            sel = st.multiselect("Topic ID", topics)
            if sel:
                filtered = filtered[filtered["topic_id"].isin(sel)]

    q = st.text_input("Search for keywords")
    if q:
        ql = q.lower()
        filtered = filtered[filtered.get("review_text","").astype(str).str.lower().str.contains(ql, na=False)]

    st.caption(f"Showing {len(filtered):,} reviews")
    show_cols = [c for c in ["review_text","rating","sentiment","sentiment_label","topic_id"] if c in filtered.columns]
    st.dataframe(filtered[show_cols].head(500), use_container_width=True, hide_index=True)


def main():
    base = Path(os.getcwd())
    data = load_all_data(base)

    with st.sidebar:
        st.title("Cruise Reviews Insights")
        st.caption("Interactive summary of reviews, topics, and actions.")
        page = st.radio(
            "Navigate",
            options=["Overview","Topics","Drivers","Recommendations","Explore"],
            index=0,
        )
        st.markdown("Data Sources")
        st.caption(str((base / "outputs" / "master_with_topics.csv").resolve()))

    if page == "Overview":
        overview_tab(data["df"])
    elif page == "Topics":
        topics_tab(data["df"], data["topic_summary"], data["topic_top_words"])
    elif page == "Drivers":
        drivers_tab(data["aspect_drivers"])
    elif page == "Recommendations":
        recs_tab(data["recommendations"], data["impact_estimates"])
    else:
        explore_tab(data["df"])


if __name__ == "__main__":
    main()
