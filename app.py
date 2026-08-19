import sys
import asyncio

# Prevent Windows ProactorEventLoop connection reset errors
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from analysis import load_and_clean_data

# --- Page Configuration ---
st.set_page_config(
    page_title="Fashion Up - Inventory Analytics",
    page_icon="assets/logo.png",
    layout="wide"
)

LOGO_PATH = "assets/logo.png"
DEFAULT_DATA_PATH = "data/ACUTE SHORTAGE_18 AUG 2026.xlsx"

# --- Sidebar: Logo & Daily File Uploader ---
try:
    st.sidebar.image(LOGO_PATH, width=220)
except Exception:
    pass

st.sidebar.title("Data Input & Controls")

uploaded_file = st.sidebar.file_uploader(
    "📤 Upload Today's Stock Report (Excel)",
    type=["xlsx", "xls"]
)

# Load data dynamically
try:
    if uploaded_file is not None:
        df = load_and_clean_data(uploaded_file)
        st.sidebar.success("Loaded uploaded daily file!")
    else:
        df = load_and_clean_data(DEFAULT_DATA_PATH)
except Exception as e:
    st.error(f"Error loading data file: {e}")
    st.stop()

# --- Main Dashboard Header ---
header_col1, header_col2 = st.columns([1, 4])

with header_col1:
    try:
        st.image(LOGO_PATH, width=180)
    except Exception:
        pass

with header_col2:
    st.title("Inventory & Stock S/E Optimization Dashboard")
    st.caption("Daily Retail Stock Run-out, Acute Shortage & Supply Chain Analytics")

st.divider()

# --- Sidebar Slicers ---
st.sidebar.subheader("🎯 Filter Options")

categories = st.sidebar.multiselect(
    "Select Category:",
    options=sorted(df['CATEGORY'].dropna().unique()),
    default=sorted(df['CATEGORY'].dropna().unique())
)

all_buckets = [
    '≤ 7 Days', '8 - 14 Days', '15 - 21 Days', '22 - 28 Days',
    '29 - 35 Days', '36 - 42 Days', '43 - 49 Days', '50 - 56 Days',
    '57 - 60 Days', '> 60 Days (or Zero Sales)'
]
selected_buckets = st.sidebar.multiselect(
    "Filter by Days of Inventory (Buckets):",
    options=all_buckets,
    default=all_buckets
)

max_doi_cutoff = st.sidebar.slider(
    "Show SKUs with Days of Inventory ≤ :",
    min_value=7,
    max_value=120,
    value=120,
    step=7
)

# Filter Dataset
filtered_df = df[
    (df['CATEGORY'].isin(categories)) &
    (df['DOI_BUCKET'].isin(selected_buckets)) &
    ((df['DAYS_OF_INVENTORY'] <= max_doi_cutoff) | (df['DAYS_OF_INVENTORY'] == 999))
]

# --- Section 1: Executive KPI Cards ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Target Base Stock", f"{int(filtered_df['BASE STOCK'].sum()):,}")
col2.metric("Total Active Stock", f"{int(filtered_df['TOTAL STK'].sum()):,}")
col3.metric("Total Shortage (S/E QTY)", f"{int(filtered_df['S/E QTY'].sum()):,}")
col4.metric("Pending POs", f"{int(filtered_df['PENDING PO QTY'].sum()):,}")

st.divider()

# --- Section 2: Visualizations Row 1 (Core Shortage & Health) ---
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    shortage_by_cat = filtered_df.groupby('CATEGORY', as_index=False)['S/E QTY'].sum().sort_values(by='S/E QTY', ascending=False)
    fig_shortage = px.bar(
        shortage_by_cat,
        x='CATEGORY',
        y='S/E QTY',
        title="Total Shortage (S/E QTY) by Category",
        text_auto='.2s',
        color='S/E QTY',
        color_continuous_scale='Reds'
    )
    st.plotly_chart(fig_shortage, width='stretch')

