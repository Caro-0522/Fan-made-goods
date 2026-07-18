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
def create_notion_page(name, date_str, ig, threads, fav, img_url_str, post_link):
    url = "https://api.notion.com/v1/pages"
        
    properties = {
        "名稱": {"title": [{"text": {"content": name}}]},
        "領取日期": {"rich_text": [{"text": {"content": date_str}}]},
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
        
        name_prop = props.get("名稱", {})
        name = "未命名"
        if name_prop.get("title"):
            name = "".join([t.get("plain_text", "") for t in name_prop.get("title", [])])
            
        date_prop = props.get("領取日期", {})
        date_val = "未設定"
        if date_prop:
            if date_prop.get("type") == "rich_text":
                rts = date_prop.get("rich_text", [])
                if rts:
                    date_val = "".join([rt.get("plain_text", "") for rt in rts])
            elif date_prop.get("type") == "date" and date_prop.get("date"):
                d = date_prop["date"]
                date_val = d.get("start", "未設定")
                if d.get("end"):
                    date_val += f", {d['end']}"
                    
        ig_prop = props.get("IG帳號", {})
        ig = "".join([rt.get("plain_text", "") for rt in ig_prop.get("rich_text", [])]) if ig_prop.get("type") == "rich_text" else ""
        
        threads_prop = props.get("Threads帳號", {})
        threads = "".join([rt.get("plain_text", "") for rt in threads_prop.get("rich_text", [])]) if threads_prop.get("type") == "rich_text" else ""
        
        fav = props.get("喜愛程度", {}).get("number", 3)
        if fav is None:
            fav = 3
            
        img_prop = props.get("圖片網址", {})
        img_url_raw = "".join([rt.get("plain_text", "") for rt in img_prop.get("rich_text", [])]) if img_prop.get("type") == "rich_text" else None
        
        link_prop = props.get("貼文連結", {})
        post_link = link_prop.get("url") if link_prop.get("type") == "url" else None
        
        items.append({
            "名稱": name if name else "未命名",
            "圖片預覽": img_url_raw,
            "領取日期": date_val if date_val else "未設定",
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
            item_name = st.text_input("應援品名稱 *", placeholder="例如：宋威龍生日杯套")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                ig_acc = st.text_input("IG 帳號", placeholder="username")
                post_link = st.text_input("🔗 貼文連結", placeholder="https://...")
            with col2:
                threads_acc = st.text_input("Threads 帳號", placeholder="username")
                preference = st.slider("喜愛程度", min_value=1, max_value=5, value=3)
            
            # 📅 日曆選擇區塊 (支援跳著選)
            st.markdown("**📅 領取日期 (支援跳著發，請點擊日曆選擇)**")
            d_col1, d_col2, d_col3 = st.columns(3)
            with d_col1:
                # 第一天預設為今天
                d1 = st.date_input("第一天 *", value=datetime.date.today())
            with d_col2:
                # 第二天預設為空
                d2 = st.date_input("第二天 (選填)", value=None)
            with d_col3:
                # 第三天預設為空
                d3 = st.date_input("第三天 (選填)", value=None)
            
            uploaded_files = st.file_uploader("📷 上傳應援品照片 (可多選)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            submitted = st.form_submit_button("💾 送出至 Notion", use_container_width=True)
            
            if submitted:
                if not item_name:
                    st.error("請輸入「應援品名稱」！")
                elif not d1:
                    st.error("請至少選擇「第一天」的領取日期！")
                else:
                    with st.spinner("正在上傳資料與圖片，請稍候..."):
                        
                        # 把有填寫的日曆日期收集起來
                        dates_list = []
                        # d1, d2, d3 可能回傳的是單一日期或日期區間的 Tuple
                        for d in [d1, d2, d3]:
                            if d:
                                if isinstance(d, tuple):
                                    # 如果使用者選了區間 (Start to End)，組合起來
                                    if len(d) == 2:
                                        dates_list.append(f"{d[0].strftime('%Y-%m-%d')} ~ {d[1].strftime('%Y-%m-%d')}")
                                    else:
                                        dates_list.append(d[0].strftime('%Y-%m-%d'))
                                else:
                                    # 單一日期
                                    dates_list.append(d.strftime('%Y-%m-%d'))
                        
                        # 用逗號串接所有的日期
                        date_str = ", ".join(dates_list)
                        
                        final_img_urls = []
                        if uploaded_files:
                            for file in uploaded_files:
                                url = upload_image_to_imgbb(file.getvalue())
                                if url:
                                    final_img_urls.append(url)
                        
                        img_url_str = ",".join(final_img_urls) if final_img_urls else None
                        res = create_notion_page(item_name, date_str, ig_acc, threads_acc, preference, img_url_str, post_link)
                        
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
            # 整理出資料庫裡所有出現過的日期供篩選
            all_dates = []
            for d in df["領取日期"]:
                if pd.notna(d) and d != "未設定":
                    parts = str(d).replace("~", ",").split(",")
                    all_dates.extend([p.strip() for p in parts if p.strip()])
            unique_dates = sorted(list(set(all_dates)))

            # --- 🔍 搜尋、篩選與排序區塊 ---
            with st.expander("🔍 搜尋、篩選與排序", expanded=False):
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    search_query = st.text_input("關鍵字搜尋", placeholder="搜尋名稱或帳號...")
                with row1_col2:
                    filter_date = st.selectbox("📅 選擇領取日", ["全部"] + unique_dates)
                    
                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    min_fav = st.slider("最低喜愛程度", min_value=1, max_value=5, value=1)
                with row2_col2:
                    sort_order = st.selectbox("⏳ 日期排序", ["由近到遠 (最新)", "由遠到近 (最舊)"])
            
            # --- 執行資料過濾與排序邏輯 ---
            filtered_df = df.copy()
            
            if search_query:
                mask_name = filtered_df["名稱"].str.contains(search_query, case=False, na=False)
                mask_ig = filtered_df["IG帳號"].str.contains(search_query, case=False, na=False)
                mask_threads = filtered_df["Threads帳號"].str.contains(search_query, case=False, na=False)
                filtered_df = filtered_df[mask_name | mask_ig | mask_threads]
                
            if filter_date != "全部":
                filtered_df = filtered_df[filtered_df["領取日期"].str.contains(filter_date, na=False)]

            if min_fav > 1:
                filtered_df = filtered_df[filtered_df["喜愛程度"] >= min_fav]

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