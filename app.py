import streamlit as st

from views.main_page import render_main_page
from views.sub_page1 import render_sub_page1  # 関数名を変更

# ページ基本設定
st.set_page_config(
    page_title="江戸川競艇予想アプリ",
    page_icon="🚤",
    layout="wide"
)

# セッション状態の初期化（初期画面はメイン）
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "main"

# ルーティング処理（画面切り替え）
if st.session_state["current_page"] == "main":
    render_main_page()
elif st.session_state["current_page"] == "sub_page1":
    render_sub_page1()  # サブ画面の描画関数を実行