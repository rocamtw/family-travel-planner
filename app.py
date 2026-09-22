from datetime import date, timedelta
import time
from google import genai
from google.genai.errors import APIError
import pandas as pd
import streamlit as st

st.set_page_config(page_title="家庭親子自由行與機票推薦器", layout="wide")

# ==========================================
# 自動從 Secrets 讀取金鑰
# ==========================================
gemini_api_key = st.secrets.get("GEMINI_KEY", "")

st.title("✈️ 家庭專屬 全年最佳機票 ＋ AI 自由行客製化規劃")

if not gemini_api_key:
  st.warning(
      "⚠️ 系統尚未在 Streamlit Secrets 偵測到 GEMINI_KEY，請至後台 Settings ->"
      " Secrets 完成設定。"
  )

# ==========================================
# 區塊 1：彈性成員配置（下拉式選單）
# ==========================================
with st.expander("👨‍👩‍👧‍👦 成員配置與體力需求（點此自訂）", expanded=True):
  col_m1, col_m2, col_m3, col_m4 = st.columns(4)

  with col_m1:
    adult_count = st.selectbox(
        "成人人數",
        options=[1, 2, 3, 4, 5, 6],
        index=1,  # 預設 2 大
        help="包含爸媽等一般成人",
    )
  with col_m2:
    child_count = st.selectbox(
        "小孩人數",
        options=[0, 1, 2, 3, 4],
        index=1,  # 預設 1 小
        help="未滿 12 歲孩童",
    )
  with col_m3:
    if child_count > 0:
      child_age_label = st.selectbox(
          "小孩年齡主要分佈",
          options=[
              "幼童 (約 2~3 歲，需午睡與推車)",
              "學齡前 (4~6 歲，體力中等、需適度休息)",
              "學齡兒童 (7~12 歲，活動力強)",
              "嬰幼兒 (未滿 2 歲，需熱水泡奶/副食品)",
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
            "有行動不便長輩 (需輪椅輔助)",
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
# 區塊 2：行程與彈性日期設定（即時日期連動）
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

col1, col2, col3, col4 = st.columns(4)

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
  flexible_time = st.selectbox(
      "彈性出發時段偏好", options=FLEXIBLE_TIME_OPTIONS, index=0
  )

with col4:
  trip_days = st.number_input(
      "預計旅遊天數", min_value=3, max_value=10, value=5
  )

# ==========================================
# 核心執行按鈕（注入即時當前日期）
# ==========================================
if st.button("🚀 推薦最佳出發檔期與航班 ＋ 產出專屬自由行行程", type="primary"):
  if not gemini_api_key:
    st.error(
        "找不到 Gemini API 金鑰，請先在 Streamlit 後台 Settings -> Secrets"
        " 中設定 GEMINI_KEY！"
    )
  else:
    # 即時計算今日日期與未來 1~3 個月的精確日曆範圍
    today = date.today()
    future_1m = today + timedelta(days=30)
    future_3m = today + timedelta(days=90)

    member_desc = f"{adult_count} 位成人"
    if child_count > 0:
      member_desc += f"、{child_count} 位小孩（{child_age_label}）"
    if senior_option != "無長輩":
      member_desc += f"、同行長輩情況：{senior_option}"
    if need_stroller:
      member_desc += "，需全程推嬰兒推車"

    with st.spinner(
        f"正在為【{member_desc}】全面分析【{dest_text}】的最佳檔期與行程規劃..."
    ):
      ai_client = genai.Client(api_key=gemini_api_key)

      prompt = f"""
你是一位專門為「家庭出遊（幼童/長輩同行）」提供深度旅遊諮詢的資深顧問。
請根據以下明確的當前系統真實日期、家庭成員結構與彈性出發偏好，規劃一份量身打造的機票建議與 {trip_days} 天自由行完整企劃。

【重要時間基準】
- **今天是真實日期**：{today.strftime('%Y 年 %m 月 %d 日')}
- 若使用者選擇近期出發，嚴格限定在未來 1~3 個月內，即：【{future_1m.strftime('%Y 年 %m 月')} 至 {future_3m.strftime('%Y 年 %m 月')}】之間推薦，絕對不可推薦已經過去的月份或半年前後的無關季節！

【出發與目的地】
- 出發地點：{origin_text}
- 目的地點：{dest_text}
- 預計天數：{trip_days} 天
- 彈性時段偏好：{flexible_time}

【旅客成員配置】
- 成人：{adult_count} 位
- 孩童：{child_count} 位（屬性：{child_age_label}）
- 長輩狀況：{senior_option}
- 嬰兒推車 / 行動需求：{'需全程考量嬰兒推車或無障礙動線（避開樓梯、陡坡，指定電梯出口）' if need_stroller else '一般步行動線'}
- 航班舒適度要求：{'起飛嚴格限制在 09:00 - 15:00 之間，不搭紅眼與極早清晨拉車' if strict_flight_time else '彈性時段'}

【企劃輸出規範】
1. **最佳出發檔期與氣候深度評估**：
   - 必須嚴格以今日（{today.strftime('%Y 年 %m 月 %d 日')}）為基準！
   - 若為「近期出發」，請在 {future_1m.strftime('%Y 年 %m 月')} 至 {future_3m.strftime('%Y 年 %m 月')} 之間推薦 2 個最理想的出發週別或具體建議區間。
   - 針對同行小孩（{child_age_label}）與長輩體感，說明該期間預計的均溫、降雨機率，並說明如何避開人潮與昂貴票價波峰。
2. **直飛航班推薦與預算估算**：
   - 推薦直飛該航點的具體航空公司與航班時段（如去程 09:00~11:00 起飛、回程 14:00~16:00 起飛）。
   - 估算全家【{adult_count} 大 {child_count} 小】的來回直飛機票總預算區間（以新台幣 TWD 計）。
3. **客製化 {trip_days} 天每日行程**：
   - 節奏控制：上午 1 個精華景點，中午舒適餐廳；下午 13:30 - 15:30 嚴格安排「午睡/飯店小憩或平坦綠地散步」；傍晚輕鬆採買或景點；20:30 前回飯店就寢。
   - 動線友善：標註設施（推車友善程度、有無哺乳室/尿布台、短程是否建議搭計程車）。
4. **推車友善住宿區域推薦**：
   - 推薦 1~2 個最方便的地鐵站或住宿區域（有電梯直達、有機場直達車或短程計程車友善）。
5. **爸媽/照顧者專屬叮嚀**：
   - 針對同行小孩年齡的行前必備清單與餐廳挑選守則。

請使用清晰的 Markdown 標題、重點粗體與表格呈現完整企劃書。
"""

      models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
      success = False

      for model_name in models_to_try:
        try:
          response = ai_client.models.generate_content(
              model=model_name, contents=prompt
          )
          st.success(
              f"🎉 規劃完成！（基準日：{today.strftime('%Y/%m/%d')} ｜ 模型：{model_name}）"
          )
          st.markdown(response.text)
          success = True
          break
        except APIError as e:
          if e.code == 503 or "503" in str(e):
            time.sleep(1)
            continue
          else:
            st.error(f"執行時發生錯誤：{e}")
            break
        except Exception as e:
          st.error(f"執行時發生錯誤：{e}")
          break

      if not success:
        st.warning(
            "⚠️ 目前伺服器瞬間流量較大，請稍候 10 秒後再次點擊按鈕重試！"
        )
