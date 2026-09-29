import streamlit as st
import time
import random
import pandas as pd
from datetime import date, timedelta, datetime
from google import genai
from google.genai import types
from google.genai.errors import APIError

# ==========================================
# 伺服器全域監控記錄庫 (Global Monitor State)
# ==========================================
class GlobalMonitor:
    def __init__(self):
        self.logs = []

    def record_log(self, dest, days, style, duration_sec, status):
        log_entry = {
            "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "目的地": dest,
            "旅遊天數": str(days),
            "旅遊型態": "自由行" if "自由" in style or "Free" in style else "跟團/包車",
            "耗時(秒)": round(duration_sec, 2),
            "狀態": status
        }
        self.logs.insert(0, log_entry)
        if len(self.logs) > 200:
            self.logs.pop()

    def get_logs_df(self):
        if not self.logs:
            return pd.DataFrame()
        return pd.DataFrame(self.logs)

    def clear_logs(self):
        self.logs.clear()

@st.cache_resource
def get_monitor():
    return GlobalMonitor()

monitor = get_monitor()

# ==========================================
# 語系字典配置 (i18n Translation Dictionary)
# ==========================================
LANG_PACK = {
    "zh": {
        "title": "✈️ 家庭專屬 最佳機票、住宿預算試算 ＋ AI 對話行程智囊",
        "missing_key": "⚠️ 系統尚未在 Streamlit Secrets 偵測到 GEMINI_KEY，請至後台 Settings -> Secrets 完成設定。",
        "members_expander": "👨‍👩‍👧‍👦 成員配置與體力需求（點此展開修改）",
        "travel_style_label": "旅遊型態偏好",
        "travel_style_opts": [
            "🎒 自由行（彈性自主、深入漫遊、推車/地鐵/計程車接駁）",
            "🚌 團體旅遊 / 包車客製團（專車接送免走累、全程領隊導遊、行李直達）"
        ],
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
            "📅 指定具體出發與回程日期區間",
            "近期出發（未來 1~3 個月推薦最舒適月份）",
            "全年度最佳月份（氣候好且避開人潮）",
            "全年度最佳月份（氣候舒適熱鬧，不避開人潮）",
            "春季出遊（3~5 月）",
            "秋季出遊（9~11 月）",
            "冬季出遊（12~2 月）"
        ],
        "specific_range_label": "請選擇旅遊日期區間（點選出發日與回程日）",
        "hotel_budget_label": "每晚住宿預算（新台幣 TWD，可手動輸入）",
        "hotel_style_label": "住宿偏好風格",
        "hotel_style_opts": [
            "親子友善 / 近地鐵或車站（電梯推車友善）",
            "舒適商務型（乾淨平價、生活機能佳）",
            "渡假村 / 溫泉飯店（休閒設施豐富）",
            "包棟公寓式飯店（附廚房、洗衣機）"
        ],
        "submit_btn": "🚀 推薦最佳檔期、計算全家總預算 ＋ 產出完整行程",
        "download_btn": "📥 下載本次旅行手冊 (.md)",
        "rainy_header": "☔ 氣候應變：室內親子備案",
        "rainy_btn": "🔄 一鍵切換全室內備案",
        "packing_expander": "🎒 行前打包清單（互動確認）",
        "chat_header": "💬 AI 旅行顧問即時對話",
        "chat_placeholder": "輸入你想微調的景點、天數或問題...",
        "ai_thinking": "AI 顧問正在為你調整企劃與試算...",
        "server_busy": "⚠️ 目前連線人數較多，請稍候 3 秒再點擊一次！"
    },
    "en": {
        "title": "✈️ Family Travel Planner: Flight & Hotel Budget Calculator + AI Itinerary Guide",
        "missing_key": "⚠️ GEMINI_KEY not found in Streamlit Secrets. Please configure it under Settings -> Secrets.",
        "members_expander": "👨‍👩‍👧‍👦 Family Members & Physical Needs (Click to edit)",
        "travel_style_label": "Travel Style Preference",
        "travel_style_opts": [
            "🎒 Free & Easy / Independent Travel (Flexible, stroller/metro/taxi friendly)",
            "🚌 Guided Group Tour / Private Chartered Tour (Coach transfer, tour guide, hassle-free luggage)"
        ],
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
            "📅 Specific Date Range (Select departure & return)",
            "Upcoming trip (Best month in next 1~3 months)",
            "Best month year-round (Pleasant weather & avoid crowds)",
            "Best month year-round (Vibrant & peak season, no crowd avoidance)",
            "Spring trip (Mar ~ May)",
            "Autumn trip (Sep ~ Nov)",
            "Winter trip (Dec ~ Feb)"
        ],
        "specific_range_label": "Select Travel Date Range (Departure & Return)",
        "hotel_budget_label": "Nightly Hotel Budget (TWD, type directly)",
        "hotel_style_label": "Preferred Accommodation Style",
        "hotel_style_opts": [
            "Family-friendly / Near station (Stroller & elevator friendly)",
            "Comfortable business hotel (Clean, great value, good amenities)",
            "Resort / Onsen Ryokan (Spacious facilities & dining)",
            "Aparthotel / Condo (Kitchen & laundry included)"
        ],
        "submit_btn": "🚀 Recommend Best Timing, Estimate Total Budget + Generate Itinerary",
        "download_btn": "📥 Download Travel Handbook (.md)",
        "rainy_header": "☔ Weather Backup: Indoor Family-friendly Itinerary",
        "rainy_btn": "🔄 Switch to 100% Indoor Rainy-day Backup",
        "packing_expander": "🎒 Pre-trip Packing Checklist (Interactive)",
        "chat_header": "💬 Real-time AI Travel Consultant Chat",
        "chat_placeholder": "Ask questions, adjust attractions, or modify the plan...",
        "ai_thinking": "AI consultant is analyzing and adjusting your itinerary...",
        "server_busy": "⚠️ High traffic right now, please try clicking again in 3 seconds!"
    }
}

st.set_page_config(page_title="Family Travel Planner", page_icon="✈️", layout="wide")

# ==========================================
# 管理員後台判斷 (相容新舊版 Streamlit 參數)
# ==========================================
ADMIN_PWD = str(st.secrets.get("ADMIN_PWD", "8888"))

# 抓取網址中的 admin 參數
url_admin = ""
try:
    if hasattr(st, "query_params") and "admin" in st.query_params:
        url_admin = str(st.query_params["admin"])
except Exception:
    pass

with st.sidebar:
    st.markdown("### 🌐 語言設定 / Language")
    selected_lang = st.selectbox(
        "選擇語言",
        options=["繁體中文", "English"],
        index=0,
        label_visibility="collapsed"
    )
    lang_key = "zh" if selected_lang == "繁體中文" else "en"
    T = LANG_PACK[lang_key]

    st.markdown("---")
    st.markdown("🔒 **後台管理通道**")
    input_pwd = st.text_input("輸入密碼 (預設: 8888)", type="password", value="")

# 判斷是否為管理員
is_admin = (input_pwd == ADMIN_PWD) or (url_admin == ADMIN_PWD)

# ==========================================
# 📊 管理員儀表板 (Admin Dashboard View)
# ==========================================
if is_admin:
    st.title("📊 系統監控與使用數據看板 (Admin Dashboard)")
    st.caption("即時匯總所有使用者的調用日誌、熱門目的地與效能指標。")

    df_logs = monitor.get_logs_df()

    if not df_logs.empty:
        col1, col2, col3, col4 = st.columns(4)
        total_runs = len(df_logs)
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_runs = len(df_logs[df_logs["時間"].str.startswith(today_str)])
        avg_duration = df_logs["耗時(秒)"].mean()
        success_rate = (len(df_logs[df_logs["狀態"] == "成功"]) / total_runs) * 100

        col1.metric("累計請求總次數", f"{total_runs} 次")
        col2.metric("今日生成次數", f"{today_runs} 次")
        col3.metric("平均生成耗時", f"{avg_duration:.2f} 秒")
        col4.metric("請求成功率", f"{success_rate:.1f} %")

        st.markdown("---")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("📍 最常查詢目的地排行")
            st.bar_chart(df_logs["目的地"].value_counts())

        with col_c2:
            st.subheader("🧭 旅遊型態分佈")
            st.bar_chart(df_logs["旅遊型態"].value_counts())

        st.markdown("---")
        st.subheader("📋 即時調用日誌 (Recent Logs - 最新在最上方)")
        st.dataframe(df_logs, use_container_width=True)

        if st.button("🗑️ 清空所有統計日誌", type="secondary"):
            monitor.clear_logs()
            st.rerun()
    else:
        st.info("💡 目前尚無呼叫紀錄。親友在前台產出行程後，數據將即時顯示在此！")

    st.markdown("---")
    st.caption("提示：在側邊欄清空密碼或從網址移除 `?admin=...` 即可返回前台介面。")
    st.stop()  # 阻斷後續前台畫面載入

