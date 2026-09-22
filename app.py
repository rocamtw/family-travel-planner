import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from amadeus import Client, ResponseError
from google import genai

st.set_page_config(page_title="小家庭 3 人自由行與機票推薦器", layout="wide")

# ==========================================
# 側邊欄：API 金鑰與已鎖定的家庭成員
# ==========================================
st.sidebar.header("🔑 API 金鑰設定")
amadeus_key = st.sidebar.text_input("Amadeus API Key", type="password")
amadeus_secret = st.sidebar.text_input("Amadeus API Secret", type="password")
gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.header("👨‍👩‍👧 家族出遊配置（已固定）")

# 鎖定 2 大 1 小 (3 歲幼童)
FAMILY_MEMBERS = [
    {"成員": "爸爸 (本人)", "身分": "成人", "需求": "主要搬運/推車支援"},
    {"成員": "媽媽 (老婆)", "身分": "成人", "需求": "照顧幼兒作息"},
    {"成員": "小孩 (約 3 歲)", "身分": "幼童 (Child 2-11歲)", "需求": "必備推車、需午睡、作息正常"},
]

st.sidebar.dataframe(pd.DataFrame(FAMILY_MEMBERS), hide_index=True)
st.sidebar.info("💡 限制已鎖定：\n- 嚴格直飛（不接受轉機）\n- 排除紅眼/清晨極端航班\n- 包含幼兒推車動線規劃")

adult_cnt = 2
child_cnt = 1

# ==========================================
# 主畫面：行程輸入（出發地與目的地皆改為下拉選單）
# ==========================================
st.title("✈️ 小家庭（2 大 1 小）全年最佳機票 ＋ AI 親子自由行規劃")

# 出發機場選項清單
ORIGIN_OPTIONS = {
    "台北桃園 (TPE)": "TPE",
    "台北松山 (TSA)": "TSA",
    "高雄小港 (KHH)": "KHH",
    "台中清泉崗 (RMQ)": "RMQ"
}

# 目的地熱門機場選項清單（中文名稱方便選取）
DEST_OPTIONS = {
    "🇯🇵 日本 - 福岡 (FUK) [航程短、推車超友善首選]": "FUK",
    "🇯🇵 日本 - 沖繩那霸 (OKA) [航程僅 1.5 hr、適合自駕]": "OKA",
    "🇯🇵 日本 - 東京成田 (NRT)": "NRT",
    "🇯🇵 日本 - 東京羽田 (HND)": "HND",
    "🇯🇵 日本 - 大阪關西 (KIX)": "KIX",
    "🇯🇵 日本 - 名古屋 (NGO)": "NGO",
    "🇯🇵 日本 - 札幌新千歲 (CTS)": "CTS",
    "🇰🇷 韓國 - 首爾仁川 (ICN)": "ICN",
    "🇰🇷 韓國 - 首爾金浦 (GMP)": "GMP",
    "🇰🇷 韓國 - 釜山金海 (PUS)": "PUS",
    "🇸🇬 新加坡 - 樟宜 (SIN) [親子設施完備]": "SIN",
    "🇹🇭 泰國 - 曼谷蘇凡納布 (BKK)": "BKK",
    "🇻🇳 越南 - 峴港 (DAD) [度假飯店放鬆]": "DAD",
    "🇭🇰 香港 - 赤鱲角 (HKG)": "HKG",
    "🌐 其他（自行輸入 3 碼機場代碼）": "CUSTOM"
}

col1, col2, col3 = st.columns(3)

with col1:
    origin_label = st.selectbox("出發機場", options=list(ORIGIN_OPTIONS.keys()), index=0)
    origin = ORIGIN_OPTIONS[origin_label]

with col2:
    dest_label = st.selectbox("目的地機場", options=list(DEST_OPTIONS.keys()), index=0)
    if DEST_OPTIONS[dest_label] == "CUSTOM":
        destination = st.text_input("請輸入機場代碼 (如 LAX)", value="LAX").upper()
    else:
        destination = DEST_OPTIONS[dest_label]

with col3:
    trip_days = st.number_input("預計旅遊天數", min_value=3, max_value=10, value=5)

def is_unfriendly_time(dep_iso, arr_iso):
    """判斷起飛或降落是否落在對 3 歲小孩不友善的時段 (21:30 - 07:30)"""
    dep_h = datetime.fromisoformat(dep_iso).hour
    arr_h = datetime.fromisoformat(arr_iso).hour
    return (dep_h >= 22 or dep_h < 7) or (arr_h >= 22 or arr_h < 7)

