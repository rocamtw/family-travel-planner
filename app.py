from datetime import date, timedelta
import time
from google import genai
from google.genai.errors import APIError
import streamlit as st

st.set_page_config(
    page_title="家庭自由行與預算智囊（旗艦防錯版）", layout="wide"
)

# ==========================================
# 自動從 Secrets 讀取金鑰
# ==========================================
gemini_api_key = st.secrets.get("GEMINI_KEY", "")

st.title("✈️ 家庭專屬 最佳機票、住宿預算試算 ＋ AI 對話行程智囊")

if not gemini_api_key:
  st.warning(
      "⚠️ 系統尚未在 Streamlit Secrets 偵測到 GEMINI_KEY，請至後台 Settings ->"
      " Secrets 完成設定。"
  )

# ==========================================
# 初始化 Session State
# ==========================================
if "chat_history" not in st.session_state:
  st.session_state.chat_history = []
if "plan_generated" not in st.session_state:
  st.session_state.plan_generated = False
if "base_plan_content" not in st.session_state:
  st.session_state.base_plan_content = ""
if "rainy_plan_content" not in st.session_state:
  st.session_state.rainy_plan_content = ""


# 通用呼叫函式：具備 429 配額重試、503 備援與 Search 自動降級機制
def generate_content_with_fallback(
    client, contents_input, enable_search=False
):
  models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

  # 建立調用組合：若有開啟 search，遇 429 時會自動退回一般無 search 模式
  configs = []
  if enable_search:
    configs.append({"tools": [{"google_search": {}}]})
  configs.append({})  # 純模型標準模式（保底）

  for model_name in models_to_try:
    for call_config in configs:
      for attempt in range(2):  # 最多重試 2 次
        try:
          resp = client.models.generate_content(
              model=model_name, contents=contents_input, config=call_config
          )
          return resp.text, None
        except APIError as e:
          err_msg = str(e)
          # 遇 429 配額限制或 503 忙碌，短暫暫停退避重試
          if e.code == 429 or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            time.sleep(2.5)
            continue
          elif e.code == 503 or "503" in err_msg:
            time.sleep(1.5)
            continue
          else:
            break
        except Exception:
          break
  return (
      None,
      "免費 API 瞬間請求流量較大（429 配額保護），請稍候 10~15 秒後再次點擊！",
  )


# ==========================================
# 區塊 1：彈性成員配置
# ==========================================
with st.expander("👨‍👩‍👧‍👦 成員配置與體力需求（點此自訂）", expanded=True):
  col_m1, col_m2, col_m3, col_m4 = st.columns(4)

  with col_m1:
    adult_count = st.selectbox("成人人數", options=[1, 2, 3, 4, 5, 6], index=1)
  with col_m2:
    child_count = st.selectbox("小孩人數", options=[0, 1, 2, 3, 4], index=1)
  with col_m3:
    if child_count > 0:
      child_age_label = st.selectbox(
          "小孩年齡分佈",
          options=[
              "幼童 (約 2~3 歲，需午睡與推車)",
              "學齡前 (4~6 歲，體力中等、需適度休息)",
              "學齡兒童 (7~12 歲，活動力強)",
              "嬰幼兒 (未滿 2 歲，需泡奶/副食品)",
          ],
          index=0,
      )
    else:
      child_age_label = "無小孩同行"
  with col_m4:
    senior_option = st.selectbox(
        "是否有長輩同行？",
        options=[
            "無長輩",
            "有長輩 (65歲以上，需多坐多休息、早睡)",
            "有行動不便長輩 (需輪椅)",
        ],
        index=0,
    )

  col_req1, col_req2 = st.columns(2)
  with col_req1:
    need_stroller = st.checkbox(
        "需攜帶嬰兒推車（要求全程平緩動線、電梯優先）",
        value=True if child_count > 0 else False,
    )
  with col_req2:
    strict_flight_time = st.checkbox(
        "航班嚴格避開紅眼與極端清晨（限 09:00 - 15:00 起飛）", value=True
    )

# ==========================================
# 區塊 2：目的地、時段與飯店偏好
# ==========================================
ORIGIN_OPTIONS = {
    "台北桃園 (TPE)": "TPE (台北桃園)",
    "台北松山 (TSA)": "TSA (台北松山)",
    "高雄小港 (KHH)": "KHH (高雄小港)",
    "台中清泉崗 (RMQ)": "RMQ (台中清泉崗)",
}

