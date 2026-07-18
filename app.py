import streamlit as st
import requests
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
def create_notion_page(name, date, ig, threads, fav):
    url = "https://api.notion.com/v1/pages"
    
    # 依照 Notion API 格式打包資料
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "名稱": {
                "title": [{"text": {"content": name}}]
            },
            "領取日期": {
                "date": {"start": str(date)}
            },
            "IG帳號": {
                "rich_text": [{"text": {"content": ig}}]
            },
            "Threads帳號": {
                "rich_text": [{"text": {"content": threads}}]
            },
            "喜愛程度": {
                "number": fav
            }
        }
    }
    
    response = requests.post(url, headers=NOTION_HEADERS, json=data)
    return response

# --- 頁面標題 ---
st.title("🎁 應援品領取小幫手")
st.markdown("隨時隨地紀錄，資料將自動同步至 Notion 資料庫！")

# --- 新增資料表單 ---
with st.container(border=True):
    st.subheader("➕ 新增應援品登記")
    with st.form("add_item_form", clear_on_submit=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            item_name = st.text_input("應援品名稱 *", placeholder="例如：宋威龍生日杯套")
            ig_acc = st.text_input("IG 帳號", placeholder="@username")
        with col2:
            threads_acc = st.text_input("Threads 帳號", placeholder="@username")
            pickup_date = st.date_input("領取日期 *", min_value=datetime.date.today())
        
        preference = st.slider("喜愛程度", min_value=1, max_value=5, value=3)
        
        # 暫時關閉圖片上傳，待 Imgur API 串接後開放
        st.info("💡 圖片上傳功能將於下一階段結合 Imgur API 後開放！")
        
        submitted = st.form_submit_button("💾 送出至 Notion", use_container_width=True)
        
        if submitted:
            if not item_name:
                st.error("請輸入「應援品名稱」！")
            else:
                with st.spinner("正在同步至 Notion..."):
                    res = create_notion_page(
                        name=item_name,
                        date=pickup_date,
                        ig=ig_acc,
                        threads=threads_acc,
                        fav=preference
                    )
                    
                if res.status_code == 200:
                    st.success(f"🎉 成功新增：{item_name}！請打開 Notion 查看。")
                else:
                    st.error(f"❌ 同步失敗，錯誤碼：{res.status_code}")
                    st.json(res.json())