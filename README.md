# 📊 TikTok OFM Strategic Analyzer

Dashboard professionale per l'analisi strategica di profili TikTok, ottimizzata per la nicchia **OnlyFans Management (OFM)**.

## 🌟 Features

- **🔧 Setup No-Code**: Configurazione semplice via sidebar con salvataggio in session state
- **📡 Data Fetching Cloud**: Utilizza Apify API per scaricare dati TikTok (no Selenium/Playwright locale)
- **📈 Metriche OFM**: Viral Ratio, Conversion Potential, Engagement Rate, Trend Analysis
- **🤖 AI Consultant**: Analisi strategica powered by Google Gemini Pro
- **📊 Visualizzazioni**: Grafici interattivi con Plotly
- **☁️ Cloud Native**: Pronto per deploy su Streamlit Community Cloud

## 🚀 Deploy su Streamlit Cloud

### Step 1: Prepara il Repository GitHub

1. Crea un nuovo repository su GitHub
2. Carica questi file:
   - `app.py` (codice principale)
   - `requirements.txt` (dipendenze)
   - `README.md` (questo file)

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TUO_USERNAME/tiktok-ofm-analyzer.git
git push -u origin main
```

### Step 2: Deploy su Streamlit Cloud

1. Vai su [share.streamlit.io](https://share.streamlit.io)
2. Accedi con il tuo account GitHub
3. Clicca **"New app"**
4. Seleziona il repository
5. Configura:
   - **Main file path**: `app.py`
   - **Python version**: 3.9+
6. Clicca **"Deploy"**

### Step 3: Ottieni le API Key

**Apify API Key:**
1. Registrati su [apify.com](https://apify.com)
2. Vai su **Account → Integrations**
3. Copia la tua API Key

**Gemini API Key:**
1. Vai su [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Clicca **"Create API Key"**
3. Copia la chiave generata

## 📋 Come Usare

1. Inserisci le API Key nella sidebar
2. Inserisci lo username TikTok da analizzare (senza @)
3. Clicca **"🚀 Analizza Profilo"**
4. Visualizza:
   - Metriche chiave (Views, Engagement, Viral Ratio)
   - Grafico andamento views
   - Top 3 vs Flop 3 video
   - Analisi AI di Gemini
   - Tabella dati completa con download CSV

## 🏗️ Architettura

```
┌─────────────────┐
│  Streamlit UI   │  ← Frontend (Cloud)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐  ┌──▼────┐
│ Apify │  │ Gemini│  ← Data & AI Backend
│ API   │  │ Pro   │
└───┬───┘  └──┬────┘
    │         │
    └────┬────┘
         │
    ┌────▼────┐
    │ TikTok  │  ← Data Source
    │ Profile │
    └─────────┘
```

## 🔒 Sicurezza

- Le API Key sono salvate in `st.session_state` (solo lato client, per sessione)
- Nessuna chiave viene salvata permanentemente
- Utilizzo di `type="password"` per mascherare le input

## 📊 Metriche Calcolate

| Metrica | Descrizione | Uso OFM |
|---------|-------------|---------|
| **Viral Ratio** | Shares / Likes | Indica potenziale di virality organica |
| **Conversion Potential** | (Shares×2 + Comments) / Views | Misura qualità engagement per conversioni |
| **Engagement Rate** | (Likes+Shares+Comments) / Views | Performance generale contenuto |
| **Trend** | Variazione ultimi vs precedenti | Rileva shadowban o crescita |

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **Data Backend**: Apify Client (`clockworks/tiktok-profile-scraper`)
- **AI**: Google Gemini Pro
- **Visualizzazione**: Plotly
- **Data Processing**: Pandas

## 📄 License

MIT License - Free for personal and commercial use.

---

**Made with ❤️ for OFM Professionals**