# ==========================================
# 一般使用者前台介面 (Public UI)
# ==========================================
st.title(T["title"])

gemini_api_key = st.secrets.get("GEMINI_KEY", "")
if not gemini_api_key:
    st.warning(T["missing_key"])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "plan_generated" not in st.session_state:
    st.session_state.plan_generated = False
if "base_plan_content" not in st.session_state:
    st.session_state.base_plan_content = ""
if "rainy_plan_content" not in st.session_state:
    st.session_state.rainy_plan_content = ""

# 非阻塞式生成核心
def generate_travel_plan_safe(api_key, contents_input, max_retries=3):
    models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    config = types.GenerateContentConfig(
        temperature=0.2,
        seed=42
    )
    for attempt in range(max_retries):
        client = genai.Client(api_key=api_key)
        for model_name in models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents_input,
                    config=config
                )
                if response.text:
                    return response.text
            except APIError as e:
                if e.code in [429, 503] or "RESOURCE_EXHAUSTED" in str(e):
                    time.sleep(1.0 + random.uniform(0.5, 1.2))
                    continue
                break
            except Exception:
                time.sleep(0.5)
                continue
    return None

def stream_text_to_ui(placeholder, text_content):
    words = text_content.split("\n")
    buffer = ""
    for line in words:
        buffer += line + "\n"
        placeholder.markdown(buffer)
        time.sleep(0.02)
    return buffer

# 區塊 1：旅遊型態與家庭成員配置
travel_style_selection = st.radio(
    f"🧭 **{T['travel_style_label']}**",
    options=T["travel_style_opts"],
    index=0,
    horizontal=True
)
is_group_tour = "團體" in travel_style_selection or "Guided" in travel_style_selection

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

# 區塊 2：行程、天數、時段與預算偏好
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

col4, col5, col6 = st.columns(3)
with col4:
    flexible_time = st.selectbox(T["timing_label"], options=T["timing_opts"], index=0)
with col5:
    hotel_budget_per_night = st.number_input(
        T["hotel_budget_label"],
        min_value=1000,
        max_value=100000,
        value=4500,
        step=500,
        help="輸入每晚預計的飯店預算金額"
    )
with col6:
    hotel_style_pref = st.selectbox(T["hotel_style_label"], options=T["hotel_style_opts"], index=0)

exact_start_date = None
exact_end_date = None
calculated_days = None

if "指定" in flexible_time or "Specific" in flexible_time:
    default_start = date.today() + timedelta(days=14)
    default_end = default_start + timedelta(days=4)
    date_range = st.date_input(
        f"📅 {T['specific_range_label']}",
        value=(default_start, default_end),
        min_value=date.today(),
        help="請先點擊出發日，再點擊回程日"
    )
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        exact_start_date, exact_end_date = date_range[0], date_range[1]
        calculated_days = (exact_end_date - exact_start_date).days + 1
        st.info(f"🗓️ 已選定行程：**{exact_start_date.strftime('%Y-%m-%d')}** 至 **{exact_end_date.strftime('%Y-%m-%d')}**（共 **{calculated_days} 天 {calculated_days - 1} 晚**）")

