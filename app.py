"""
TikTok OFM Strategic Analyzer
Dashboard per l'analisi strategica di profili TikTok (nicchia OFM)
Deploy: Streamlit Community Cloud
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from apify_client import ApifyClient
import google.generativeai as genai
from datetime import datetime
import json

# ============================================
# CONFIGURAZIONE PAGINA
# ============================================
st.set_page_config(
    page_title="TikTok OFM Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# INIZIALIZZAZIONE SESSION STATE
# ============================================
def init_session_state():
    """Inizializza le variabili di sessione"""
    if 'apify_key' not in st.session_state:
        st.session_state.apify_key = ""
    if 'gemini_key' not in st.session_state:
        st.session_state.gemini_key = ""
    if 'tiktok_username' not in st.session_state:
        st.session_state.tiktok_username = ""
    if 'df_videos' not in st.session_state:
        st.session_state.df_videos = None
    if 'analysis_done' not in st.session_state:
        st.session_state.analysis_done = False
    if 'gemini_analysis' not in st.session_state:
        st.session_state.gemini_analysis = None

init_session_state()

# ============================================
# SIDEBAR - CONFIGURAZIONE
# ============================================
st.sidebar.title("🔧 Configurazione")
st.sidebar.markdown("---")

# Input API Keys (salvati in session_state)
st.session_state.apify_key = st.sidebar.text_input(
    "🔑 Apify API Key",
    value=st.session_state.apify_key,
    type="password",
    placeholder="apify_api_xxxxxxxx...",
    help="Trova la tua chiave su: https://console.apify.com/account/integrations"
)

st.session_state.gemini_key = st.sidebar.text_input(
    "🔑 Gemini API Key",
    value=st.session_state.gemini_key,
    type="password",
    placeholder="AIzaSy...",
    help="Ottieni la chiave su: https://makersuite.google.com/app/apikey"
)

st.sidebar.markdown("---")

# Input Target Username
st.session_state.tiktok_username = st.sidebar.text_input(
    "👤 TikTok Username Target",
    value=st.session_state.tiktok_username,
    placeholder="es. charlidamelio",
    help="Inserisci lo username senza @"
).replace("@", "").strip()

st.sidebar.markdown("---")

# Pulsante Analisi
analyze_button = st.sidebar.button(
    "🚀 Analizza Profilo",
    type="primary",
    use_container_width=True,
    disabled=not (st.session_state.apify_key and st.session_state.gemini_key and st.session_state.tiktok_username)
)

# Info Sidebar
st.sidebar.markdown("---")
st.sidebar.info("""
**📋 Come ottenere le API Key:**

