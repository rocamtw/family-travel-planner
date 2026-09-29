import streamlit as st
from datetime import date, timedelta
from google import genai

# ==========================================
# 語系字典配置 (i18n Translation Dictionary)
# ==========================================
LANG_PACK = {
    "zh": {
        "title": "✈️ 家庭專屬 最佳機票、住宿預算試算 ＋ AI 對話行程智囊",
        "missing_key": "⚠️ 系統尚未在 Streamlit Secrets 偵測到 GEMINI_KEY，請至後台 Settings -> Secrets 完成設定。",
        "members_expander": "👨‍👩‍👧‍👦 成員配置與體力需求（點此展開修改）",
        "adults": "成人人數",
        "children": "小孩人數",
        "child_age": "小孩年齡分佈",
        "child_age_opts": [
            "幼童 (約 2~3 歲，需午睡與推車)",
            "學齡前 (4~6 歲)",
            "學齡兒童 (7~12 歲)",
            "嬰幼兒 (未滿 2 歲)",
            "無小孩同行"
        ],
        "seniors": "長輩同行狀況",
        "seniors_opts": ["無長輩", "有長輩 (需多休息)", "有行動不便長輩"],
        "stroller": "需攜帶推車（平緩動線、電梯優先）",
        "daylight_flight": "限白天班機（09:00 - 15:00 起飛）",
        "origin": "出發機場",
        "dest": "目的地城市 / 機場",
        "custom_dest_prompt": "請輸入城市或機場名稱",
        "trip_days_label": "預計旅遊天數",
        "days_opts": [
            "🤖 由 AI 依目的地與幼童體力推薦最佳天數",
            "3 天（快閃輕旅行）",
            "4 天（輕鬆漫遊首選）",
            "5 天（經典黃金天數）",
            "6 天（深度不趕場）",
            "7 天（完整長假）",
            "8 天以上（慢活深度遊）"
        ],
        "timing_label": "出發時段偏好",
        "timing_opts": [
            "近期出發（未來 1~3 個月推薦最舒適月份）",
            "全年度最佳月份（氣候好且避開人潮）",
            "全年度最佳月份（氣候舒適熱鬧，不避開人潮）",
            "春季出遊（3~5 月）",
            "秋季出遊（9~11 月）",
            "冬季出遊（12~2 月）"
        ],
        "hotel_label": "每晚住宿預算",
        "hotel_opts": [
            "中價位商務/家庭型（約 NT$ 3,500 ~ 5,500 /晚）",
            "親子友善/星級飯店（約 NT$ 5,500 ~ 9,000 /晚）",
            "平價小資型（約 NT$ 2,500 ~ 3,500 /晚）",
            "頂級度假村（約 NT$ 9,000 以上 /晚）"
        ],
        "submit_btn": "🚀 推薦最佳檔期、計算全家總預算 ＋ 產出完整行程",
        "download_btn": "📥 下載本次旅行手冊 (.md)",
        "rainy_header": "☔ 氣候應變：室內親子備案",
        "rainy_btn": "🔄 一鍵切換全室內備案",
        "packing_expander": "🎒 行前打包清單（互動確認）",
        "chat_header": "💬 AI 旅行顧問即時對話",
        "chat_placeholder": "輸入你想微調的景點、天數或問題...",
        "ai_thinking": "AI 顧問正在為你調整企劃與試算...",
        "server_busy": "⚠️ 伺服器忙碌，請稍候再試！"
    },
    "en": {
        "title": "✈️ Family Travel Planner: Flight & Hotel Budget Calculator + AI Itinerary Guide",
        "missing_key": "⚠️ GEMINI_KEY not found in Streamlit Secrets. Please configure it under Settings -> Secrets.",
        "members_expander": "👨‍👩‍👧‍👦 Family Members & Physical Needs (Click to edit)",
        "adults": "Adults",
        "children": "Children",
        "child_age": "Children Age Distribution",
        "child_age_opts": [
            "Toddler (2~3 yrs, stroller & afternoon nap required)",
            "Preschooler (4~6 yrs)",
            "School Age (7~12 yrs)",
            "Infant (<2 yrs)",
            "No children"
        ],
        "seniors": "Seniors Traveling Together",
        "seniors_opts": ["No seniors", "With seniors (Need more rest)", "Reduced mobility (Wheelchair needed)"],
        "stroller": "Stroller required (Smooth paths & elevators prioritized)",
        "daylight_flight": "Daytime flights only (Depart between 09:00 - 15:00)",
        "origin": "Departure Airport",
        "dest": "Destination City / Airport",
        "custom_dest_prompt": "Please enter city or airport name",
        "trip_days_label": "Trip Duration",
        "days_opts": [
            "🤖 Let AI recommend optimal days based on destination & toddlers",
            "3 Days (Weekend Getaway)",
            "4 Days (Relaxed Pace)",
            "5 Days (Classic Golden Duration)",
            "6 Days (In-depth Exploration)",
            "7 Days (Full Vacation)",
            "8+ Days (Slow Travel)"
        ],
        "timing_label": "Departure Timing Preference",
        "timing_opts": [
            "Upcoming trip (Best month in next 1~3 months)",
            "Best month year-round (Pleasant weather & avoid crowds)",
            "Best month year-round (Vibrant & peak season, no crowd avoidance)",
            "Spring trip (Mar ~ May)",
            "Autumn trip (Sep ~ Nov)",
            "Winter trip (Dec ~ Feb)"
        ],
        "hotel_label": "Nightly Accommodation Budget",
        "hotel_opts": [
            "Mid-range Business/Family Hotel (~NT$ 3,500 - 5,500 / night)",
            "Family-friendly / 4-5 Star Hotel (~NT$ 5,500 - 9,000 / night)",
            "Budget-friendly (~NT$ 2,500 - 3,500 / night)",
            "Luxury Resort / Onsen Hotel (>NT$ 9,000 / night)"
        ],
        "submit_btn": "🚀 Recommend Best Timing, Estimate Total Budget + Generate Itinerary",
        "download_btn": "📥 Download Travel Handbook (.md)",
        "rainy_header": "☔ Weather Backup: Indoor Family-friendly Itinerary",
        "rainy_btn": "🔄 Switch to 100% Indoor Rainy-day Backup",
        "packing_expander": "🎒 Pre-trip Packing Checklist (Interactive)",
        "chat_header": "💬 Real-time AI Travel Consultant Chat",
        "chat_placeholder": "Ask questions, adjust attractions, or modify the plan...",
        "ai_thinking": "AI consultant is analyzing and adjusting your itinerary...",
        "server_busy": "⚠️ Server busy, please retry in a moment!"
    }
}

