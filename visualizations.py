import plotly.express as px
import pandas as pd
import json
import requests
import streamlit as st

# GeoJSON for Mexico
# Using a reliable public source or cache. 
# Cached version logic would be better but for scratch we use URL
GEOJSON_URL = "https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json"

@st.cache_data
def load_geojson():
    try:
        r = requests.get(GEOJSON_URL)
        return r.json()
    except:
        return None

# Executive Color Palette
COLORS = {
    "Riesgo": {"Alto": "#B91C1C", "Medio": "#D97706", "Bajo": "#059669"}, # Red, Amber, Emerald (Darker/Pro)
    "Estatus": {"Abierto": "#DC2626", "En Proceso": "#F59E0B", "Cerrado": "#10B981"}
}

def plot_kpis_risk(df):
    if df.empty: return None, None, None

    # --- 1. Riesgo (Donut Chart Professional) ---
    riesgo_counts = df['riesgo'].value_counts().reset_index()
    riesgo_counts.columns = ['riesgo', 'count']
    
    fig_risk = px.pie(
        riesgo_counts, values='count', names='riesgo', 
        title="<b>Nivel de Riesgo</b>",
        color='riesgo',
        color_discrete_map=COLORS["Riesgo"],
        hole=0.6 # Thinner donut looks more modern
    )
    fig_risk.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig_risk.update_traces(textinfo='percent', textfont_size=14)

    # --- 2. Estatus (Clean Bar) ---
    estatus_counts = df['estatus'].value_counts().reset_index()
    estatus_counts.columns = ['estatus', 'count']
    
    fig_status = px.bar(
        estatus_counts, x='count', y='estatus', orientation='h',
        title="<b>Estatus de Cumplimiento</b>", 
        color='estatus',
        color_discrete_map=COLORS["Estatus"],
        text='count'
    )
    fig_status.update_layout(
        xaxis_title="", yaxis_title="", 
        showlegend=False, 
        plot_bgcolor='rgba(0,0,0,0)'
    )
    fig_status.update_traces(textposition='outside')

    # --- 3. Mapa (O Barras Estado si falla) ---
    fig_map = None
    if 'estado_geo' in df.columns:
        state_counts = df['estado_geo'].value_counts().reset_index()
        state_counts.columns = ['name', 'count']
        
        geojson = load_geojson()
        if geojson:
            fig_map = px.choropleth(
                state_counts,
                geojson=geojson,
                locations='name',
                featureidkey="properties.name",
                color='count',
                color_continuous_scale="Reds",
                title="<b>Distribución Geográfica</b>",
                scope="north america"
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
        else:
            # Fallback elegante
            fig_map = px.bar(
                state_counts.head(10), x='name', y='count', 
                title="<b>Hallazgos por Estado (Top 10)</b>",
                color='count', color_continuous_scale="Blues"
            )
            fig_map.update_layout(plot_bgcolor='rgba(0,0,0,0)')

    return fig_risk, fig_status, fig_map

def plot_gantt(df):
    if df.empty: return None
    
    # Sort by date for waterfall effect
    df = df.sort_values("fecha_hallazgo", ascending=False)
    
    fig = px.timeline(
        df, x_start="fecha_hallazgo", x_end="fecha_compromiso", y="hallazgo",
        color="estatus",
        hover_data=["cedis", "responsable"],
        color_discrete_map=COLORS["Estatus"],
        title="<b>Cronograma de Actividades</b>"
    )
    
    fig.update_yaxes(visible=False) # Hide y labels if too many findings make it cluttered
    fig.update_layout(
        xaxis_title="Línea de Tiempo",
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig
