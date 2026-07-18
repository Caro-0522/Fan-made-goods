import streamlit as st
import requests
import pandas as pd
import datetime

# --- 網頁基本設定 ---
st.set_page_config(page_title="應援品領取小幫手", page_icon="🎁", layout="wide")

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
def create_notion_page(name, start_date, end_date, ig, threads, fav, img_url_str, post_link):
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
    
    # 寫入多張圖片網址 (改為 rich_text 文字格式)
    if img_url_str:
        properties["圖片網址"] = {"rich_text": [{"text": {"content": img_url_str}}]}
        
    # 寫入貼文連結
    if post_link:
        properties["貼文連結"] = {"url": post_link}
        
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
            date_val = "未設定日期"
            
        ig = props["IG帳號"]["rich_text"][0]["text"]["content"] if props["IG帳號"]["rich_text"] else ""
        threads = props["Threads帳號"]["rich_text"][0]["text"]["content"] if props["Threads帳號"]["rich_text"] else ""
        fav = props["喜愛程度"]["number"]
        
        # 抓取圖片網址字串 (從 rich_text 讀取)
        img_url_raw = props["圖片網址"]["rich_text"][0]["text"]["content"] if props.get("圖片網址") and props["圖片網址"].get("rich_text") else None
        
        post_link = props["貼文連結"]["url"] if props.get("貼文連結") and props["貼文連結"].get("url") else None
        
        items.append({
            "名稱": name,
            "圖片預覽": img_url_raw,
            "領取日期": date_val,
            "IG帳號": ig,
            "Threads帳號": threads,
            "喜愛程度": fav,
            "貼文連結": post_link
        })
        
    return pd.DataFrame(items)

# --- UI 介面 ---
st.title("🎁 應援品領取小幫手")
tab1, tab2 = st.tabs(["➕ 新增登記", "🖼️ 畫廊檢視"])

# ================= 分頁 1：新增資料 =================
with tab1:
    with st.container(border=True):
        with st.form("add_item_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 1])
            with col1:
                item_name = st.text_input("應援品名稱 *", placeholder="例如：宋威龍生日杯套")
                ig_acc = st.text_input("IG 帳號", placeholder="@username")
                post_link = st.text_input("🔗 貼文連結", placeholder="https://...")
            with col2:
                threads_acc = st.text_input("Threads 帳號", placeholder="@username")
                pickup_date = st.date_input("領取日期 (點兩下可選區間) *", value=[datetime.date.today()])
                preference = st.slider("喜愛程度", min_value=1, max_value=5, value=3)
            
            # 開啟 accept_multiple_files 允許選擇多張照片
            uploaded_files = st.file_uploader("📷 上傳應援品照片 (可多選)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            submitted = st.form_submit_button("💾 送出至 Notion", use_container_width=True)
            
            if submitted:
                if not item_name:
                    st.error("請輸入「應援品名稱」！")
                else:
                    with st.spinner("正在上傳資料與圖片，請稍候..."):
                        start_d = pickup_date[0]
                        end_d = pickup_date[1] if len(pickup_date) > 1 else None
                        
                        # 處理多張圖片上傳
                        final_img_urls = []
                        if uploaded_files:
                            for file in uploaded_files:
                                url = upload_image_to_imgbb(file.getvalue())
                                if url:
                                    final_img_urls.append(url)
                        
                        # 將多個網址用逗號串接成一個字串
                        img_url_str = ",".join(final_img_urls) if final_img_urls else None
                        
                        res = create_notion_page(item_name, start_d, end_d, ig_acc, threads_acc, preference, img_url_str, post_link)
                        
                    if res.status_code == 200:
                        st.success(f"🎉 成功新增：{item_name}！")
                    else:
                        st.error(f"❌ 同步失敗，錯誤碼：{res.status_code}")

# ================= 分頁 2：畫廊檢視 =================
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
            cols_per_row = 3 
            
            for i in range(0, len(df), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(df):
                        item = df.iloc[i + j]
                        with col:
                            # 拿掉 height 讓高度在手機上能自然伸展
                            with st.container(border=True):
                                # 圖片處理 (支援多圖分頁)
                                if pd.notna(item["圖片預覽"]) and str(item["圖片預覽"]).strip() != "":
                                    urls = str(item["圖片預覽"]).split(",")
                                    if len(urls) > 1:
                                        # 如果有多張圖，產生手動點擊的小分頁
                                        img_tabs = st.tabs([f"圖 {k+1}" for k in range(len(urls))])
                                        for k, t in enumerate(img_tabs):
                                            with t:
                                                st.image(urls[k].strip(), use_container_width=True)
                                    else:
                                        # 只有一張圖就直接顯示
                                        st.image(urls[0].strip(), use_container_width=True)
                                else:
                                    st.info("── 沒有照片 ──")
                                
                                # 名稱與日期
                                st.markdown(f"#### {item['名稱']}")
                                st.markdown(f"**📅 {item['領取日期']}**")
                                
                                # 帳號
                                if pd.notna(item["IG帳號"]) and str(item["IG帳號"]).strip() != "":
                                    st.caption(f"IG: {item['IG帳號']}")
                                if pd.notna(item["Threads帳號"]) and str(item["Threads帳號"]).strip() != "":
                                    st.caption(f"Threads: {item['Threads帳號']}")
                                    
                                # 喜愛程度
                                st.markdown(f"喜愛程度：{'⭐' * item['喜愛程度']}")
                                
                                # 跳轉按鈕
                                if pd.notna(item["貼文連結"]) and str(item["貼文連結"]).strip() != "":
                                    st.link_button("🔗 前往貼文", item["貼文連結"], use_container_width=True)
        else:
            st.info("目前資料庫還是空的喔！趕快去新增第一筆吧！")