import streamlit as st
from datetime import date, timedelta
from google import genai

st.set_page_config(page_title="家庭自由行智囊", page_icon="✈️", layout="wide")

gemini_api_key = st.secrets.get("GEMINI_KEY", "")

st.title("✈️ 家庭專屬 最佳機票、住宿預算試算 ＋ AI 對話行程智囊")

if not gemini_api_key:
    st.warning("⚠️ 系統尚未在 Streamlit Secrets 偵測到 GEMINI_KEY，請至後台 Settings -> Secrets 完成設定。")

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
    yield "\n\n⚠️ 伺服器忙碌，請稍候再試！"

# ==========================================
# 區塊 1：家庭成員配置
# ==========================================
with st.expander("👨‍👩‍👧‍👦 成員配置與體力需求（點此展開修改）", expanded=False):
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        adult_count = st.selectbox("成人人數", options=[1, 2, 3, 4, 5, 6], index=1)
    with col_m2:
        child_count = st.selectbox("小孩人數", options=[0, 1, 2, 3, 4], index=1)
    with col_m3:
        child_age_label = st.selectbox(
            "小孩年齡分佈",
            options=["幼童 (約 2~3 歲，需午睡與推車)", "學齡前 (4~6 歲)", "學齡兒童 (7~12 歲)", "嬰幼兒 (未滿 2 歲)", "無小孩同行"],
            index=0 if child_count > 0 else 4
        )
    with col_m4:
        senior_option = st.selectbox("長輩同行狀況", options=["無長輩", "有長輩 (需多休息)", "有行動不便長輩"], index=0)

    col_req1, col_req2 = st.columns(2)
    with col_req1:
        need_stroller = st.checkbox("需攜帶推車（平緩動線、電梯優先）", value=True if child_count > 0 else False)
    with col_req2:
        strict_flight_time = st.checkbox("限白天班機（09:00 - 15:00 起飛）", value=True)

# ==========================================
# 區塊 2：行程、天數與預算偏好
# ==========================================
ORIGIN_OPTIONS = {
    "台北桃園 (TPE)": "TPE",
    "台北松山 (TSA)": "TSA",
    "高雄小港 (KHH)": "KHH",
    "台中清泉崗 (RMQ)": "RMQ"
}

DEST_OPTIONS = {
    "🇯🇵 日本 - 福岡 (FUK)": "福岡 (FUK)",
    "🇯🇵 日本 - 沖繩那霸 (OKA)": "沖繩 (OKA)",
    "🇯🇵 日本 - 東京成田 (NRT)": "東京成田 (NRT)",
    "🇯🇵 日本 - 東京羽田 (HND)": "東京羽田 (HND)",
    "🇯🇵 日本 - 大阪關西 (KIX)": "大阪關西 (KIX)",
    "🇯🇵 日本 - 名古屋 (NGO)": "名古屋 (NGO)",
    "🇯🇵 日本 - 札幌新千歲 (CTS)": "札幌 (CTS)",
    "🇰🇷 韓國 - 首爾仁川 (ICN)": "首爾仁川 (ICN)",
    "🇰🇷 韓國 - 釜山金海 (PUS)": "釜山 (PUS)",
    "🇸🇬 新加坡 - 樟宜 (SIN)": "新加坡 (SIN)",
    "🇹🇭 泰國 - 曼谷 (BKK)": "曼谷 (BKK)",
    "🇻🇳 越南 - 峴港 (DAD)": "峴港 (DAD)",
    "🌐 其他（手動輸入）": "CUSTOM"
}

DAYS_OPTIONS = [
    "🤖 由 AI 依目的地與幼童體力推薦最佳天數",
    "3 天（快閃輕旅行）",
    "4 天（輕鬆漫遊首選）",
    "5 天（經典黃金天數）",
    "6 天（深度不趕場）",
    "7 天（完整長假）",
    "8 天以上（慢活深度遊）"
]

col1, col2, col3 = st.columns(3)
with col1:
    origin_label = st.selectbox("出發機場", options=list(ORIGIN_OPTIONS.keys()), index=0)
    origin_text = ORIGIN_OPTIONS[origin_label]
with col2:
    dest_label = st.selectbox("目的地城市 / 機場", options=list(DEST_OPTIONS.keys()), index=0)
    if DEST_OPTIONS[dest_label] == "CUSTOM":
        dest_text = st.text_input("請輸入城市或機場名稱", value="沖繩")
    else:
        dest_text = DEST_OPTIONS[dest_label]
with col3:
    days_selection = st.selectbox("預計旅遊天數", options=DAYS_OPTIONS, index=0)

col4, col5 = st.columns(2)
with col4:
    flexible_time = st.selectbox(
        "出發時段偏好",
        options=[
            "近期出發（未來 1~3 個月推薦最舒適月份）",
            "全年度最佳月份（氣候好且避開人潮）",
            "春季出遊（3~5 月）",
            "秋季出遊（9~11 月）",
            "冬季出遊（12~2 月）"
        ],
        index=0
    )
