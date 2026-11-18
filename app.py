import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Coffee Roasters | Sales Dashboard", page_icon="☕", layout="wide")

st.title("☕ Afficionado Coffee Roasters")
st.subheader("Sales Trend & Time-Based Performance Dashboard")

@st.cache_data
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)

    candidates = [
        Path("afficionade coffee rosters.xlsx"),
        Path("afficionado coffee roasters.xlsx"),
        Path("afficionade coffee roasters.xlsx"),
        Path("afficionado coffee rosters.xlsx"),
    ]
    for file_path in candidates:
        if file_path.exists():
            return pd.read_excel(file_path)

    excel_files = list(Path(".").glob("*.xlsx")) + list(Path(".").glob("*.xls"))
    if excel_files:
        return pd.read_excel(excel_files[0])
    return None

uploaded = st.sidebar.file_uploader("Upload your Sales Excel dataset", type=["xlsx", "xls"])
df = load_data(uploaded)

if df is None:
    st.info("Please keep your Sales Excel file in the same folder as app.py, or upload it using the sidebar.")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
df = df.dropna(how="all").copy()

# Identify common columns in the Coffee Shop Sales dataset
def find_col(options):
    lower_map = {str(c).lower().strip(): c for c in df.columns}
    for option in options:
        if option in lower_map:
            return lower_map[option]
    for c in df.columns:
        name = str(c).lower().replace(" ", "_")
        if any(option in name for option in options):
            return c
    return None

date_col = find_col(["transaction_date", "date", "order_date"])
time_col = find_col(["transaction_time", "time", "order_time"])
sales_col = find_col(["sales", "revenue", "total_amount", "amount"])
qty_col = find_col(["transaction_qty", "quantity", "qty"])
price_col = find_col(["unit_price", "price"])
product_col = find_col(["product_type", "product_category", "product_detail", "product", "item"])
location_col = find_col(["store_location", "store", "location"])
category_col = find_col(["product_category", "category"])

if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=False)

if sales_col:
    df["_sales"] = pd.to_numeric(df[sales_col], errors="coerce")
elif qty_col and price_col:
    df["_sales"] = pd.to_numeric(df[qty_col], errors="coerce") * pd.to_numeric(df[price_col], errors="coerce")
else:
    df["_sales"] = pd.NA

if qty_col:
    df["_quantity"] = pd.to_numeric(df[qty_col], errors="coerce")
else:
    df["_quantity"] = 1

# Sidebar date filter
filtered = df.copy()
if date_col and df[date_col].notna().any():
    min_date = df[date_col].min().date()
    max_date = df[date_col].max().date()
    selected_dates = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start, end = selected_dates
        filtered = filtered[(filtered[date_col].dt.date >= start) & (filtered[date_col].dt.date <= end)]

if location_col:
    locations = sorted(filtered[location_col].dropna().astype(str).unique())
    chosen_locations = st.sidebar.multiselect("Store location", locations, default=locations)
    if chosen_locations:
        filtered = filtered[filtered[location_col].astype(str).isin(chosen_locations)]

# KPI cards
c1, c2, c3, c4 = st.columns(4)
total_sales = pd.to_numeric(filtered["_sales"], errors="coerce").sum()
total_orders = len(filtered)
total_qty = pd.to_numeric(filtered["_quantity"], errors="coerce").sum()
avg_sale = total_sales / total_orders if total_orders else 0

c1.metric("Total Sales", f"{total_sales:,.2f}" if pd.notna(total_sales) else "N/A")
c2.metric("Transactions", f"{total_orders:,}")
c3.metric("Quantity Sold", f"{total_qty:,.0f}" if pd.notna(total_qty) else "N/A")
c4.metric("Average Sales / Transaction", f"{avg_sale:,.2f}" if pd.notna(avg_sale) else "N/A")

st.divider()

# Trend chart
left, right = st.columns(2)
with left:
    st.markdown("### 📈 Sales Trend Over Time")
    if date_col and filtered[date_col].notna().any() and filtered["_sales"].notna().any():
        trend = filtered.dropna(subset=[date_col]).copy()
        trend["_period"] = trend[date_col].dt.to_period("M").astype(str)
        trend_data = trend.groupby("_period", as_index=False)["_sales"].sum()
        fig = px.line(trend_data, x="_period", y="_sales", markers=True, labels={"_period": "Month", "_sales": "Sales"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("A usable date and sales/price column was not detected.")

with right:
    st.markdown("### 🏆 Top Products")
    if product_col:
        product_data = filtered.groupby(product_col, dropna=True)["_quantity"].sum().reset_index().sort_values("_quantity", ascending=False).head(10)
        fig = px.bar(product_data, x="_quantity", y=product_col, orientation="h", labels={"_quantity": "Quantity Sold", product_col: "Product"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Product column not detected in this dataset.")

# Time analysis
st.markdown("### 🕒 Time-Based Performance")
t1, t2 = st.columns(2)
with t1:
    if time_col:
        times = pd.to_datetime(filtered[time_col].astype(str), errors="coerce")
        hourly = times.dt.hour.value_counts().sort_index().rename_axis("Hour").reset_index(name="Transactions")
        fig = px.bar(hourly, x="Hour", y="Transactions", labels={"Hour": "Hour of Day"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Transaction time column not detected.")

with t2:
    if date_col and filtered[date_col].notna().any():
        weekday_data = filtered.copy()
        weekday_data["Day"] = weekday_data[date_col].dt.day_name()
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_summary = weekday_data.groupby("Day").size().reindex(order).fillna(0).reset_index(name="Transactions")
        fig = px.bar(day_summary, x="Day", y="Transactions", labels={"Transactions": "Transactions"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Date column not detected for weekday analysis.")

# Store comparison
if location_col and filtered["_sales"].notna().any():
    st.markdown("### 📍 Store Location Performance")
    store_data = filtered.groupby(location_col)["_sales"].sum().reset_index().sort_values("_sales", ascending=False)
    fig = px.bar(store_data, x=location_col, y="_sales", labels={"_sales": "Sales", location_col: "Store"})
    st.plotly_chart(fig, use_container_width=True)

with st.expander("View dataset and detected columns"):
    st.write("Detected columns:", {
        "Date": date_col, "Time": time_col, "Sales": sales_col,
        "Quantity": qty_col, "Unit price": price_col,
        "Product": product_col, "Store location": location_col
    })
    st.dataframe(filtered.drop(columns=["_sales", "_quantity"], errors="ignore"), use_container_width=True)

st.caption("Dashboard generated from the supplied Excel dataset. Check the detected columns and metrics before using them in a report.")
