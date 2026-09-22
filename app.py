import streamlit as st
import pandas as pd
from google import genai

st.set_page_config(page_title="小家庭 3 人自由行與機票推薦器", layout="wide")

# ==========================================
# 自動從 Secrets 讀取金鑰
# ==========================================
gemini_api_key = st.secrets.get("GEMINI_KEY", "")

st.title("✈️ 小家庭（2 大 1 小）全年最佳機票 ＋ AI 親子自由行規劃")

if not gemini_api_key:
    st.warning("⚠️ 系統尚未在 Streamlit Secrets 偵測到 GEMINI_KEY，請至後台 Settings -> Secrets 完成設定。")

# ==========================================
# 家族成員配置（已鎖定）
# ==========================================
with st.expander("👨‍👩‍👧 查看本次家庭成員與行程偏好（已鎖定）", expanded=False):
    FAMILY_MEMBERS = [
        {"成員": "爸爸 (本人)", "身分": "成人", "需求": "主要搬運、推車支援"},
        {"成員": "媽媽 (老婆)", "身分": "成人", "需求": "照顧幼兒作息"},
        {"成員": "小孩 (約 3 歲)", "身分": "幼童 (3歲)", "需求": "必備推車、需午睡、作息正常"},
    ]
    st.dataframe(pd.DataFrame(FAMILY_MEMBERS), hide_index=True)
    st.info("🎯 系統原則：嚴格直飛 ｜ 排除紅眼與清晨 ｜ 每日下午保留午睡 ｜ 推車電梯平緩動線")

# ==========================================
# 行程輸入選項（下拉選單）
# ==========================================
ORIGIN_OPTIONS = {
    "台北桃園 (TPE)": "TPE (台北桃園)",
    "台北松山 (TSA)": "TSA (台北松山)",
    "高雄小港 (KHH)": "KHH (高雄小港)",
    "台中清泉崗 (RMQ)": "RMQ (台中清泉崗)"
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
    "🌐 其他（自行輸入）": "CUSTOM"
}

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
    trip_days = st.number_input("預計旅遊天數", min_value=3, max_value=10, value=5)

# ==========================================
# 核心執行按鈕
# ==========================================
if st.button("🚀 推薦全年最佳時段與直飛航班 ＋ 產出 AI 行程", type="primary"):
    if not gemini_api_key:
        st.error("找不到 Gemini API 金鑰，請先在 Streamlit 後台 Settings -> Secrets 中設定 GEMINI_KEY！")
    else:
        with st.spinner(f"正在為一家三口全面分析【{dest_text}】的最佳出遊月份、直飛航班與親子自由行企劃..."):
            try:
                ai_client = genai.Client(api_key=gemini_api_key)

                prompt = f"""
你是一位專門為「育兒家庭（幼童同行）」提供旅遊顧問服務的專家。
請為一組家庭（爸爸、媽媽、一位約 3 歲的幼童）規劃一次出遊。

【出遊基本條件】
- 出發地：{origin_text}
- 目的地：{dest_text}
- 預計天數：{trip_days} 天
- 成員：2 位成人、1 位 3 歲幼兒（全程攜帶嬰兒推車）

【核心限制】
1. **全年最適合時間與氣候**：
   - 避開當地盛夏酷暑（幼兒容易中暑）、嚴寒、雨季或颱風季，推薦出「全年度最舒服、最適合 3 歲小孩體感的 2~3 個最佳月份區間」。
   - 同時標註這幾個月份的機票價格趨勢與避開人潮建議。
2. **航班直飛建議**：
   - 推薦最適合該家庭的真實航空公司與班次（如長榮、華航、星宇、國泰或日系航空）。
   - 起飛時間嚴格限制在 09:00 - 15:00 之間（拒絕清晨 07:00 前拉車，拒絕 21:00 後抵達），估算「2 大 1 小」的平均機票總預算（TWD）。
3. **專屬親子每日行程（{trip_days} 天）**：
   - 每日節奏：上午 1 個景點，中午舒服用餐，下午 13:30 - 15:30 必須安排「回飯店午休」或「在推車上熟睡的平坦散步道」，傍晚/晚間輕鬆行程，20:30 前回飯店。
   - 動線友善：標註電梯動線、有無障礙坡道、是否有乾淨尿布台與育嬰室。
4. **住宿與交通配置**：
   - 推薦住在哪個地鐵站周邊最推車友善、去機場最方便。
   - 標明何時建議搭乘計程車（短程免搬推車）。
5. **打包與行前注意事項**：針對 3 歲幼兒必備的用品與餐廳挑選提醒。

請以清晰排版（多用條列與表格）呈現完整企劃書。
"""

                response = ai_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt
                )

                st.success("🎉 已完成全年度最佳檔期分析與專屬親子自由行企劃！")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"執行時發生錯誤：{e}")