with col5:
    hotel_level = st.selectbox(
        "每晚住宿預算",
        options=[
            "中價位商務/家庭型（約 NT$ 3,500 ~ 5,500 /晚）",
            "親子友善/星級飯店（約 NT$ 5,500 ~ 9,000 /晚）",
            "平價小資型（約 NT$ 2,500 ~ 3,500 /晚）",
            "頂級度假村（約 NT$ 9,000 以上 /晚）"
        ],
        index=0
    )

# ==========================================
# 核心執行
# ==========================================
if st.button("🚀 推薦最佳檔期、計算全家總預算 ＋ 產出完整行程", type="primary"):
    if not gemini_api_key:
        st.error("找不到 Gemini API 金鑰！")
    else:
        today = date.today()
        f_start = today + timedelta(days=30)
        f_end = today + timedelta(days=90)

        # 根據是否手動指定天數動態生成 Prompt 規範
        if "AI" in days_selection:
            days_instruction = f"""
- 使用者未預設天數，請你根據【{dest_text}】的景點分布與家庭成員（{adult_count} 大 {child_count} 小，包含幼童推車）的體力極限，主動評估並建議「最舒服、不趕場的最佳天數（如建議 X 天 Y 晚）」，並說明推薦此天數的考量原因。接著直接以該建議天數輸出完整行程與預算。
"""
        else:
            exact_days = days_selection.split(" ")[0]
            days_instruction = f"""
- 使用者已指定旅遊天數為【{exact_days}】，請精確規劃此天數的完整每日動線與住宿預算。
"""

        base_prompt = f"""
扮演資深親子旅遊顧問，以簡明扼要、高資訊密度的排版，為家庭規劃一趟直飛自由行。

【基本設定】
- 基準日：{today.strftime('%Y/%m/%d')}
- 出發/目的地：{origin_text} 至 {dest_text}
- 人數：{adult_count} 大 {child_count} 小（{child_age_label}，長輩：{senior_option}）
- 住宿要求：{hotel_level}
- 限制：{'全程推車無障礙動線' if need_stroller else '一般步行'}，{'起飛 09:00-15:00 直飛' if strict_flight_time else '彈性班機'}
{days_instruction}

【請直接輸出以下重點結構】
1. **天數與出發檔期評估**：
   - 說明此目的地最推薦的遊玩天數及原因（若使用者無預設天數）。
   - 若為近期請鎖定 {f_start.strftime('%Y/%m')}~{f_end.strftime('%Y/%m')}，列出均溫與避開人潮週別。
2. **直飛航班推薦**：適合家庭的航空公司與起降時段。
3. **住宿推薦**：推薦 2 間推車出入方便的飯店（附 Google 地圖搜尋格式：[飯店名](https://www.google.com/maps/search/?api=1&query=飯店名)）。
4. **💰 全家總預算表（TWD）**：條列機票、住宿、餐飲、交通、門票與預備金，給出總預算區間。
5. **每日精華動線**：每日上午 1 景點、中午後午睡充電、傍晚悠閒散步，景點與餐廳附 Google 地圖超連結 `[導航](https://www.google.com/maps/search/?api=1&query=景點名+{dest_text})`。
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
        label="📥 下載本次旅行手冊 (.md)",
        data=st.session_state.base_plan_content,
        file_name=f"{dest_text}_行程企劃手冊.md",
        mime="text/markdown"
    )

    # 雨天備案按鈕
    st.subheader("☔ 氣候應變：室內親子備案")
    if st.button("🔄 一鍵切換全室內備案", type="secondary"):
        ai_client = genai.Client(api_key=gemini_api_key)
        rain_prompt = f"請將剛才【{dest_text}】的行程替換為全室內備案（室內商場、水族館、推車友善），附 Google 地圖超連結。"
        rain_box = st.empty()
        rain_text = rain_box.write_stream(stream_gemini_fast(ai_client, rain_prompt))
        st.session_state.rainy_plan_content = rain_text

    # 行李打包清單
    with st.expander("🎒 行前打包清單（互動確認）", expanded=False):
        c1, c2, c3 = st.columns(3)
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

    # 延伸對話
    st.markdown("---")
    st.subheader("💬 AI 旅行顧問即時對話")
    for msg in st.session_state.chat_history[2:]:
        st.chat_message(msg["role"]).write(msg["parts"])

    user_query = st.chat_input("輸入你想微調的景點、天數或問題...")
    if user_query:
        st.chat_message("user").write(user_query)
        st.session_state.chat_history.append({"role": "user", "parts": user_query})

        with st.chat_message("assistant"):
            ai_client = genai.Client(api_key=gemini_api_key)
            formatted = [{"role": h["role"], "parts": [{"text": h["parts"]}]} for h in st.session_state.chat_history]
            chat_reply = st.write_stream(stream_gemini_fast(ai_client, formatted))
            st.session_state.chat_history.append({"role": "model", "parts": chat_reply})