# 核心執行按鈕
if st.button(T["submit_btn"], type="primary"):
    if not gemini_api_key:
        st.error(T["missing_key"])
    elif ("指定" in flexible_time or "Specific" in flexible_time) and (not exact_start_date or not exact_end_date):
        st.warning("⚠️ 請先在上方日曆選妥完整的【出發日】與【回程日】！")
    else:
        today = date.today()

        if exact_start_date and exact_end_date:
            days_instruction = f"""
- 【EXACT TRAVEL DATES LOCKED】:
  - Departure: {exact_start_date.strftime('%Y-%m-%d')} ({exact_start_date.strftime('%A')})
  - Return: {exact_end_date.strftime('%Y-%m-%d')} ({exact_end_date.strftime('%A')})
  - Duration: Exactly {calculated_days} Days / {calculated_days - 1} Nights.
  - Please arrange the day-by-day plan mapping strictly to these exact calendar dates.
"""
            timing_instruction = f"Travel strictly across {exact_start_date.strftime('%Y-%m-%d')} to {exact_end_date.strftime('%Y-%m-%d')}."
            logged_days = f"{calculated_days} 天"
        else:
            if "AI" in days_selection:
                days_instruction = f"""
- The user has not preset duration. Suggest the most comfortable duration (e.g. X days Y nights) based on {dest_text} and a family with {adult_count} adults and {child_count} children (stroller-friendly pace). Explain the rationale and generate the complete plan accordingly.
"""
            else:
                days_instruction = f"""
- The user specified duration: {days_selection}. Plan strictly according to this duration.
"""
            timing_instruction = f"Departure preference: {flexible_time}."
            if "不避開人潮" in flexible_time or "Vibrant" in flexible_time:
                timing_instruction += " Recommend the peak, lively season with optimal pleasant weather without worrying about crowd levels."
            logged_days = days_selection

        if is_group_tour:
            style_instruction = """
- 【TRAVEL MODE: GUIDED GROUP TOUR / PRIVATE CHARTER TOUR (團體旅遊 / 包車客製團)】
  - 規劃重點：強調專用遊覽巴士直達接送、免拉大件行李趕電車、全程導遊兼領隊照應、適合幼童與長輩體力的合菜聚餐、減少純步行拉車距離。
  - 預算表調整：將機票、住宿、餐飲、專用巴士包車與司導服務費整合為「團費/包車團總估價」或列出「每人平均團費估算 + 導遊司機小費 + 自由活動零用金」。
"""
        else:
            style_instruction = """
- 【TRAVEL MODE: FREE & EASY / INDEPENDENT TRAVEL (自由行)】
  - 規劃重點：彈性自主動線、捷運/地鐵平緩電梯動線、點對點時短程計程車搭配、推車友善餐廳、保留下午 13:30 - 15:30 午睡或回飯店充電時間。
  - 預算表調整：分項列出直飛機票、飯店住宿、當地大眾交通/計程車、餐飲、門票雜支及總預算區間。
"""

        lang_instruction = "Respond entirely in Traditional Chinese (繁體中文)." if lang_key == "zh" else "Respond entirely in fluent English."

        base_prompt = f"""
You are a senior family travel consultant. Provide a comprehensive itinerary and budget breakdown.
Language requirement: {lang_instruction}

[Profile & Constraints]
- Reference Date: {today.strftime('%Y/%m/%d')}
- Travel Mode: {'團體旅遊 / 包車客製團 (Guided / Private Tour)' if is_group_tour else '自由行 (Free & Easy)'}
{style_instruction}
- Route: {origin_text} to {dest_text}
- Travelers: {adult_count} Adults, {child_count} Children ({child_age_label}), Seniors: {senior_option}
- Accommodation Budget: Strictly around NT$ {hotel_budget_per_night:,} per night. Preferred style: {hotel_style_pref}.
- Requirements: {'Stroller and barrier-free routes prioritized' if need_stroller else 'Standard walking'}, {'Direct daylight flight (departing 09:00 - 15:00)' if strict_flight_time else 'Flexible flight timing'}
- Timing & Dates: {timing_instruction}
{days_instruction}

[Output Structure Guidelines]
1. **Duration & Departure Timing Analysis**:
   - If exact date range is specified, confirm the exact period (Day 1: YYYY-MM-DD to Day End: YYYY-MM-DD) and expected weather/temperature during those exact days.
   - If AI recommended, explain the optimal duration assessment.
2. **Direct Flights & Recommended Hotels**:
   - Family-friendly direct airlines and flight schedules suitable for this period.
   - Recommend 2 stroller-accessible hotels matching the budget around NT$ {hotel_budget_per_night:,} / night, with Google Maps links format: [Hotel Name](https://www.google.com/maps/search/?api=1&query=HotelName).
3. **Daily Family-Friendly Itinerary**:
   - Morning attraction, comfortable lunch, afternoon nap/rest break, relaxed evening.
   - If exact date range is given, label each day with specific date & weekday (e.g. Day 1 - 2026/10/06 Tue).
   - Each attraction & restaurant with Google Maps navigation link: `[Map](https://www.google.com/maps/search/?api=1&query=SpotName+{dest_text})`.
4. **💰 Total Estimated Family Budget Table ({adult_count} Adults + {child_count} Children in TWD)**:
   Must provide a clear Markdown table at the very end summarizing:
   | Item | Details | Estimated Amount (TWD) |
"""
        st.markdown("---")
        plan_box = st.empty()

        start_time = time.time()
        with st.spinner(T["ai_thinking"]):
            result_text = generate_travel_plan_safe(gemini_api_key, base_prompt)
        elapsed_time = time.time() - start_time

        # 記錄至全域後台監控庫
        status_label = "成功" if result_text else "失敗/忙碌"
        monitor.record_log(dest_text, logged_days, travel_style_selection, elapsed_time, status_label)

        if result_text:
            full_text = stream_text_to_ui(plan_box, result_text)
            st.session_state.base_plan_content = full_text
            st.session_state.plan_generated = True
            st.session_state.rainy_plan_content = ""
            st.session_state.chat_history = [
                {"role": "user", "parts": base_prompt},
                {"role": "model", "parts": full_text}
            ]
        else:
            plan_box.error(T["server_busy"])

