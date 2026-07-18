import streamlit as st
import requests
import pandas as pd
import datetime

st.set_page_config(page_title="應援品領取小幫手", page_icon="🎁", layout="centered")

# --- 讀取環境變數 ---
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    DATABASE_ID = st.secrets["DATABASE_ID"]
    IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]
except KeyError:
    st.error("⚠️ 找不到密鑰！請確認 Secrets 是否設定正確。")
    st.stop()

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- 圖床上傳函式 ---
def upload_image_to_imgbb(image_bytes):
    url = "https://api.imgbb.com/1/upload"
    payload = {"key": IMGBB_API_KEY}
    files = {"image": image_bytes}
    res = requests.post(url, data=payload, files=files)
    if res.status_code == 200:
        return res.json()["data"]["url"]
    return None

# --- Notion 寫入函式 ---
def create_notion_page(name, start_date, end_date, ig, threads, fav, img_url):
    url = "https://api.imgbb.com/v1/pages"  # Notion API URL
    url = "https://api.notion.com/v1/pages"
    
    date_data = {"start": str(start_date)}
    if end_date:
        date_data["end"] = str(end_date)
        
    properties = {
        "名稱": {"title": [{"text": {"content": name}}]},
        "領取日期": {"date": date_data},
        "IG帳號": {"rich_text": [{"text": {"content": ig}}]},
        "Threads帳號": {"rich_text": [{"text": {"content": threads}}]},
        "喜愛程度": {"number": fav}
    }
    
    # 如果有圖片網址，才加入圖片網址欄位
    if img_url:
        properties["圖片網址"] = {"url": img_url}
        
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    }
    return requests.post(url, headers=NOTION_HEADERS, json=data)

# --- Notion 讀取函式 ---
def fetch_notion_data():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=NOTION_HEADERS)
    data = res.json()
    
    items = []
    for result in data.get("results", []):
        props = result["properties"]
        
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
        
        # 抓取圖片網址
        img_url = props["圖片網址"]["url"] if props.get("圖片網址") and props["圖片網址"].get("url") else None
        
        items.append({
            "名稱": name,
            "圖片預覽": img_url,  # 供 Streamlit 渲染圖片用
            "領取日期": date_val,
            "IG帳號": ig,
            "Threads帳號": threads,
            "喜愛程度": fav
        })
        
    return pd.DataFrame(items)

# --- UI 介面 ---
st.title("🎁 應援品領取小幫手")
tab1, tab2 = st.tabs(["➕ 新增登記", "📋 檢視資料庫"])

with tab1:
    with st.container(border=True):
        with st.form("add_item_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 1])
            with col1:
                item_name = st.text_input("應援品名稱 *", placeholder="例如：宋威龍生日杯套")
                ig_acc = st.text_input("IG 帳號", placeholder="@username")
            with col2:
                threads_acc = st.text_input("Threads 帳號", placeholder="@username")
                pickup_date = st.date_input("領取日期 (點兩下可選區間) *", value=[datetime.date.today()])
            
            preference = st.slider("喜愛程度", min_value=1, max_value=5, value=3)
            
            # 加入圖片上傳區塊
            uploaded_file = st.file_uploader("📷 上傳應援品照片", type=["jpg", "jpeg", "png"])
            
            submitted = st.form_submit_button("💾 送出至 Notion", use_container_width=True)
            
            if submitted:
                if not item_name:
                    st.error("請輸入「應援品名稱」！")
                else:
                    with st.spinner("正在上傳資料與圖片，請稍候..."):
                        start_d = pickup_date[0]
                        end_d = pickup_date[1] if len(pickup_date) > 1 else None
                        
                        # 處理圖片上傳
                        final_img_url = None
                        if uploaded_file is not None:
                            final_img_url = upload_image_to_imgbb(uploaded_file.getvalue())
                        
                        res = create_notion_page(item_name, start_d, end_d, ig_acc, threads_acc, preference, final_img_url)
                        
                    if res.status_code == 200:
                        st.success(f"🎉 成功新增：{item_name}！")
                    else:
                        st.error(f"❌ 同步失敗，錯誤碼：{res.status_code}")

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
            st.dataframe(
                df,
                column_config={
                    "圖片預覽": st.column_config.ImageColumn("照片", help="實體照片")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("目前資料庫還是空的喔！")