DEST_OPTIONS = {
    "🇯🇵 日本 - 福岡 (FUK) [航程短、推車超友善首選]": "福岡 (FUK)",
    "🇯🇵 日本 - 沖繩那霸 (OKA) [航程僅 1.5 hr、適合自駕]": "沖繩 (OKA)",
    "🇯🇵 日本 - 東京成田 (NRT)": "東京成田 (NRT)",
    "🇯🇵 日本 - 東京羽田 (HND)": "東京羽田 (HND)",
    "🇯🇵 日本 - 大阪關西 (KIX)": "大阪關西 (KIX)",
    "🇯🇵 日本 - 名古屋 (NGO)": "名古屋 (NGO)",
    "🇯🇵 日本 - 札幌新千歲 (CTS)": "札幌 (CTS)",
    "🇰🇷 韓國 - 首爾仁川 (ICN)": "首爾仁川 (ICN)",
    "🇰🇷 韓國 - 首爾金浦 (GMP)": "首爾金浦 (GMP)",
    "🇰🇷 韓國 - 釜山金海 (PUS)": "釜山 (PUS)",
    "🇸🇬 新加坡 - 樟宜 (SIN) [親子設施極佳]": "新加坡 (SIN)",
    "🇹🇭 泰國 - 曼谷蘇凡納布 (BKK)": "曼谷 (BKK)",
    "🇻🇳 越南 - 峴港 (DAD) [度假飯店放鬆]": "峴港 (DAD)",
    "🇭🇰 香港 - 赤鱲角 (HKG)": "香港 (HKG)",
    "🌐 其他（自行輸入）": "CUSTOM",
}

FLEXIBLE_TIME_OPTIONS = [
    "近期出發（由系統依今日起算未來 1~3 個月推薦具體月份與週末）",
    "全年度皆可（請推薦整年度避開極端氣候與票價最划算的 2~3 個黃金檔期）",
    "春季出遊（3 月 ~ 5 月，賞花、氣候溫和）",
    "秋季出遊（9 月 ~ 11 月，避開酷暑、秋高氣爽）",
    "冬季出遊（12 月 ~ 2 月，避寒或賞雪體驗）",
    "連假前後避人潮時段（避開連續假期天價機票與人擠人）",
]

HOTEL_LEVEL_OPTIONS = [
    (
        "中價位商務/家庭型（乾淨、交通極佳、推車好進出，約 NT$ 3,500 ~ 5,500"
        " /晚）"
    ),
    (
        "親子友善/星級飯店（空間大、近車站、備品齊全，約 NT$ 5,500 ~ 9,000"
        " /晚）"
    ),
    "平價小資型（空間精簡但乾淨，約 NT$ 2,500 ~ 3,500 /晚）",
    "頂級度假村 / 溫泉飯店（設施豐富、餐食極佳，約 NT$ 9,000 以上 /晚）",
]

col1, col2, col3 = st.columns(3)
with col1:
  origin_label = st.selectbox(
      "出發機場", options=list(ORIGIN_OPTIONS.keys()), index=0
  )
  origin_text = ORIGIN_OPTIONS[origin_label]
with col2:
  dest_label = st.selectbox(
      "目的地城市 / 機場", options=list(DEST_OPTIONS.keys()), index=0
  )
  if DEST_OPTIONS[dest_label] == "CUSTOM":
    dest_text = st.text_input("請輸入城市或機場名稱", value="沖繩")
  else:
    dest_text = DEST_OPTIONS[dest_label]
with col3:
  trip_days = st.number_input(
      "預計旅遊天數", min_value=3, max_value=10, value=5
  )

col4, col5 = st.columns(2)
with col4:
  flexible_time = st.selectbox(
      "彈性出發時段偏好", options=FLEXIBLE_TIME_OPTIONS, index=0
  )
with col5:
  hotel_level = st.selectbox(
      "偏好的住宿檔次與每晚預算", options=HOTEL_LEVEL_OPTIONS, index=0
  )

# 可選開關：預設關閉聯網，避免撞到 Search 配額
use_live_search = st.checkbox(
    "啟用 Google 即時聯網搜尋（若遇到 429 配額錯誤時可取消勾選以提升穩定度）",
    value=False,
)

