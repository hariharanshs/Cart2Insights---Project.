import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go

username = "root"
password = "1234"
host = "localhost"
port = "3306"
database = "cart2insights"
engine = create_engine(f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}")

st.title("Cart2Insights: E-Commerce Performance Dashboard")
st.header("Business Overview")

total_revenue = pd.read_sql("SELECT SUM(price + freight_value) AS val FROM order_items;", con=engine)['val'][0]
total_orders = pd.read_sql("SELECT COUNT(DISTINCT order_id) AS val FROM orders;", con=engine)['val'][0]
total_customers = pd.read_sql("SELECT COUNT(DISTINCT customer_unique_id) AS val FROM customers;", con=engine)['val'][0]
total_sellers = pd.read_sql("SELECT COUNT(DISTINCT seller_id) AS val FROM sellers;", con=engine)['val'][0]
avg_order_value = pd.read_sql("""
    SELECT AVG(order_total) AS val FROM (
        SELECT order_id, SUM(price + freight_value) AS order_total
        FROM order_items GROUP BY order_id
    ) AS t;
""", con=engine)['val'][0]
avg_review_score = pd.read_sql("SELECT AVG(review_score) AS val FROM order_reviews;", con=engine)['val'][0]

col1, col2, col3 = st.columns(3)
col1.metric("Total Revenue", f"R$ {total_revenue:,.2f}")
col2.metric("Total Orders", f"{total_orders:,}")
col3.metric("Total Customers", f"{total_customers:,}")

col4, col5, col6 = st.columns(3)
col4.metric("Total Sellers", f"{total_sellers:,}")
col5.metric("Avg Order Value", f"R$ {avg_order_value:,.2f}")
col6.metric("Avg Review Score", f"{avg_review_score:.2f}")



st.header("Sales Analysis")

# Monthly revenue trend
monthly_trend = pd.read_sql("""
    SELECT DATE_FORMAT(o.order_purchase_timestamp, '%%Y-%%m') AS month,
           SUM(oi.price + oi.freight_value) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY month ORDER BY month;
""", con=engine)
st.subheader("Monthly Revenue Trend")
st.line_chart(monthly_trend.set_index('month')['revenue'])

# Revenue by category
category_revenue = pd.read_sql("""
    SELECT ct.product_category_name_english AS category,
           SUM(oi.price + oi.freight_value) AS revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    GROUP BY category ORDER BY revenue DESC LIMIT 10;
""", con=engine)
st.subheader("Top 10 Categories by Revenue")
st.bar_chart(category_revenue.set_index('category')['revenue'])

# Top-selling products
top_products = pd.read_sql("""
    SELECT product_id, COUNT(*) AS times_ordered, SUM(price + freight_value) AS total_revenue
    FROM order_items GROUP BY product_id ORDER BY times_ordered DESC LIMIT 10;
""", con=engine)
st.subheader("Top-Selling Products")
st.dataframe(top_products)

# Sales by location
sales_by_state = pd.read_sql("""
    SELECT c.customer_state, SUM(oi.price + oi.freight_value) AS total_revenue,
           COUNT(DISTINCT o.order_id) AS total_orders
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY c.customer_state ORDER BY total_revenue DESC LIMIT 10;
""", con=engine)
st.subheader("Sales by State")
fig5 = px.treemap(sales_by_state, path=['customer_state'], values='total_revenue',
                   title='Sales by State (Revenue)')
st.plotly_chart(fig5)





st.header("Customer Analysis")

# Customer distribution
customer_dist = pd.read_sql("""
    SELECT customer_state, COUNT(DISTINCT customer_unique_id) AS customer_count
    FROM customers GROUP BY customer_state ORDER BY customer_count DESC LIMIT 10;
""", con=engine)
st.subheader("Customer Distribution by State")
st.bar_chart(customer_dist.set_index('customer_state')['customer_count'])

# Top customers (also covers customer spending)
top_customers = pd.read_sql("""
    SELECT c.customer_unique_id, SUM(oi.price + oi.freight_value) AS total_spent
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY c.customer_unique_id ORDER BY total_spent DESC LIMIT 10;
""", con=engine)
st.subheader("Top 10 Customers by Spending")
st.dataframe(top_customers)

# Repeat vs new customers
repeat_vs_new = pd.read_sql("""
    SELECT CASE WHEN order_count > 1 THEN 'Repeat' ELSE 'New' END AS customer_type,
           COUNT(*) AS customer_count
    FROM (
        SELECT customer_unique_id, COUNT(DISTINCT customer_id) AS order_count
        FROM customers GROUP BY customer_unique_id
    ) AS t
    GROUP BY customer_type;
""", con=engine)
st.subheader("Repeat vs New Customers")
fig1 = px.pie(repeat_vs_new, names='customer_type', values='customer_count', 
              title='Repeat vs New Customers')
st.plotly_chart(fig1)






st.header("Seller & Product Analysis")

