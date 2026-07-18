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
    
    if img_url_str:
        properties["圖片網址"] = {"rich_text": [{"text": {"content": img_url_str}}]}
        
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
                date_val += f"~{date_prop['end']}" 
        else:
            date_val = "未設定"
            
        ig = props["IG帳號"]["rich_text"][0]["text"]["content"] if props["IG帳號"]["rich_text"] else ""
        threads = props["Threads帳號"]["rich_text"][0]["text"]["content"] if props["Threads帳號"]["rich_text"] else ""
        fav = props["喜愛程度"]["number"]
        
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
                ig_acc = st.text_input("IG 帳號", placeholder="username")
                post_link = st.text_input("🔗 貼文連結", placeholder="https://...")
            with col2:
                threads_acc = st.text_input("Threads 帳號", placeholder="username")
                pickup_date = st.date_input("領取日期 (點兩下可選區間) *", value=[datetime.date.today()])
                preference = st.slider("喜愛程度", min_value=1, max_value=5, value=3)
            
            uploaded_files = st.file_uploader("📷 上傳應援品照片 (可多選)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            submitted = st.form_submit_button("💾 送出至 Notion", use_container_width=True)
            
            if submitted:
                if not item_name:
                    st.error("請輸入「應援品名稱」！")
                else:
                    with st.spinner("正在上傳資料與圖片，請稍候..."):
                        start_d = pickup_date[0]
                        end_d = pickup_date[1] if len(pickup_date) > 1 else None
                        
                        final_img_urls = []
                        if uploaded_files:
                            for file in uploaded_files:
                                url = upload_image_to_imgbb(file.getvalue())
                                if url:
                                    final_img_urls.append(url)
                        
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
            # --- 🔍 搜尋、篩選與排序區塊 ---
            with st.expander("🔍 搜尋、篩選與排序", expanded=False):
                filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
                with filter_col1:
                    search_query = st.text_input("關鍵字搜尋", placeholder="搜尋名稱或帳號...")
                with filter_col2:
                    min_fav = st.slider("最低喜愛程度", min_value=1, max_value=5, value=1)
                with filter_col3:
                    # 加入排序下拉選單
                    sort_order = st.selectbox("📅 日期排序", ["由近到遠 (最新)", "由遠到近 (最舊)"])
            
            # --- 執行資料過濾與排序邏輯 ---
            filtered_df = df.copy()
            
            # 1. 過濾關鍵字 (不分大小寫)
            if search_query:
                mask_name = filtered_df["名稱"].str.contains(search_query, case=False, na=False)
                mask_ig = filtered_df["IG帳號"].str.contains(search_query, case=False, na=False)
                mask_threads = filtered_df["Threads帳號"].str.contains(search_query, case=False, na=False)
                filtered_df = filtered_df[mask_name | mask_ig | mask_threads]
                
            # 2. 過濾星等
            if min_fav > 1:
                filtered_df = filtered_df[filtered_df["喜愛程度"] >= min_fav]

            # 3. 日期排序
            is_ascending = True if sort_order == "由遠到近 (最舊)" else False
            filtered_df = filtered_df.sort_values(by="領取日期", ascending=is_ascending)

            # --- 呈現過濾後的資料 ---
            if filtered_df.empty:
                st.warning("找不到符合篩選條件的應援品喔！")
            else:
                cols_per_row = 3 
                for i in range(0, len(filtered_df), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(filtered_df):
                            item = filtered_df.iloc[i + j]
                            with col:
                                with st.container(border=True):
                                    acc_text = ""
                                    if pd.notna(item["IG帳號"]) and str(item["IG帳號"]).strip():
                                        acc_text = f"@{item['IG帳號']}"
                                    elif pd.notna(item["Threads帳號"]) and str(item["Threads帳號"]).strip():
                                        acc_text = f"@{item['Threads帳號']}"
                                    
                                    # 建立帶有浮水印的 CSS 圖片模板 (加入點擊看全圖功能)
                                    def get_img_html(img_url, date_str, acc_str):
                                        return f"""
                                        <div style="width: 100%; padding-bottom: 100%; position: relative; border-radius: 8px; overflow: hidden; margin-bottom: 10px;">
                                            <a href="{img_url}" target="_blank" title="點擊查看完整原圖">
                                                <img src="{img_url}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; cursor: pointer;">
                                            </a>
                                            <div style="position: absolute; bottom: 8px; left: 8px; background: rgba(20, 25, 30, 0.85); color: white; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold; pointer-events: none;">
                                                {date_str} {acc_str}
                                            </div>
                                        </div>
                                        """
                                    
                                    if pd.notna(item["圖片預覽"]) and str(item["圖片預覽"]).strip() != "":
                                        urls = str(item["圖片預覽"]).split(",")
                                        if len(urls) > 1:
                                            img_tabs = st.tabs([f"圖 {k+1}" for k in range(len(urls))])
                                            for k, t in enumerate(img_tabs):
                                                with t:
                                                    st.markdown(get_img_html(urls[k].strip(), item['領取日期'], acc_text), unsafe_allow_html=True)
                                        else:
                                            st.markdown(get_img_html(urls[0].strip(), item['領取日期'], acc_text), unsafe_allow_html=True)
                                    else:
                                        empty_html = f"""
                                        <div style="width: 100%; padding-bottom: 100%; position: relative; border-radius: 8px; background: #e0e4eb; margin-bottom: 10px;">
                                            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #7f8c8d; font-weight: bold;">
                                                ── 沒有照片 ──
                                            </div>
                                            <div style="position: absolute; bottom: 8px; left: 8px; background: rgba(20, 25, 30, 0.5); color: white; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">
                                                {item['領取日期']} {acc_text}
                                            </div>
                                        </div>
                                        """
                                        st.markdown(empty_html, unsafe_allow_html=True)
                                    
                                    st.markdown(f"**{item['名稱']}**")
                                    st.caption(f"喜愛程度：{'⭐' * item['喜愛程度']}")
                                    
                                    if pd.notna(item["貼文連結"]) and str(item["貼文連結"]).strip() != "":
                                        st.link_button("🔗 前往貼文", item["貼文連結"], use_container_width=True)
        else:
            st.info("目前資料庫還是空的喔！趕快去新增第一筆吧！")