# ==========================================
# 核心執行按鈕：產出主行程與預算
# ==========================================
if st.button("🚀 推薦最佳檔期、計算全家總預算 ＋ 產出完整行程", type="primary"):
  if not gemini_api_key:
    st.error(
        "找不到 Gemini API 金鑰，請先在 Streamlit 後台 Settings -> Secrets"
        " 中設定 GEMINI_KEY！"
    )
  else:
    today = date.today()
    future_1m = today + timedelta(days=30)
    future_3m = today + timedelta(days=90)

    member_desc = f"{adult_count} 位成人"
    if child_count > 0:
      member_desc += f"、{child_count} 位小孩（{child_age_label}）"
    if senior_option != "無長輩":
      member_desc += f"、同行長輩：{senior_option}"
    if need_stroller:
      member_desc += "，需全程推嬰兒推車"

    with st.spinner(
        f"正在為【{member_desc}】試算機票/住宿總預算，並生成【{dest_text}】客製化行程..."
    ):
      ai_client = genai.Client(api_key=gemini_api_key)

      base_prompt = f"""
你是一位專門為「家庭出遊（幼童同行）」提供全方位旅遊顧問服務的資深專家。
請規劃一份包含【全行程各項花費預抓與總預算試算】與【{trip_days} 天詳細行程】的專業企劃書。

【時間基準】
- 今日基準日：{today.strftime('%Y 年 %m 月 %d 日')}
- 若為「近期出發」，請嚴格限定在【{future_1m.strftime('%Y 年 %m 月')} 至 {future_3m.strftime('%Y 年 %m 月')}】之間推薦，切勿推薦過去月份！

【成員與旅遊需求】
- 出發地：{origin_text} ｜ 目的地：{dest_text} ｜ 天數：{trip_days} 天（{trip_days - 1} 晚）
- 成員：{adult_count} 位成人、{child_count} 位小孩（{child_age_label}）、長輩：{senior_option}
- 住宿檔次要求：{hotel_level}
- 限制條件：{'全程推車與無障礙動線' if need_stroller else '一般步行動線'}，{'起飛限制 09:00 - 15:00 直飛' if strict_flight_time else '彈性時段'}

【企劃輸出規範】
1. **最佳出發時段評估**：針對幼童與長輩體感，推薦 2 個近期最舒適且避開人潮與天價機票的檔期。
2. **直飛航班推薦**：推薦具體航空公司與合適起飛時段。
3. **住宿推薦與房型建議**：
   - 推薦 2~3 間適合該家庭結構的具體飯店或區域（備註推車電梯直達、生活機能）。
   - 包含超連結格式：例如 `[在 Google 地圖查看飯店](https://www.google.com/maps/search/?api=1&query=飯店名稱)`。
4. **💰 全行程花費預估表（全家 {adult_count} 大 {child_count} 小 總花費，以新台幣 TWD 計算）**：
   請列出清晰的預算彙整表格，包含：
   - 直飛來回機票總花費
   - {trip_days - 1} 晚飯店住宿總預估
   - 當地餐飲費用（以家庭舒適聚餐計）
   - 當地交通費（含地鐵、機場快線與必要的計程車接駁）
   - 門票與活動娛樂費
   - 預備金/雜支
   👉 **結算：全家 {trip_days} 天總預算區間（最低 ~ 寬裕）**。
5. **{trip_days} 天每日詳細行程**：
   - 上午 1 景點、中午舒適餐廳、下午 13:30 - 15:30 嚴格保留午睡或回飯店充電、傍晚悠閒活動、20:30 回飯店。
   - 每個景點與主要推薦餐廳名稱後，請自動附上 Google 地圖超連結，格式為：`[📍導航](https://www.google.com/maps/search/?api=1&query=景點或餐廳名稱+{dest_text})`。
   - 標記各點的推車友善度與無障礙電梯位置。
"""

      plan_text, err = generate_content_with_fallback(
          ai_client, base_prompt, enable_search=use_live_search
      )
      if plan_text:
        st.session_state.base_plan_content = plan_text
        st.session_state.plan_generated = True
        st.session_state.rainy_plan_content = ""
        st.session_state.chat_history = [
            {"role": "user", "parts": base_prompt},
            {"role": "model", "parts": plan_text},
        ]
      else:
        st.error(err)

