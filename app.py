import streamlit as st
import requests
import pandas as pd
import datetime

# --- 網頁基本設定 ---
st.set_page_config(page_title="應援品領取小幫手", page_icon="🎁", layout="centered")

# --- 讀取環境變數 (Secrets) ---
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    DATABASE_ID = st.secrets["DATABASE_ID"]
except KeyError:
    st.error("⚠️ 找不到密鑰！請確認是否已在 Streamlit Cloud 設定 Secrets。")
    st.stop()

# --- Notion API 設定 ---
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- 寫入 Notion 的函式 ---
def create_notion_page(name, start_date, end_date, ig, threads, fav):
    url = "https://api.notion.com/v1/pages"
    
    # 處理日期區間格式
    date_data = {"start": str(start_date)}
    if end_date:
        date_data["end"] = str(end_date)
        
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "名稱": {"title": [{"text": {"content": name}}]},
            "領取日期": {"date": date_data},
            "IG帳號": {"rich_text": [{"text": {"content": ig}}]},
            "Threads帳號": {"rich_text": [{"text": {"content": threads}}]},
            "喜愛程度": {"number": fav}
        }
    }
    return requests.post(url, headers=NOTION_HEADERS, json=data)

# --- 讀取 Notion 資料的函式 ---
def fetch_notion_data():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    # Notion 的 query API 是使用 POST 方法
    res = requests.post(url, headers=NOTION_HEADERS)
    data = res.json()
    
    items = []
    for result in data.get("results", []):
        props = result["properties"]
        
        # 解析各欄位資料，加入防呆機制避免空值報錯
        name = props["名稱"]["title"][0]["text"]["content"] if props["名稱"]["title"] else "未命名"
        
        date_prop = props["領取日期"]["date"]
        if date_prop:
            date_val = date_prop["start"]
            if date_prop.get("end"):
                date_val += f" ~ {date_prop['end']}"
        else:
            date_val = ""
            
        ig = props["IG帳號"]["rich_text"][0]["text"]["content"] if props["IG帳號"]["rich_text"] else ""
        threads = props["Threads帳號"]["rich_text"][0]["text"]["content"] if props["Threads帳號"]["rich_text"] else ""
        fav = props["喜愛程度"]["number"]
        
        items.append({
            "名稱": name,
            "領取日期": date_val,
            "IG帳號": ig,
            "Threads帳號": threads,
            "喜愛程度": fav
        })
        
    # 將解析完的資料轉換為 Pandas 表格
    return pd.DataFrame(items)

# --- 頁面標題 ---
st.title("🎁 應援品領取小幫手")

# --- 建立雙分頁 ---
tab1, tab2 = st.tabs(["➕ 新增登記", "📋 檢視資料庫"])

# ================= 分頁 1：新增資料 =================
with tab1:
    with st.container(border=True):
        with st.form("add_item_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 1])
            with col1:
                item_name = st.text_input("應援品名稱 *", placeholder="例如：宋威龍生日杯套")
                ig_acc = st.text_input("IG 帳號", placeholder="@username")
            with col2:
                threads_acc = st.text_input("Threads 帳號", placeholder="@username")
                # 日期選擇器：給予 list 預設值以開啟「區間選擇」功能
                pickup_date = st.date_input("領取日期 (點兩下可選區間) *", value=[datetime.date.today()])
            
            preference = st.slider("喜愛程度", min_value=1, max_value=5, value=3)
            submitted = st.form_submit_button("💾 送出至 Notion", use_container_width=True)
            
            if submitted:
                if not item_name:
                    st.error("請輸入「應援品名稱」！")
                else:
                    with st.spinner("正在同步至 Notion..."):
                        # 判斷使用者選了單一天還是兩天的區間
                        start_d = pickup_date[0]
                        end_d = pickup_date[1] if len(pickup_date) > 1 else None
                        
                        res = create_notion_page(item_name, start_d, end_d, ig_acc, threads_acc, preference)
                        
                    if res.status_code == 200:
                        st.success(f"🎉 成功新增：{item_name}！")
                    else:
                        st.error(f"❌ 同步失敗，錯誤碼：{res.status_code}")

# ================= 分頁 2：檢視資料 =================
with tab2:
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.subheader("目前已登記的應援品")
    with col_btn:
        if st.button("🔄 重新整理", use_container_width=True):
            st.rerun()
            
    with st.spinner("正在從 Notion 載入資料..."):
        df = fetch_notion_data()
        if not df.empty:
            # 顯示互動式表格，隱藏索引值
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("目前資料庫還是空的喔！")