# 輔助功能區塊
if st.session_state.plan_generated:
    st.markdown("---")
    st.download_button(
        label=T["download_btn"],
        data=st.session_state.base_plan_content,
        file_name=f"{dest_text}_Travel_Plan.md",
        mime="text/markdown"
    )

    st.subheader(T["rainy_header"])
    if st.button(T["rainy_btn"], type="secondary"):
        rain_lang_inst = "Respond in Traditional Chinese." if lang_key == "zh" else "Respond in English."
        rain_prompt = f"Replace the previous itinerary for {dest_text} with 100% indoor family-friendly alternatives (aquariums, shopping malls, science centers, stroller-accessible). Include Google Maps links. {rain_lang_inst}"
        rain_box = st.empty()
        with st.spinner(T["ai_thinking"]):
            rain_result = generate_travel_plan_safe(gemini_api_key, rain_prompt)
        if rain_result:
            rain_text = stream_text_to_ui(rain_box, rain_result)
            st.session_state.rainy_plan_content = rain_text
        else:
            rain_box.error(T["server_busy"])

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

    st.markdown("---")
    st.subheader(T["chat_header"])
    for msg in st.session_state.chat_history[2:]:
        st.chat_message(msg["role"]).write(msg["parts"])

    user_query = st.chat_input(T["chat_placeholder"])
    if user_query:
        st.chat_message("user").write(user_query)
        st.session_state.chat_history.append({"role": "user", "parts": user_query})

        with st.chat_message("assistant"):
            chat_box = st.empty()
            formatted = [{"role": h["role"], "parts": [{"text": h["parts"]}]} for h in st.session_state.chat_history]
            with st.spinner("..."):
                chat_res = generate_travel_plan_safe(gemini_api_key, formatted)
            if chat_res:
                chat_reply = stream_text_to_ui(chat_box, chat_res)
                st.session_state.chat_history.append({"role": "model", "parts": chat_reply})
            else:
                chat_box.error(T["server_busy"])
