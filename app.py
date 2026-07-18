import streamlit as st
import pandas as pd
import os
import datetime
from PIL import Image
import uuid

# --- 網頁基本設定 ---
st.set_page_config(page_title="應援品領取小幫手", page_icon="🎁", layout="centered")

# --- 初始化資料夾與檔案 ---
DATA_FILE = "support_items.csv"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=["名稱", "IG帳號", "Threads帳號", "領取日期", "喜愛程度", "圖片路徑"])
    df_init.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# --- 讀取資料函式 ---
def load_data():
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    # 將日期字串轉為 datetime.date 格式以便比較
    df['領取日期'] = pd.to_datetime(df['領取日期']).dt.date
    return df

# --- 頁面標題 ---
st.title("🎁 應援品領取小幫手")
st.markdown("隨時隨地紀錄，不錯過任何一份心意！")

# --- 新增資料區塊 (手機版優化：使用折疊設計) ---
with st.expander("➕ 新增應援品登記", expanded=False):
    with st.form("add_item_form", clear_on_submit=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            item_name = st.text_input("應援品名稱 *", placeholder="例如：宋威龍生日杯套")
            ig_acc = st.text_input("IG 帳號", placeholder="@username")
        with col2:
            threads_acc = st.text_input("Threads 帳號", placeholder="@username")
            pickup_date = st.date_input("領取日期 *", min_value=datetime.date.today())
        
        preference = st.slider("喜愛程度", min_value=1, max_value=5, value=3)
        uploaded_file = st.file_uploader("上傳參考圖片 (支援拍照)", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("💾 儲存資料", use_container_width=True)
        
        if submitted:
            if not item_name:
                st.error("請輸入「應援品名稱」！")
            else:
                image_path = ""
                # 處理圖片儲存
                if uploaded_file is not None:
                    # 產生隨機檔名避免重複覆蓋
                    file_ext = uploaded_file.name.split('.')[-1]
                    unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                    image_path = os.path.join(IMAGE_DIR, unique_filename)
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                # 將新資料存入 CSV
                new_data = pd.DataFrame({
                    "名稱": [item_name],
                    "IG帳號": [ig_acc],
                    "Threads帳號": [threads_acc],
                    "領取日期": [pickup_date],
                    "喜愛程度": [preference],
                    "圖片路徑": [image_path]
                })
                
                new_data.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")
                st.success(f"已成功新增：{item_name}！")
                st.rerun() # 重新整理頁面以更新下方清單

# --- 讀取最新資料 ---
df = load_data()

# --- 主頁面呈現 (分頁設計) ---
tab1, tab2 = st.tabs(["📅 下週即將領取", "📋 總清單回顧"])

with tab1:
    st.subheader("未來 7 天領取任務")
    today = datetime.date.today()
    next_week = today + datetime.timedelta(days=7)
    
    # 篩選未來7天的資料，並按日期排序
    mask = (df['領取日期'] >= today) & (df['領取日期'] <= next_week)
    upcoming_df = df[mask].sort_values(by="領取日期")
    
    if upcoming_df.empty:
        st.info("太棒了！接下來 7 天暫時沒有需要跑點的任務。")
    else:
        for index, row in upcoming_df.iterrows():
            # 使用 container 製作卡片，加上邊框使其在手機上界線分明
            with st.container(border=True):
                # 將喜愛程度轉換為星星符號
                stars = "★" * int(row["喜愛程度"]) + "☆" * (5 - int(row["喜愛程度"]))
                
                # 排版：如果有圖片，上面放圖片，下面放資訊；無圖片則直接顯示資訊
                if pd.notna(row["圖片路徑"]) and row["圖片路徑"] != "":
                    try:
                        img = Image.open(row["圖片路徑"])
                        st.image(img, use_container_width=True)
                    except Exception:
                        st.warning("圖片載入失敗")
                
                st.markdown(f"### {row['名稱']}")
                st.markdown(f"**📅 日期：** {row['領取日期']}")
                
                # 將 IG 和 Threads 帳號並排顯示
                acc_col1, acc_col2 = st.columns(2)
                with acc_col1:
                    st.markdown(f"**IG:** {row['IG帳號'] if pd.notna(row['IG帳號']) and row['IG帳號'] else '無'}")
                with acc_col2:
                    st.markdown(f"**Threads:** {row['Threads帳號'] if pd.notna(row['Threads帳號']) and row['Threads帳號'] else '無'}")
                
                st.markdown(f"**喜愛程度：** <span style='color:#f39c12'>{stars}</span>", unsafe_allow_html=True)

with tab2:
    st.subheader("所有應援品紀錄")
    if df.empty:
        st.write("目前還沒有任何紀錄喔！")
    else:
        # 隱藏圖片路徑欄位，並將日期排序後顯示
        display_df = df.drop(columns=["圖片路徑"]).sort_values(by="領取日期", ascending=False)
        # 轉換星星欄位讓表格更直觀
        display_df["喜愛程度"] = display_df["喜愛程度"].apply(lambda x: "★" * int(x) + "☆" * (5 - int(x)))
        st.dataframe(display_df, use_container_width=True, hide_index=True)