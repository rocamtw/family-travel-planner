import plotly.graph_objects as go

def render_cute_summary_dashboard(dest_name, total_days, adults, children, hotel_budget):
    """
    可愛風格的行程預算視覺化儀表板
    """
    st.markdown("### 🧁 行程預算可愛總結卡片")
    
    # 預估預算分佈（可依天數與人數動態微調）
    categories = ['✈️ 機票', '🏨 住宿', '🍱 美食餐飲', '🚕 當地交通', '🎟️ 門票活動', '🛍️ 伴手禮雜支']
    
    # 範例動態權重：5天4夜常見家庭比例
    flight_est = (adults * 12000) + (children * 9500)
    hotel_est = max(1, total_days - 1) * hotel_budget
    food_est = total_days * (adults * 1500 + children * 800)
    traffic_est = total_days * 1200
    ticket_est = (adults * 2500 + children * 1500)
    misc_est = 5000
    
    values = [flight_est, hotel_est, food_est, traffic_est, ticket_est, misc_est]
    total_budget = sum(values)

    # 1. 頂部可愛指標卡片
    col1, col2, col3 = st.columns(3)
    col1.metric("📍 夢想目的地", f"{dest_name}")
    col2.metric("🗓️ 旅遊天數", f"{total_days} 天")
    col3.metric("💰 全家預估總預算", f"NT$ {total_budget:,}")

    # 2. 馬卡龍可愛配色環形圖 (Donut Chart)
    cute_colors = [
        '#FF9AA2',  # 蜜桃粉 (機票)
        '#FFB7B2',  # 珊瑚粉 (住宿)
        '#FFDAC1',  # 杏桃奶黃 (美食)
        '#E2F0CB',  # 薄荷蘋果綠 (交通)
        '#B5EAD7',  # 湖水冰綠 (門票)
        '#C7CEEA'   # 薰衣草淡紫 (雜支)
    ]

    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=values,
        hole=0.55,
        marker=dict(colors=cute_colors, line=dict(color='#FFFFFF', width=2)),
        textinfo='label+percent',
        hoverinfo='label+value',
        textfont=dict(size=14, family="sans-serif")
    )])

    fig.update_layout(
        title=dict(
            text="🎀 全家旅遊預算分佈佔比",
            x=0.5,
            xanchor='center',
            font=dict(size=18, color="#4A4A4A")
        ),
        margin=dict(t=50, b=20, l=20, r=20),
        height=380,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True)