# ==========================================
# 顯示結果與四大強化功能
# ==========================================
if st.session_state.plan_generated:
  st.markdown("---")

  # 功能 3：一鍵下載旅遊企劃書
  st.download_button(
      label="📥 下載本次旅行手冊 (.md / 記事本格式)",
      data=st.session_state.base_plan_content,
      file_name=f"{dest_text}_{trip_days}天親子自由行手冊.md",
      mime="text/markdown",
  )

  # 主行程呈現（含 Google Maps 導航連結）
  st.markdown(st.session_state.base_plan_content)

  # ==========================================
  # 功能 2：雨天／突發狀況一鍵室內備案
  # ==========================================
  st.markdown("---")
  st.subheader("☔ 氣候應變：雨天 / 小孩體力不佳 室內備案專區")
  col_rain_btn, _ = st.columns([2, 5])
  with col_rain_btn:
    if st.button("🔄 一鍵切換全室內親子備案行程", type="secondary"):
      with st.spinner("正在規劃全室內大型商場、水族館與推車友善設施..."):
        ai_client = genai.Client(api_key=gemini_api_key)
        rain_prompt = (
            "請針對剛才為我們規劃的行程，提供一套完整的【全室內雨天替代備案】。"
            f"針對目的地【{dest_text}】，將所有戶外景點替換成大商場室內樂園、水族館、大型科學館或室內推車平緩設施，並附上"
            " Google Maps 連結與哺乳室標註。"
        )
        rain_resp_text, rain_err = generate_content_with_fallback(
            ai_client, rain_prompt, enable_search=False
        )
        if rain_resp_text:
          st.session_state.rainy_plan_content = rain_resp_text
        else:
          st.error(f"備案生成錯誤：{rain_err}")

  if st.session_state.rainy_plan_content:
    st.info("🌧️ 以下為雨天 / 室內友善備用方案：")
    st.markdown(st.session_state.rainy_plan_content)

  # ==========================================
  # 功能 4：幼童出遊專屬行前清單（Checklist）
  # ==========================================
  st.markdown("---")
  with st.expander(
      "🎒 3 歲幼兒與家庭專屬【行前打包清單】（互動式勾選）", expanded=True
  ):
    st.caption("出發前依序確認，打勾後不怕遺漏關鍵備品：")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
      st.markdown("**🩺 醫藥與護理**")
      st.checkbox("幼兒退燒藥水 / 塞劑", value=False)
      st.checkbox("常備止瀉、感冒藥水", value=False)
      st.checkbox("防蚊液、蚊蟲叮咬止癢膏", value=False)
      st.checkbox("體溫計、OK繃、消毒棉片", value=False)
      st.checkbox("護照正本（效期 6 個月以上）", value=False)

    with col_c2:
      st.markdown("**🛒 推車與移動**")
      st.checkbox("推車專用雨罩（防風防雨必備）", value=False)
      st.checkbox("輕便型登機推車 / 推車背帶", value=False)
      st.checkbox("推車掛勾與大容量置物袋", value=False)
      st.checkbox("幼兒薄毯 / 小外套（機上與商場冷氣房）", value=False)
      st.checkbox("隨身濕紙巾 / 酒精濕巾多包", value=False)

    with col_c3:
      st.markdown("**🍼 飲食與安撫**")
      st.checkbox("拋棄式圍兜、食物剪刀", value=False)
      st.checkbox("常溫寶寶粥 / 幼兒隨身米餅", value=False)
      st.checkbox("幼兒水壺（過安檢後裝溫水）", value=False)
      st.checkbox("機上安撫貼紙書 / 離線卡通影片", value=False)
      st.checkbox("尿布（按天數 × 5 片計算）", value=False)

  # ==========================================
  # 延伸對話互動（Chat 系統）
  # ==========================================
  st.markdown("---")
  st.subheader("💬 專屬 AI 旅行顧問線上對話（隨時微調行程）")

  for msg in st.session_state.chat_history[2:]:
    if msg["role"] == "user":
      st.chat_message("user").write(msg["parts"])
    else:
      st.chat_message("assistant").write(msg["parts"])

  user_query = st.chat_input("請輸入你想調整的項目或延伸問題...")
  if user_query:
    st.chat_message("user").write(user_query)
    st.session_state.chat_history.append({"role": "user", "parts": user_query})

    with st.chat_message("assistant"):
      with st.spinner("AI 顧問正在為你調整企劃與試算..."):
        ai_client = genai.Client(api_key=gemini_api_key)
        formatted_contents = []
        for h in st.session_state.chat_history:
          formatted_contents.append(
              {"role": h["role"], "parts": [{"text": h["parts"]}]}
          )

        chat_reply, chat_err = generate_content_with_fallback(
            ai_client, formatted_contents, enable_search=False
        )
        if chat_reply:
          st.write(chat_reply)
          st.session_state.chat_history.append(
              {"role": "model", "parts": chat_reply}
          )
        else:
          st.error(f"對話產生錯誤：{chat_err}")