# Top sellers
top_sellers = pd.read_sql("""
    SELECT seller_id, COUNT(DISTINCT order_id) AS total_orders, SUM(price + freight_value) AS total_revenue
    FROM order_items GROUP BY seller_id ORDER BY total_revenue DESC LIMIT 10;
""", con=engine)
st.subheader("Top 10 Sellers by Revenue")
st.dataframe(top_sellers)

# Category performance
category_performance = pd.read_sql("""
    SELECT ct.product_category_name_english AS category,
           COUNT(DISTINCT oi.order_id) AS total_orders,
           SUM(oi.price + oi.freight_value) AS total_revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    GROUP BY category ORDER BY total_revenue DESC LIMIT 10;
""", con=engine)
st.subheader("Category Performance")
st.bar_chart(category_performance.set_index('category')['total_revenue'])

# Seller ratings
seller_ratings = pd.read_sql("""
    SELECT oi.seller_id, AVG(r.review_score) AS avg_rating, COUNT(DISTINCT oi.order_id) AS total_orders
    FROM order_items oi
    JOIN order_reviews r ON oi.order_id = r.order_id
    GROUP BY oi.seller_id
    HAVING total_orders >= 20
    ORDER BY avg_rating DESC LIMIT 10;
""", con=engine)
st.subheader("Top Rated Sellers (20+ orders)")
st.dataframe(seller_ratings)






st.header("Delivery Analysis")

# Average delivery time
avg_delivery = pd.read_sql("""
    SELECT AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) AS val
    FROM orders WHERE order_delivered_customer_date IS NOT NULL;
""", con=engine)['val'][0]
fig6 = go.Figure(go.Indicator(
    mode="gauge+number",
    value=avg_delivery,
    title={'text': "Average Delivery Time (days)"},
    gauge={
        'axis': {'range': [0, 30]},
        'bar': {'color': "#378ADD"},
        'steps': [
            {'range': [0, 10], 'color': "#E6F1FB"},
            {'range': [10, 20], 'color': "#B5D4F4"},
            {'range': [20, 30], 'color': "#85B7EB"}
        ],
    }
))
st.plotly_chart(fig6)

# On-time vs delayed
delivery_status = pd.read_sql("""
    SELECT CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 'On-time' ELSE 'Delayed' END AS status,
    COUNT(*) AS order_count
    FROM orders WHERE order_delivered_customer_date IS NOT NULL GROUP BY status;
""", con=engine)
st.subheader("On-Time vs Delayed Orders")
fig2 = px.pie(delivery_status, names='status', values='order_count',
              title='On-Time vs Delayed Orders', hole=0.4)
st.plotly_chart(fig2)

# Delivery by location
delivery_by_state = pd.read_sql("""
    SELECT c.customer_state, AVG(DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)) AS avg_delivery_days
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_state ORDER BY avg_delivery_days DESC LIMIT 10;
""", con=engine)

st.subheader("Slowest Delivery States")
st.bar_chart(delivery_by_state.set_index('customer_state')['avg_delivery_days'])

# Delivery delay vs review score
delay_vs_review = pd.read_sql("""
    SELECT r.review_score, AVG(DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date)) AS avg_delay
    FROM order_reviews r
    JOIN orders o ON r.order_id = o.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
    GROUP BY r.review_score ORDER BY r.review_score;
""", con=engine)

scatter_data = pd.read_sql("""
    SELECT r.review_score, 
           DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) AS delivery_delay_days
    FROM order_reviews r
    JOIN orders o ON r.order_id = o.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
    LIMIT 5000;
""", con=engine)

st.subheader("Delivery Delay vs Review Score")
fig7 = px.scatter(scatter_data, x='review_score', y='delivery_delay_days',
                   title='Delivery Delay vs Review Score (sample)',
                   opacity=0.3)
st.plotly_chart(fig7)







st.header("Customer Experience")

# Review score distribution
review_dist = pd.read_sql("""
    SELECT review_score, COUNT(*) AS count
    FROM order_reviews GROUP BY review_score ORDER BY review_score;
""", con=engine)
st.subheader("Review Score Distribution")
fig3 = px.bar(review_dist, x='count', y='review_score', orientation='h',
              color='count', color_continuous_scale='Blues',
              title='Review Score Distribution')
fig3.update_layout(yaxis=dict(dtick=1))
st.plotly_chart(fig3)

# Reviews by category
reviews_by_category = pd.read_sql("""
    SELECT ct.product_category_name_english AS category,
           AVG(r.review_score) AS avg_rating, COUNT(*) AS total_reviews
    FROM order_reviews r
    JOIN order_items oi ON r.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    GROUP BY category
    HAVING total_reviews >= 50
    ORDER BY avg_rating DESC LIMIT 10;
""", con=engine)
st.subheader("Top Rated Categories")
st.dataframe(reviews_by_category)

# Rating vs delivery performance (reuse from Section 5)
st.subheader("Rating vs Delivery Delay")
st.bar_chart(delay_vs_review.set_index('review_score')['avg_delay'])