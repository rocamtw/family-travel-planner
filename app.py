import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from amadeus import Client, ResponseError
from google import genai

st.set_page_config(page_title="家族全年最佳機票與 AI 自由行規劃器", layout="wide")

# ==========================================
# 側邊欄：金鑰與成員輸入
# ==========================================
st.sidebar.header("🔑 API 金鑰設定")
amadeus_key = st.sidebar.text_input("Amadeus API Key", type="password")
amadeus_secret = st.sidebar.text_input("Amadeus API Secret", type="password")
gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.header("👨‍👩‍👧‍👦 家族成員配置")

default_family = [
    {"姓名": "爸爸", "身分": "長輩 (65歲以上)", "不轉機": True, "不搭紅眼": True, "輪椅/推車": False},
    {"姓名": "媽媽", "身分": "長輩 (65歲以上)", "不轉機": True, "不搭紅眼": True, "輪椅/推車": False},
    {"姓名": "本人", "身分": "成人", "不轉機": False, "不搭紅眼": False, "輪椅/推車": False},
    {"姓名": "配偶", "身分": "成人", "不轉機": False, "不搭紅眼": False, "輪椅/推車": False},
    {"姓名": "小孩", "身分": "孩童 (5歲以下)", "不轉機": True, "不搭紅眼": True, "輪椅/推車": True},
]

df_members = st.sidebar.data_editor(
    pd.DataFrame(default_family),
    num_rows="dynamic",
    use_container_width=True
)

# 統計成員特性
adult_cnt = sum(1 for _, r in df_members.iterrows() if "成人" in r["身分"] or "長輩" in r["身分"])
child_cnt = sum(1 for _, r in df_members.iterrows() if "孩童" in r["身分"])
senior_cnt = sum(1 for _, r in df_members.iterrows() if "長輩" in r["身分"])
has_stroller = any(df_members["輪椅/推車"])
strict_nonstop = any(df_members["不轉機"])
strict_no_redeye = any(df_members["不搭紅眼"])

# ==========================================
# 主畫面：行程參數
# ==========================================
st.title("✈️ 家族全年最佳時機機票 ＋ AI 自由行規劃系統")

c1, c2, c3 = st.columns(3)
with c1:
    origin = st.text_input("出發機場 (IATA)", value="TPE").upper()
with c2:
    destination = st.text_input("目的地機場 (IATA)", value="FUK").upper()
with c3:
    trip_days = st.number_input("預計旅遊天數", min_value=3, max_value=14, value=5)

st.markdown(f"**成員概況**：共 {len(df_members)} 人（{adult_cnt} 大、{child_cnt} 小，其中長輩 {senior_cnt} 位）｜ 嚴格直飛：{'是' if strict_nonstop else '否'} ｜ 排除紅眼：{'是' if strict_no_redeye else '否'}")