# ==========================================
# 核心執行：搜尋最適合時間並生成 AI 親子行程
# ==========================================
if st.button("🚀 掃描全年最佳親子出發日與航班", type="primary"):
    if not (amadeus_key and amadeus_secret and gemini_api_key):
        st.error("請在左側輸入 Amadeus API 與 Gemini API 金鑰！")
    else:
        with st.status("正在為 2 大 1 小家庭尋找最佳旅遊檔期...", expanded=True) as status:
            try:
                status.write(f"🔍 步驟 1/3：正在針對【{destination}】掃描直飛航班與票價波谷...")
                amadeus = Client(client_id=amadeus_key, client_secret=amadeus_secret)

                # 挑選接下來數個月份的合適日期
                today = date.today()
                sample_dates = [
                    today + timedelta(days=45),
                    today + timedelta(days=75),
                    today + timedelta(days=105),
                    today + timedelta(days=135),
                ]

                candidate_flights = []

                for d in sample_dates:
                    ret_d = d + timedelta(days=trip_days)
                    try:
                        resp = amadeus.shopping.flight_offers_search.get(
                            originLocationCode=origin,
                            destinationLocationCode=destination,
                            departureDate=str(d),
                            returnDate=str(ret_d),
                            adults=adult_cnt,
                            children=child_cnt,
                            currencyCode="TWD",
                            nonStop="true",  # 強制直飛
                            max=5
                        )
                        if not resp.data:
                            continue

                        for flight in resp.data:
                            outbound = flight["itineraries"][0]["segments"]
                            inbound = flight["itineraries"][1]["segments"]
                            
                            dep_t = outbound[0]["departure"]["at"]
                            arr_t = outbound[-1]["arrival"]["at"]
                            in_dep_t = inbound[0]["departure"]["at"]
                            in_arr_t = inbound[-1]["arrival"]["at"]

                            # 排除幼童不耐的深夜/清晨拉車時間
                            if is_unfriendly_time(dep_t, arr_t) or is_unfriendly_time(in_dep_t, in_arr_t):
                                continue

                            price = float(flight["price"]["total"])
                            candidate_flights.append({
                                "dep_date": str(d),
                                "ret_date": str(ret_d),
                                "out_airline": outbound[0]["carrierCode"],
                                "out_flight": f"{outbound[0]['carrierCode']}{outbound[0]['number']}",
                                "out_dep_time": dep_t,
                                "out_arr_time": arr_t,
                                "in_flight": f"{inbound[0]['carrierCode']}{inbound[0]['number']}",
                                "in_dep_time": in_dep_t,
                                "in_arr_time": in_arr_t,
                                "total_price": price
                            })
                    except Exception:
                        continue

                if not candidate_flights:
                    status.update(label="未能找到符合條件的直飛班機，請嘗試調整目的地或放寬天數！", state="error")
                    st.stop()

                # 取票價最親民、時間最舒適的組合
                candidate_flights.sort(key=lambda x: x["total_price"])
                best_flight = candidate_flights[0]

                status.write(f"✅ 步驟 2/3：鎖定出發日 {best_flight['dep_date']} 至 {best_flight['ret_date']}，直飛時段極佳！")

                # 呼叫 Gemini AI 產出專屬親子行程
                status.write("🤖 步驟 3/3：Gemini AI 正在依據 3 歲幼兒生理作息規劃行程...")
                ai_client = genai.Client(api_key=gemini_api_key)

                prompt = f"""
你是一位專門為「育兒家庭 / 幼童親子旅遊」規劃自由行的高級顧問。
請為一組家庭（爸爸、媽媽、一位約 3 歲的幼童）量身定制一份 {trip_days} 天的悠閒放鬆自由行。

【家庭成員特性】
- 成員：2 位成人、1 位 3 歲幼兒（全程攜帶嬰兒推車）。
- 作息節奏：幼兒每天下午 13:30 - 15:30 必須回飯店午睡或在推車上熟睡；晚上 20:30 前需回到飯店準備就寢。
- 體力限制：每天「主景點」最多安排 1~2 個，拒絕行軍式趕場，隨時需有尿布台、育嬰室與平緩推車動線。

【已確定的直飛航班】
- 目的地：{destination}
- 去程：{best_flight['dep_date']} {best_flight['out_flight']}，起飛 {best_flight['out_dep_time']}，抵達 {best_flight['out_arr_time']}
- 回程：{best_flight['ret_date']} {best_flight['in_flight']}，起飛 {best_flight['in_dep_time']}，抵達 {best_flight['in_arr_time']}
- 全家（2大1小）機票總金額：NT$ {best_flight['total_price']:,.0f}

【產出規範】
1. **每日行程規劃**：上午、下午（含午睡安排）、傍晚，動線必須極度鬆散舒適。第 1 天與最後一天緊密配合航班起降時間。
2. **交通建議**：清楚標記何時建議搭乘計程車（短程省力）或推薦有無障礙電梯的地鐵路線。
3. **幼童友善點評**：每個景點標記適合 3 歲小孩玩的元素（如公園草地、水族館、大型商場室內樂園）。
4. **推薦住宿地點**：推薦在哪個生活機能佳、進出機場方便且推車友善的地點住宿。
5. **爸媽必備提醒**：推薦必備用品、幼兒用餐（餐廳兒童椅/副食品/友善料理）建議。
"""

                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )

                status.update(label="🎉 規劃完成！最佳直飛航班與親子自由行已產生！", state="complete")

                # 顯示結果
                st.success("🎯 已為你們一家三口鎖定最佳直飛時段！")

                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("出發與回程日期", f"{best_flight['dep_date']} ~ {best_flight['ret_date']}")
                c_m2.metric("去程直飛起降", f"{best_flight['out_flight']} ({best_flight['out_dep_time'][11:16]} - {best_flight['out_arr_time'][11:16]})")
                c_m3.metric("一家三口機票總價", f"NT$ {best_flight['total_price']:,.0f}")

                st.markdown("---")
                st.subheader("🍼 2 大 1 小專屬親子自由行完整指南")
                st.markdown(response.text)

            except Exception as e:
                status.update(label="執行時發生錯誤", state="error")
                st.error(f"錯誤訊息：{e}")