with row1_col2:
    doi_dist = filtered_df['DOI_BUCKET'].value_counts().reset_index()
    doi_dist.columns = ['DOI Range', 'SKU Count']
    fig_doi = px.bar(
        doi_dist,
        x='DOI Range',
        y='SKU Count',
        title="SKU Distribution across Days of Inventory",
        color='SKU Count',
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig_doi, width='stretch')

# --- Section 3: Visualizations Row 2 (Pipeline & Price Heatmap) ---
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    # 1. Pipeline Coverage (Shortage vs Warehouse vs Open POs)
    coverage_summary = filtered_df.groupby('CATEGORY')[['S/E QTY', 'WH QT', 'PENDING PO QTY']].sum().reset_index()
    fig_coverage = px.bar(
        coverage_summary,
        x='CATEGORY',
        y=['S/E QTY', 'WH QT', 'PENDING PO QTY'],
        barmode='group',
        title="Shortage vs. Inbound Pipeline Coverage by Category",
        labels={'value': 'Units', 'variable': 'Stock Stream'},
        color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71']
    )
    st.plotly_chart(fig_coverage, width='stretch')

with row2_col2:
    # 2. Price-Band Shortage Heatmap
    fig_heat = px.density_heatmap(
        filtered_df,
        x='RSP RANGE',
        y='CATEGORY',
        z='S/E QTY',
        color_continuous_scale='YlOrRd',
        title="Shortage Intensity Heatmap (Category vs. RSP Bracket)"
    )
    st.plotly_chart(fig_heat, width='stretch')

# --- Section 4: Visualizations Row 3 (Priority Matrix & Fulfillment Stages) ---
row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    # 3. Replenishment Priority Scatter Plot
    fig_scatter = px.scatter(
        filtered_df,
        x='7D SALE',
        y='S/E QTY',
        size='BASE STOCK',
        color='CATEGORY',
        hover_name='DEPARTMENT',
        title="Replenishment Priority Matrix: Sales Velocity vs. Shortage Deficit",
        labels={'7D SALE': '7-Day Sales Units', 'S/E QTY': 'Shortage Quantity'}
    )
    st.plotly_chart(fig_scatter, width='stretch')

with row3_col2:
    # 4. Active Stock Composition (Shelf vs Transit vs Packing)
    stock_breakdown = filtered_df.groupby('CATEGORY')[['STOCK QTY', 'TRANSIT QTY', 'PACK QTY']].sum().reset_index()
    fig_comp = px.bar(
        stock_breakdown,
        y='CATEGORY',
        x=['STOCK QTY', 'TRANSIT QTY', 'PACK QTY'],
        orientation='h',
        title="Active Stock Breakdown (Shelf vs. In-Transit vs. Packed)",
        labels={'value': 'Total Quantity', 'variable': 'Fulfillment Stage'},
        color_discrete_sequence=['#16a085', '#f39c12', '#9b59b6']
    )
    st.plotly_chart(fig_comp, width='stretch')

st.divider()

# --- Section 5: Filtered Data Table ---
st.subheader(f"📋 Detailed Stock Records ({len(filtered_df)} SKUs matching criteria)")

display_cols = [
    'CATEGORY', 'DEPARTMENT', 'RSP RANGE', 'BASE STOCK', 'TOTAL STK',
    '7D SALE', 'DAYS_OF_INVENTORY', 'DOI_BUCKET', 'S/E QTY', 'WH QT', 'PENDING PO QTY'
]

st.dataframe(
    filtered_df[display_cols].sort_values(by='DAYS_OF_INVENTORY', ascending=True).style.format({
        'BASE STOCK': '{:,.0f}',
        'TOTAL STK': '{:,.0f}',
        '7D SALE': '{:,.0f}',
        'DAYS_OF_INVENTORY': '{:,.1f}',
        'S/E QTY': '{:,.0f}',
        'WH QT': '{:,.0f}',
        'PENDING PO QTY': '{:,.0f}'
    }),
    width='stretch'
)