**Apify:**
1. Registrati su [apify.com](https://apify.com)
2. Vai su Account → Integrations
3. Copia la tua API Key

**Gemini:**
1. Vai su [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crea una nuova API Key
3. Copia la chiave generata
""")

# ============================================
# FUNZIONI DI FETCHING DATI (Apify)
# ============================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tiktok_data(apify_key: str, username: str) -> list:
    """
    Scarica i dati del profilo TikTok usando Apify API.
    Utilizza l'actor clockworks/tiktok-profile-scraper
    """
    try:
        client = ApifyClient(apify_key)
        
        # Configurazione dell'actor per lo scraping del profilo
        run_input = {
            "profiles": [username],
            "resultsPerPage": 30,  # Ultimi 30 video
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False
        }
        
        # Esegui l'actor
        with st.spinner("🔄 Connessione ad Apify in corso..."):
            run = client.actor("clockworks/tiktok-profile-scraper").call(run_input=run_input)
        
        # Recupera i risultati
        with st.spinner("📥 Download dati in corso..."):
            dataset_items = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                dataset_items.append(item)
        
        return dataset_items
        
    except Exception as e:
        st.error(f"❌ Errore durante il fetch da Apify: {str(e)}")
        return []

def parse_apify_data(raw_data: list) -> pd.DataFrame:
    """
    Converte i dati grezzi di Apify in un DataFrame Pandas pulito.
    Estrae i campi rilevanti per l'analisi OFM.
    Supporta multipli formati di risposta.
    """
    if not raw_data:
        return pd.DataFrame()
    
    # DEBUG: Mostra struttura primo elemento per diagnosticare
    if len(raw_data) > 0:
        st.write("🔍 Debug - Struttura dati ricevuti (primo elemento):")
        st.json(raw_data[0])
    
    videos = []
    
    for item in raw_data:
        # Prova diversi formati di risposta
        
        # Formato 1: Dati diretti (item è il video)
        if "playCount" in item or "stats" in item:
            video_data = item
            stats = item.get("stats", item)  # Se stats non esiste, usa item diretto
            author_data = item.get("author", {})
        
        # Formato 2: Dati annidati in "video"
        elif "video" in item:
            video_data = item.get("video", {})
            stats = video_data.get("stats", {})
            author_data = item.get("author", {})
        
        # Formato 3: Dati in formato diverso (prova a cercare chiavi comuni)
        else:
            # Cerca chiavi in modo flessibile
            video_data = item
            stats = item
            author_data = item.get("author", item.get("authorStats", {}))
        
        # Estrazione campi con gestione multipla nomi
        def get_value(obj, keys, default=0):
            """Cerca il valore tra più chiavi possibili"""
            for key in keys:
                if isinstance(obj, dict) and key in obj:
                    val = obj[key]
                    return val if val is not None else default
            return default
        
        video_info = {
            "id": get_value(video_data, ["id", "videoId", "awemeId"], ""),
            "text": get_value(video_data, ["desc", "description", "text", "caption"], ""),
            "createTime": get_value(video_data, ["createTime", "create_time", "createDate"], 0),
            "createDate": "",
            "duration": get_value(video_data.get("video", {}), ["duration"], 0) if isinstance(video_data.get("video"), dict) else 0,
            "playCount": get_value(stats, ["playCount", "play_count", "viewCount", "views", "statsV2.playCount"], 0),
            "diggCount": get_value(stats, ["diggCount", "digg_count", "likeCount", "likes", "statsV2.diggCount"], 0),
            "shareCount": get_value(stats, ["shareCount", "share_count", "shares", "statsV2.shareCount"], 0),
            "commentCount": get_value(stats, ["commentCount", "comment_count", "comments", "statsV2.commentCount"], 0),
            "collectCount": get_value(stats, ["collectCount", "collect_count", "collects", "statsV2.collectCount"], 0),
            "authorUsername": get_value(author_data, ["uniqueId", "unique_id", "username", "nickname"], ""),
            "authorNickname": get_value(author_data, ["nickname", "nickName", "displayName"], ""),
            "authorFollowers": get_value(author_data.get("stats", {}), ["followerCount", "follower_count", "followers"], 0),
        }
        
        # Converte createTime in data leggibile
        if video_info["createTime"]:
            try:
                # Prova formato timestamp
                if isinstance(video_info["createTime"], (int, float)) and video_info["createTime"] > 1000000000:
                    video_info["createDate"] = datetime.fromtimestamp(video_info["createTime"]).strftime("%Y-%m-%d %H:%M")
                # Prova formato stringa
                elif isinstance(video_info["createTime"], str):
                    video_info["createDate"] = video_info["createTime"]
            except:
                video_info["createDate"] = str(video_info["createTime"])
        
        videos.append(video_info)
    
    df = pd.DataFrame(videos)
    
    # DEBUG: Mostra DataFrame creato
    st.write(f"🔍 Debug - DataFrame creato con {len(df)} righe")
    if not df.empty:
        st.write("Prime righe:", df.head())
    
    # Ordina per data di creazione (più recenti prima)
    if not df.empty and "createTime" in df.columns:
        df = df.sort_values("createTime", ascending=False).reset_index(drop=True)
    
    return df

def calculate_metrics(df: pd.DataFrame) -> dict:
    """
    Calcola le metriche chiave per l'analisi OFM.
    """
    if df.empty:
        return {}
    
    metrics = {
        "total_videos": len(df),
        "avg_views": df["playCount"].mean(),
        "avg_likes": df["diggCount"].mean(),
        "avg_shares": df["shareCount"].mean(),
        "avg_comments": df["commentCount"].mean(),
        "total_views": df["playCount"].sum(),
        "total_engagement": (df["diggCount"] + df["shareCount"] + df["commentCount"]).sum(),
    }
    
    # Viral Ratio (Shares/Likes) - indica potenziale di virality
    df["viralRatio"] = df.apply(
        lambda row: row["shareCount"] / row["diggCount"] if row["diggCount"] > 0 else 0,
        axis=1
    )
    metrics["avg_viral_ratio"] = df["viralRatio"].mean()
    
    # Engagement Rate
    df["engagementRate"] = df.apply(
        lambda row: ((row["diggCount"] + row["shareCount"] + row["commentCount"]) / row["playCount"] * 100)
        if row["playCount"] > 0 else 0,
        axis=1
    )
    metrics["avg_engagement_rate"] = df["engagementRate"].mean()
    
    # Conversion Potential (Views vs Engagement quality)
    df["conversionPotential"] = df.apply(
        lambda row: (row["shareCount"] * 2 + row["commentCount"]) / row["playCount"] * 100
        if row["playCount"] > 0 else 0,
        axis=1
    )
    metrics["avg_conversion_potential"] = df["conversionPotential"].mean()
    
    # Top 3 e Flop 3 video
    metrics["top3"] = df.nlargest(3, "playCount").to_dict("records")
    metrics["flop3"] = df.nsmallest(3, "playCount").to_dict("records")
    
    # Trend analysis (ultimi 10 vs primi 10)
    if len(df) >= 20:
        recent_10 = df.head(10)["playCount"].mean()
        older_10 = df.tail(10)["playCount"].mean()
        metrics["trend"] = ((recent_10 - older_10) / older_10 * 100) if older_10 > 0 else 0
    else:
        metrics["trend"] = 0
    
    return metrics

# ============================================
# FUNZIONI GEMINI AI
# ============================================
def get_gemini_analysis(df: pd.DataFrame, metrics: dict, username: str) -> str:
    """
    Genera l'analisi strategica usando Gemini Pro.
    """
    try:
        # Configura Gemini
        genai.configure(api_key=st.session_state.gemini_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        # Prepara i dati aggregati
        data_summary = {
            "username": username,
            "total_videos_analyzed": metrics.get("total_videos", 0),
            "avg_views": round(metrics.get("avg_views", 0), 2),
            "avg_likes": round(metrics.get("avg_likes", 0), 2),
            "avg_shares": round(metrics.get("avg_shares", 0), 2),
            "avg_comments": round(metrics.get("avg_comments", 0), 2),
            "avg_engagement_rate": round(metrics.get("avg_engagement_rate", 2), 2),
            "avg_viral_ratio": round(metrics.get("avg_viral_ratio", 4), 4),
            "trend_percentage": round(metrics.get("trend", 2), 2),
        }
        
        # Top 3 video
        top3_summary = []
        for i, video in enumerate(metrics.get("top3", []), 1):
            top3_summary.append({
                "rank": i,
                "views": video.get("playCount", 0),
                "likes": video.get("diggCount", 0),
                "shares": video.get("shareCount", 0),
                "comments": video.get("commentCount", 0),
                "text_preview": video.get("text", "")[:100],
                "duration_sec": video.get("duration", 0),
                "date": video.get("createDate", "")
            })
        
        # Flop 3 video
        flop3_summary = []
        for i, video in enumerate(metrics.get("flop3", []), 1):
            flop3_summary.append({
                "rank": i,
                "views": video.get("playCount", 0),
                "likes": video.get("diggCount", 0),
                "shares": video.get("shareCount", 0),
                "comments": video.get("commentCount", 0),
                "text_preview": video.get("text", "")[:100],
                "duration_sec": video.get("duration", 0),
                "date": video.get("createDate", "")
            })
        
        # Costruisci il prompt
        prompt = f"""Sei un Growth Manager esperto per creator OnlyFans. Analizza i dati di questo account TikTok.

## OBIETTIVO
L'obiettivo è spostare traffico qualificato su Instagram/Link in bio per conversioni OFM.

## DATI AGGREGATI
{json.dumps(data_summary, indent=2)}

## TOP 3 VIDEO (Migliori Performance)
{json.dumps(top3_summary, indent=2)}

## FLOP 3 VIDEO (Peggiori Performance)
{json.dumps(flop3_summary, indent=2)}

## ANALISI RICHIESTA

1. **SHADOWBAN CHECK**: C'è un problema di shadowban? Analizza se ci sono crolli improvvisi nelle views (trend: {metrics.get('trend', 0):.1f}%).

2. **AUDIENCE QUALITY**: I video stanno attirando il pubblico giusto (USA/Male/18-35) o sono solo virali a caso? Basati sul rapporto shares/likes e commenti.

3. **CONTENT PATTERN**: Cosa hanno in comune i top 3 vs flop 3? (lunghezza, hook, tipo di contenuto)

4. **3 CONSIGLI OPERATIVI**: Dammi 3 consigli secchi e actionable per la prossima settimana su:
   - Audio/Trend da usare
   - Lunghezza ottimale video
   - Hook visivi che convertono

Rispondi in italiano, in modo diretto e professionale."""
        
        with st.spinner("🤖 Gemini sta analizzando i dati..."):
            response = model.generate_content(prompt)
            return response.text
            
    except Exception as e:
        return f"❌ Errore durante l'analisi Gemini: {str(e)}"

# ============================================
# MAIN DASHBOARD
# ============================================
st.title("📊 TikTok OFM Strategic Analyzer")
st.markdown("*Dashboard professionale per l'analisi strategica di profili TikTok - Nicchia OnlyFans Management*")
st.markdown("---")

# Gestione del bottone Analizza
if analyze_button:
    if not st.session_state.apify_key or not st.session_state.gemini_key or not st.session_state.tiktok_username:
        st.warning("⚠️ Inserisci tutte le API Key e lo username prima di procedere.")
    else:
        # Fetch dati da Apify
        raw_data = fetch_tiktok_data(st.session_state.apify_key, st.session_state.tiktok_username)
        
        if raw_data:
            # Parsing dati
            df = parse_apify_data(raw_data)
            
            if not df.empty:
                st.session_state.df_videos = df
                st.session_state.analysis_done = True
                
                # Calcola metriche
                metrics = calculate_metrics(df)
                st.session_state.metrics = metrics
                
                # Analisi Gemini
                gemini_result = get_gemini_analysis(df, metrics, st.session_state.tiktok_username)
                st.session_state.gemini_analysis = gemini_result
                
                st.success(f"✅ Analisi completata! Trovati {len(df)} video per @{st.session_state.tiktok_username}")
            else:
                st.error("❌ Nessun video trovato per questo username.")
        else:
            st.error("❌ Impossibile recuperare i dati. Verifica le API Key e lo username.")

# Visualizzazione Dashboard
if st.session_state.analysis_done and st.session_state.df_videos is not None:
    df = st.session_state.df_videos
    metrics = st.session_state.metrics
    
    # ============================================
    # SEZIONE 1: METRICHE CHIAVE
    # ============================================
    st.header("📈 Metriche Chiave")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="🎥 Video Analizzati",
            value=f"{metrics.get('total_videos', 0)}"
        )
    
    with col2:
        st.metric(
            label="👁️ Media Views",
            value=f"{metrics.get('avg_views', 0):,.0f}"
        )
    
    with col3:
        st.metric(
            label="📊 Engagement Rate",
            value=f"{metrics.get('avg_engagement_rate', 0):.2f}%"
        )
    
    with col4:
        st.metric(
            label="🚀 Viral Ratio",
            value=f"{metrics.get('avg_viral_ratio', 0):.4f}"
        )
    
    with col5:
        trend_value = metrics.get('trend', 0)
        trend_delta = f"{trend_value:+.1f}%"
        st.metric(
            label="📉 Trend (Ultimi vs Precedenti)",
            value=trend_delta,
            delta=trend_delta
        )
    
    st.markdown("---")
    
    # ============================================
    # SEZIONE 2: GRAFICI
    # ============================================
    st.header("📊 Visualizzazioni")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("👁️ Andamento Views - Ultimi 30 Video")
        
        # Prepara dati per il grafico (ordine cronologico)
        df_chart = df.sort_values("createTime", ascending=True).reset_index(drop=True)
        df_chart["video_num"] = range(1, len(df_chart) + 1)
        
        fig_views = go.Figure()
        fig_views.add_trace(go.Scatter(
            x=df_chart["video_num"],
            y=df_chart["playCount"],
            mode='lines+markers',
            name='Views',
            line=dict(color='#FF0050', width=2),
            marker=dict(size=8)
        ))
        
        fig_views.update_layout(
            xaxis_title="Video # (dal più vecchio al più recente)",
            yaxis_title="Views",
            height=400,
            showlegend=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_views, use_container_width=True)
    
    with col_chart2:
        st.subheader("📊 Engagement Breakdown")
        
        # Media engagement per tipo
        engagement_data = {
            'Metrica': ['Likes', 'Shares', 'Comments'],
            'Media': [
                metrics.get('avg_likes', 0),
                metrics.get('avg_shares', 0),
                metrics.get('avg_comments', 0)
            ]
        }
        df_engagement = pd.DataFrame(engagement_data)
        
        fig_engagement = px.bar(
            df_engagement,
            x='Metrica',
            y='Media',
            color='Metrica',
            color_discrete_map={
                'Likes': '#FF0050',
                'Shares': '#00F2EA',
                'Comments': '#000000'
            }
        )
        fig_engagement.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_engagement, use_container_width=True)
    
    st.markdown("---")
    
    # ============================================
    # SEZIONE 3: TOP 3 E FLOP 3
    # ============================================
    st.header("🏆 Top 3 vs Flop 3 Video")
    
    col_top, col_flop = st.columns(2)
    
    with col_top:
        st.subheader("🥇 Top 3 Video")
        for i, video in enumerate(metrics.get("top3", []), 1):
            with st.container():
                st.markdown(f"**#{i}** - {video.get('createDate', 'N/A')}")
                st.markdown(f"📝 *{video.get('text', 'No caption')[:80]}...*")
                cols = st.columns(4)
                cols[0].metric("Views", f"{video.get('playCount', 0):,}")
                cols[1].metric("Likes", f"{video.get('diggCount', 0):,}")
                cols[2].metric("Shares", f"{video.get('shareCount', 0):,}")
                cols[3].metric("Durata", f"{video.get('duration', 0)}s")
                st.markdown("---")
    
    with col_flop:
        st.subheader("📉 Flop 3 Video")
        for i, video in enumerate(metrics.get("flop3", []), 1):
            with st.container():
                st.markdown(f"**#{i}** - {video.get('createDate', 'N/A')}")
                st.markdown(f"📝 *{video.get('text', 'No caption')[:80]}...*")
                cols = st.columns(4)
                cols[0].metric("Views", f"{video.get('playCount', 0):,}")
                cols[1].metric("Likes", f"{video.get('diggCount', 0):,}")
                cols[2].metric("Shares", f"{video.get('shareCount', 0):,}")
                cols[3].metric("Durata", f"{video.get('duration', 0)}s")
                st.markdown("---")
    
    # ============================================
    # SEZIONE 4: GEMINI CONSULTANT
    # ============================================
    st.header("🤖 Gemini AI Consultant")
    
    if st.session_state.gemini_analysis:
        st.markdown(st.session_state.gemini_analysis)
    else:
        st.info("🤖 L'analisi AI non è disponibile. Clicca 'Analizza Profilo' per generarla.")
    
    st.markdown("---")
    
    # ============================================
    # SEZIONE 5: TABELLA DATI COMPLETA
    # ============================================
    st.header("📋 Dati Completi")
    
    with st.expander("Visualizza tutti i dati scaricati"):
        # Seleziona colonne rilevanti per la visualizzazione
        display_cols = ["createDate", "text", "playCount", "diggCount", "shareCount", "commentCount", "duration", "viralRatio", "engagementRate"]
        df_display = df[display_cols].copy()
        df_display.columns = ["Data", "Testo", "Views", "Likes", "Shares", "Comments", "Durata(s)", "Viral Ratio", "Engagement %"]
        st.dataframe(df_display, use_container_width=True)
        
        # Download CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Scarica CSV",
            data=csv,
            file_name=f"tiktok_analysis_{st.session_state.tiktok_username}.csv",
            mime="text/csv"
        )

else:
    # Stato iniziale - nessuna analisi
    st.info("""
    👋 **Benvenuto in TikTok OFM Analyzer!**
    
    Per iniziare l'analisi:
    1. Inserisci la tua **Apify API Key** nella sidebar
    2. Inserisci la tua **Gemini API Key** nella sidebar  
    3. Inserisci lo **username TikTok** da analizzare
    4. Clicca su **"🚀 Analizza Profilo"**
    
    L'app scaricherà gli ultimi 30 video, calcolerà le metriche chiave e genererà un report AI personalizzato.
    """)
    
    # Placeholder dashboard
    col1, col2, col3 = st.columns(3)
    col1.metric("🎥 Video Analizzati", "-", help="Numero di video analizzati")
    col2.metric("👁️ Media Views", "-", help="Media views per video")
    col3.metric("📊 Engagement Rate", "-", help="Tasso di engagement medio")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>🔒 TikTok OFM Analyzer - Cloud Native App | Powered by Apify + Gemini + Streamlit</small>
</div>
""", unsafe_allow_html=True)