# ==========================================
# 核心功能：搜尋全年最佳時間與機票
# ==========================================
if st.button("🚀 掃描全年最佳出發時間並自動生成 AI 行程", type="primary"):
    if not (amadeus_key and amadeus_secret and gemini_api_key):
        st.error("請在左側完整填寫 Amadeus API 及 Gemini API 金鑰！")
    else:
        with st.status("正在執行全流程智慧運算...", expanded=True) as status:
            try:
                # 1. 建立 Amadeus 客戶端
                status.write("🔍 步驟 1/3：向航空資料庫掃描全年度票價趨勢與班次供給...")
                amadeus = Client(client_id=amadeus_key, client_secret=amadeus_secret)

                # 採樣未來區間的各推薦出發日（約 2~5 個月後）
                today = date.today()
                sample_dates = [
                    today + timedelta(days=60),   # 約 2 個月後
                    today + timedelta(days=90),   # 約 3 個月後
                    today + timedelta(days=120),  # 約 4 個月後
                    today + timedelta(days=150),  # 約 5 個月後
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
                            max=5
                        )
                        if not resp.data:
                            continue

                        for flight in resp.data:
                            outbound = flight["itineraries"][0]["segments"]
                            inbound = flight["itineraries"][1]["segments"]
                            out_layovers = len(outbound) - 1
                            in_layovers = len(inbound) - 1
                            
                            # 檢查起降時間（排除紅眼：23:00 - 06:00）
                            dep_h = datetime.fromisoformat(outbound[0]["departure"]["at"]).hour
                            arr_h = datetime.fromisoformat(outbound[-1]["arrival"]["at"]).hour
                            is_red_eye = (dep_h >= 23 or dep_h < 6) or (arr_h >= 23 or arr_h < 6)

                            if strict_nonstop and (out_layovers > 0 or in_layovers > 0):
                                continue
                            if strict_no_redeye and is_red_eye:
                                continue

                            price = float(flight["price"]["total"])
                            candidate_flights.append({
                                "dep_date": str(d),
                                "ret_date": str(ret_d),
                                "out_airline": outbound[0]["carrierCode"],
                                "out_flight": f"{outbound[0]['carrierCode']}{outbound[0]['number']}",
                                "out_dep_time": outbound[0]["departure"]["at"],
                                "out_arr_time": outbound[-1]["arrival"]["at"],
                                "in_dep_time": inbound[0]["departure"]["at"],
                                "in_arr_time": inbound[-1]["arrival"]["at"],
                                "total_price": price
                            })
                    except Exception:
                        continue

                if not candidate_flights:
                    status.update(label="未能找到符合嚴格直飛與無紅眼的航班，請放寬限制或更換航點！", state="error")
                    st.stop()

                # 取票價最親民、時間最舒適的航班作為最佳推薦
                candidate_flights.sort(key=lambda x: x["total_price"])
                best_flight = candidate_flights[0]

                status.write(f"✅ 步驟 2/3：已鎖定最佳出發檔期：{best_flight['dep_date']} 至 {best_flight['ret_date']}")
                
                # 2. 呼叫 Gemini AI 生成客製化家族自由行
                status.write("🤖 步驟 3/3：Gemini AI 正在為全家撰寫客製化自由行行程...")
                
                ai_client = genai.Client(api_key=gemini_api_key)
                
                prompt = f"""
你是一位專門為「三代同堂 / 家族旅遊」量身定制行程的高級旅遊顧問。
請根據以下家族結構與實際航班時間，規劃一份詳細、舒適且合理的 {trip_days} 天自由行行程。

【家族成員資訊】
- 總人數：{len(df_members)} 人（成人含長輩 {adult_cnt} 人、孩童 {child_cnt} 人）
- 成員特質：有 {senior_cnt} 位長輩、{child_cnt} 位幼童。
- 移動限制：{'需考量嬰兒推車 / 輪椅動線，避開陡坡、大量樓梯與長時間步行' if has_stroller else '一般步行'}。
- 體力節奏：長輩需要早睡且不可過度勞累，下午需要有喝茶休息或飯店小憩時間；小孩作息需規律。

【確定的航班資訊】
- 目的地機場：{destination}
- 去程：{best_flight['dep_date']} {best_flight['out_flight']}，起飛 {best_flight['out_dep_time']}，抵達 {best_flight['out_arr_time']}
- 回程：{best_flight['ret_date']}，起飛 {best_flight['in_dep_time']}，抵達 {best_flight['in_arr_time']}
- 全家機票總花費：NT$ {best_flight['total_price']:,.0f}

【產出規範】
1. **每日行程規劃**：包含上午、下午、晚間安排。必須配合航班起降時間安排第 1 天與最後一天的抵達與去機場交通。
2. **交通方式推薦**：明確建議包車、計程車或適合大推車的電車路線。
3. **無障礙與體力友善點評**：針對每個景點說明為何適合長輩與小孩。
4. **推薦住宿區域**：說明住在哪個地鐵站附近最少搬運行李。
5. **長輩與孩童緊急與便利提示**：廁所便利性、雨天室內備案。
"""

                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                
                status.update(label="🎉 規劃完成！機票與 AI 行程已就緒！", state="complete")

                # ==========================================
                # 呈現結果
                # ==========================================
                st.success("🎯 系統已為全家鎖定最佳旅遊檔期與班機！")
                
                col_f1, col_f2, col_f3 = st.columns(3)
                col_f1.metric("最佳出發與回程日", f"{best_flight['dep_date']} ~ {best_flight['ret_date']}")
                col_f2.metric("去程班次與起飛", f"{best_flight['out_flight']} ({best_flight['out_dep_time'][11:16]})")
                col_f3.metric("全家來回機票總價", f"NT$ {best_flight['total_price']:,.0f}")

                st.markdown("---")
                st.subheader("📖 Gemini AI 專屬家族自由行完整企劃書")
                st.markdown(response.text)

            except Exception as e:
                status.update(label="執行過程發生錯誤", state="error")
                st.error(f"錯誤詳情：{e}")