st.set_page_config(page_title="Family Travel Planner", page_icon="✈️", layout="wide")

# ==========================================
# 語系切換器 (Language Selector)
# ==========================================
col_title, col_lang = st.columns([5, 1])
with col_lang:
    selected_lang = st.selectbox(
        "🌐 Language / 語言",
        options=["繁體中文", "English"],
        index=0
    )
lang_key = "zh" if selected_lang == "繁體中文" else "en"
T = LANG_PACK[lang_key]

with col_title:
    st.title(T["title"])

gemini_api_key = st.secrets.get("GEMINI_KEY", "")
if not gemini_api_key:
    st.warning(T["missing_key"])

# 狀態初始化
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "plan_generated" not in st.session_state:
    st.session_state.plan_generated = False
if "base_plan_content" not in st.session_state:
    st.session_state.base_plan_content = ""
if "rainy_plan_content" not in st.session_state:
    st.session_state.rainy_plan_content = ""

# 極速串流輸出函式
def stream_gemini_fast(client, contents_input):
    models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    for model_name in models:
        try:
            response_stream = client.models.generate_content_stream(
                model=model_name,
                contents=contents_input
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            return
        except Exception:
            continue
    yield f"\n\n{T['server_busy']}"

# ==========================================
# 區塊 1：家庭成員配置
# ==========================================
with st.expander(T["members_expander"], expanded=False):
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        adult_count = st.number_input(T["adults"], min_value=1, max_value=20, value=2, step=1)
    with col_m2:
        child_count = st.number_input(T["children"], min_value=0, max_value=10, value=1, step=1)
    with col_m3:
        child_age_label = st.selectbox(
            T["child_age"],
            options=T["child_age_opts"],
            index=0 if child_count > 0 else 4
        )
    with col_m4:
        senior_option = st.selectbox(T["seniors"], options=T["seniors_opts"], index=0)

    col_req1, col_req2 = st.columns(2)
    with col_req1:
        need_stroller = st.checkbox(T["stroller"], value=True if child_count > 0 else False)
    with col_req2:
        strict_flight_time = st.checkbox(T["daylight_flight"], value=True)

# ==========================================
# 區塊 2：行程、天數與預算偏好
# ==========================================
ORIGIN_OPTIONS = {
    "台北桃園 (TPE) / Taipei Taoyuan": "TPE",
    "台北松山 (TSA) / Taipei Songshan": "TSA",
    "高雄小港 (KHH) / Kaohsiung": "KHH",
    "台中清泉崗 (RMQ) / Taichung": "RMQ"
}

DEST_OPTIONS = {
    "🇯🇵 日本 - 福岡 (FUK) / Fukuoka": "福岡 (FUK)",
    "🇯🇵 日本 - 沖繩那霸 (OKA) / Okinawa": "沖繩 (OKA)",
    "🇯🇵 日本 - 東京成田 (NRT) / Tokyo Narita": "東京成田 (NRT)",
    "🇯🇵 日本 - 東京羽田 (HND) / Tokyo Haneda": "東京羽田 (HND)",
    "🇯🇵 日本 - 大阪關西 (KIX) / Osaka Kansai": "大阪關西 (KIX)",
    "🇯🇵 日本 - 名古屋 (NGO) / Nagoya": "名古屋 (NGO)",
    "🇯🇵 日本 - 札幌新千歲 (CTS) / Sapporo Chitose": "札幌 (CTS)",
    "🇰🇷 韓國 - 首爾仁川 (ICN) / Seoul Incheon": "首爾仁川 (ICN)",
    "🇰🇷 韓國 - 釜山金海 (PUS) / Busan": "釜山 (PUS)",
    "🇸🇬 新加坡 - 樟宜 (SIN) / Singapore Changi": "新加坡 (SIN)",
    "🇹🇭 泰國 - 曼谷 (BKK) / Bangkok": "曼谷 (BKK)",
    "🇻🇳 越南 - 峴港 (DAD) / Da Nang": "峴港 (DAD)",
    "🌐 其他 / Custom": "CUSTOM"
}

col1, col2, col3 = st.columns(3)
with col1:
    origin_label = st.selectbox(T["origin"], options=list(ORIGIN_OPTIONS.keys()), index=0)
    origin_text = ORIGIN_OPTIONS[origin_label]
with col2:
    dest_label = st.selectbox(T["dest"], options=list(DEST_OPTIONS.keys()), index=0)
    if DEST_OPTIONS[dest_label] == "CUSTOM":
        dest_text = st.text_input(T["custom_dest_prompt"], value="Okinawa" if lang_key == "en" else "沖繩")
    else:
        dest_text = DEST_OPTIONS[dest_label]
with col3:
    days_selection = st.selectbox(T["trip_days_label"], options=T["days_opts"], index=0)

col4, col5 = st.columns(2)
with col4:
    flexible_time = st.selectbox(T["timing_label"], options=T["timing_opts"], index=0)
with col5:
    hotel_level = st.selectbox(T["hotel_label"], options=T["hotel_opts"], index=0)

# ==========================================
# 核心執行按鈕
# ==========================================
if st.button(T["submit_btn"], type="primary"):
    if not gemini_api_key:
        st.error(T["missing_key"])
    else:
        today = date.today()
        f_start = today + timedelta(days=30)
        f_end = today + timedelta(days=90)

        # 組合語言與天數規範提示詞
        if "AI" in days_selection:
            days_instruction = f"""
- The user has not preset duration. Suggest the most comfortable duration (e.g. X days Y nights) based on {dest_text} and a family with {adult_count} adults and {child_count} children (stroller-friendly pace). Explain the rationale and generate the complete plan accordingly.
"""
        else:
            days_instruction = f"""
- The user specified duration: {days_selection}. Plan strictly according to this duration.
"""

        lang_instruction = "Respond entirely in Traditional Chinese (繁體中文)." if lang_key == "zh" else "Respond entirely in fluent English."

        base_prompt = f"""
You are a senior family travel consultant. Provide a comprehensive direct-flight itinerary and budget breakdown.
Language requirement: {lang_instruction}

[Profile & Constraints]
- Reference Date: {today.strftime('%Y/%m/%d')}
- Route: {origin_text} to {dest_text}
- Travelers: {adult_count} Adults, {child_count} Children ({child_age_label}), Seniors: {senior_option}
- Hotel Budget: {hotel_level}
- Requirements: {'Stroller and barrier-free routes prioritized' if need_stroller else 'Standard walking'}, {'Direct daylight flight (departing 09:00 - 15:00)' if strict_flight_time else 'Flexible flight timing'}
- Timing Preference: {flexible_time}
{days_instruction}

[Output Structure Guidelines]
1. **Duration & Departure Timing Analysis**:
   - Optimal days assessment if AI recommended.
   - Recommended departure month/weeks, expected temperature, weather, and crowd considerations.
2. **Direct Flights & Recommended Hotels**:
   - Family-friendly direct airlines and flight schedules.
   - 2 stroller-accessible hotels with Google Maps links format: [Hotel Name](https://www.google.com/maps/search/?api=1&query=HotelName).
3. **Daily Family-Friendly Itinerary**:
   - 1 morning attraction, comfortable lunch, afternoon nap/rest break, relaxed evening.
   - Each attraction & restaurant with Google Maps navigation link: `[Map](https://www.google.com/maps/search/?api=1&query=SpotName+{dest_text})`.
4. **💰 Total Estimated Family Budget Table ({adult_count} Adults + {child_count} Children in TWD)**:
   Must provide a clear Markdown table at the very end summarizing:
   | Item | Details | Estimated Amount (TWD) |
   Include: Direct Flights, Accommodation, Dining, Transportation, Tickets & Activities, Contingency/Shopping, and Total Range.
"""

        ai_client = genai.Client(api_key=gemini_api_key)
        st.markdown("---")
        plan_box = st.empty()
        full_text = plan_box.write_stream(stream_gemini_fast(ai_client, base_prompt))

        st.session_state.base_plan_content = full_text
        st.session_state.plan_generated = True
        st.session_state.rainy_plan_content = ""
        st.session_state.chat_history = [
            {"role": "user", "parts": base_prompt},
            {"role": "model", "parts": full_text}
        ]

# ==========================================
# 輔助功能區塊
# ==========================================
if st.session_state.plan_generated:
    st.markdown("---")
    st.download_button(
        label=T["download_btn"],
        data=st.session_state.base_plan_content,
        file_name=f"{dest_text}_Travel_Plan.md",
        mime="text/markdown"
    )

    # 雨天室內備案按鈕
    st.subheader(T["rainy_header"])
    if st.button(T["rainy_btn"], type="secondary"):
        ai_client = genai.Client(api_key=gemini_api_key)
        rain_lang_inst = "Respond in Traditional Chinese." if lang_key == "zh" else "Respond in English."
        rain_prompt = f"Replace the previous itinerary for {dest_text} with 100% indoor family-friendly alternatives (aquariums, shopping malls, science centers, stroller-accessible). Include Google Maps links. {rain_lang_inst}"
        rain_box = st.empty()
        rain_text = rain_box.write_stream(stream_gemini_fast(ai_client, rain_prompt))
        st.session_state.rainy_plan_content = rain_text

    # 行前清單
    with st.expander(T["packing_expander"], expanded=False):
        c1, c2, c3 = st.columns(3)
        if lang_key == "zh":
            with c1:
                st.markdown("**🩺 醫藥與護理**")
                st.checkbox("幼兒退燒/感冒藥水", value=False)
                st.checkbox("防蚊液/止癢膏/OK繃", value=False)
                st.checkbox("護照正本（效期半年以上）", value=False)
            with c2:
                st.markdown("**🛒 移動裝備**")
                st.checkbox("推車專用雨罩（必備）", value=False)
                st.checkbox("輕便登機推車/掛勾", value=False)
                st.checkbox("隨身濕紙巾/酒精棉片", value=False)
            with c3:
                st.markdown("**🍼 飲食與安撫**")
                st.checkbox("拋棄式圍兜/食物剪", value=False)
                st.checkbox("常溫粥/米餅/水壺", value=False)
                st.checkbox("尿布（天數 × 5 片）", value=False)
        else:
            with c1:
                st.markdown("**🩺 Medical & Care**")
                st.checkbox("Child fever/cold medication", value=False)
                st.checkbox("Mosquito repellent / Band-Aids", value=False)
                st.checkbox("Passports (Valid for >6 months)", value=False)
            with c2:
                st.markdown("**🛒 Gear & Mobility**")
                st.checkbox("Stroller rain cover (Must-have)", value=False)
                st.checkbox("Compact cabin stroller & hooks", value=False)
                st.checkbox("Wet wipes & sanitizer packs", value=False)
            with c3:
                st.markdown("**🍼 Feeding & Comfort**")
                st.checkbox("Disposable bibs & food scissors", value=False)
                st.checkbox("Baby purees/snacks & water bottle", value=False)
                st.checkbox("Diapers (Trip Days × 5 pcs)", value=False)

    # 延伸對話
    st.markdown("---")
    st.subheader(T["chat_header"])
    for msg in st.session_state.chat_history[2:]:
        st.chat_message(msg["role"]).write(msg["parts"])

    user_query = st.chat_input(T["chat_placeholder"])
    if user_query:
        st.chat_message("user").write(user_query)
        st.session_state.chat_history.append({"role": "user", "parts": user_query})

        with st.chat_message("assistant"):
            ai_client = genai.Client(api_key=gemini_api_key)
            formatted = [{"role": h["role"], "parts": [{"text": h["parts"]}]} for h in st.session_state.chat_history]
            chat_reply = st.write_stream(stream_gemini_fast(ai_client, formatted))
            st.session_state.chat_history.append({"role": "model", "parts": chat_reply})
