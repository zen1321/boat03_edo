import json
import re
import pandas as pd
import streamlit as st

from logic import (
    calc_all_start_scores,
    calc_exhibition_scores,
    calc_motor_score,
    calc_racer_scores_detail,
    calc_water_score,
)
from logic_betting import generate_edogawa_formation

# 1. 縦の項目名（9項目）の設定
INDEX_ITEMS = [
    "登録番号",
    "名前",
    "ランク",
    "2連対率",
    "今期",
    "全国",
    "当地",
    "展示",
    "ST",
]
COLUMNS = [f"{i+1}号艇" for i in range(6)]


# -----------------------------------------------------------------------------
# 選手マスタ(data_json/racer_2026.json)読み込み関数
# -----------------------------------------------------------------------------
@st.cache_data
def load_racer_master(filepath="data_json/racer_2026.json"):
    """data_json/racer_2026.jsonを読み込み、登番(toban)をキーにした辞書を返却"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        racer_dict = {}
        for r in data:
            toban = str(r.get("toban", "")).strip()
            if not toban:
                continue

            # 平均ST（例: "021" -> "0.21"）
            raw_st_avg = str(r.get("st_avg", "")).strip()
            st_avg_str = ""
            if raw_st_avg.isdigit():
                st_avg_str = f"{float(raw_st_avg) / 100:.2f}"

            racer_dict[toban] = {
                "name": r.get("name_kanji", ""),
                "rank": r.get("rank", ""),
                "st_avg": st_avg_str,  # 「今期」項目に反映する平均ST
            }
        return racer_dict
    except Exception as e:
        st.warning(f"選手マスタ({filepath})の読み込みに失敗しました: {e}")
        return {}


def create_default_grid() -> pd.DataFrame:
    """デフォルトの9項目×6艇の空データフレームを作成"""
    return pd.DataFrame("", index=INDEX_ITEMS, columns=COLUMNS, dtype=object)


def enrich_grid_with_racer_master(
    grid_df: pd.DataFrame, master: dict
) -> pd.DataFrame:
    """表内の登録番号から選手マスタ(JSON)の情報を検索し、「名前」「ランク」「今期(平均ST)」のみを補完"""
    if not master:
        return grid_df

    for col in COLUMNS:
        toban_val = str(grid_df.loc["登録番号", col]).strip()
        if toban_val in master:
            r_info = master[toban_val]
            grid_df.loc["名前", col] = r_info["name"]
            grid_df.loc["ランク", col] = r_info["rank"]
            grid_df.loc["今期", col] = r_info["st_avg"]

    return grid_df


def parse_pasted_text_to_grid(raw_text: str, master: dict) -> pd.DataFrame:
    """コピペテキスト解析処理（9項目対応）＋JSONマスタ自動反映"""
    grid_df = create_default_grid()
    lines = [
        line.strip() for line in raw_text.strip().splitlines() if line.strip()
    ]
    target_auto_idx = 0

    for line in lines:
        if "\t" in line:
            row_data = [item.strip() for item in line.split("\t")]
        else:
            row_data = [item.strip() for item in line.split() if item.strip()]

        if not row_data:
            continue

        first_val = row_data[0]

        if first_val in INDEX_ITEMS:
            target_row_idx = INDEX_ITEMS.index(first_val)
            raw_values = row_data[1:]
        else:
            target_row_idx = target_auto_idx
            raw_values = row_data
            target_auto_idx += 1

        if target_row_idx < len(INDEX_ITEMS):
            cols_to_copy = min(len(raw_values), 6)
            for c in range(cols_to_copy):
                val_str = str(raw_values[c]).strip()
                clean_val = val_str.replace("%", "").replace("％", "")
                if clean_val.startswith("."):
                    clean_val = "0" + clean_val
                grid_df.iloc[target_row_idx, c] = clean_val

    grid_df = enrich_grid_with_racer_master(grid_df, master)
    return grid_df


def render_main_page():
    st.title("🚤 江戸川競艇 難水面攻略予想システム")
    st.caption("潮・風・機力・当地適性に特化した100点満点評価モデル")

    # 選手マスタのロード
    racer_master = load_racer_master("data_json/racer_2026.json")

    # 画面遷移ボタン（サブ画面1へ）
    col_title, col_nav = st.columns([4, 1])
    with col_nav:
        if st.button("📊 詳細データ確認 (サブ1) ➡️", type="secondary"):
            st.session_state["current_page"] = "sub_page1"
            st.rerun()

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 水面・環境条件設定エリア（4項目 ＆ 安定板トグル）
    # -----------------------------------------------------------------------------
    st.header("🌊 水面・環境条件設定")

    col_env1, col_env2, col_env3, col_env4, col_env5 = st.columns([2, 2, 2, 2, 2])

    with col_env1:
        wind_dir = st.selectbox(
            "風向",
            ["追い風", "向かい風", "横風", "無風"]
        )

    with col_env2:
        wind_speed_label = st.selectbox(
            "風速",
            ["0m", "5m未満", "5m以上"]
        )
        if wind_speed_label == "0m":
            wind_speed = 0
        elif wind_speed_label == "5m未満":
            wind_speed = 1
        else:
            wind_speed = 5

    with col_env3:
        tide_dir = st.selectbox(
            "潮流向",
            ["上げ潮", "下げ潮", "潮止まり"]
        )

    with col_env4:
        wave_speed = st.selectbox(
            "波速",
            ["強", "弱", "無"]
        )

    with col_env5:
        st.write("") # 配置バランス調整用
        is_stabilizer = st.checkbox("🔧 安定板装着", value=False)

    # 難水面警告の判定
    is_unreliable_water = (
        tide_dir == "下げ潮" and wind_dir == "追い風" and wind_speed >= 5
    )
    if is_unreliable_water:
        st.warning(
            "⚠️ 難水面警告：下げ潮＋強追い風のため展示タイム影響度を50%に自動割り引きます[cite: 1]."
        )
        
    if is_stabilizer:
        st.info("💡 安定板装着モード：1コース(+2pt)、2〜3コース(-1pt)、4〜6コース(-3pt)の補正および当地勝率強調が適用されます。")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 1. Webサイトからのデータ貼り付け（9項目対応）
    # -----------------------------------------------------------------------------
    st.header("1. Webサイトからのデータ貼り付け（9項目対応）")

    if "grid_df" not in st.session_state:
        st.session_state.grid_df = create_default_grid()

    raw_text = st.text_area(
        label="コピペ用エリア",
        key="input_text_main",
        height=140,
        placeholder="Webサイトからコピーしたテキストをここに貼り付け",
        label_visibility="collapsed",
    )

    col_btn1, col_btn2, col_btn3, _ = st.columns([2, 2, 2, 4])

    with col_btn1:
        if st.button(
            "📥 表に反映する", type="primary", use_container_width=True
        ):
            if raw_text.strip():
                try:
                    st.session_state.grid_df = parse_pasted_text_to_grid(
                        raw_text, racer_master
                    )
                    st.success("表へデータを正常に反映しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"解析エラー: {e}")
            else:
                st.session_state.grid_df = enrich_grid_with_racer_master(
                    st.session_state.grid_df, racer_master
                )
                st.info(
                    "登録番号から選手情報（名前・ランク・今期平均ST）を反映しました。"
                )
                st.rerun()

    with col_btn2:
        if st.button("🧹 テキストクリア", use_container_width=True):
            st.session_state.input_text_main = ""
            st.rerun()

    with col_btn3:
        if st.button("🗑️ 表をリセット", use_container_width=True):
            st.session_state.grid_df = create_default_grid()
            st.rerun()

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 2. データ確認・編集エリア
    # -----------------------------------------------------------------------------
    st.subheader("2. データ確認・微調整")

    edited_df = st.data_editor(
        st.session_state.grid_df,
        num_rows="fixed",
        use_container_width=True,
        key="boat_editor_main",
    )
    st.session_state.grid_df = edited_df

    # -----------------------------------------------------------------------------
    # 進入コース個別設定エリア
    # -----------------------------------------------------------------------------
    st.markdown("#### 🚩 進入コース設定（コース侵入の変化がある場合に変更）")

    course_cols = st.columns(6)
    courses = {}
    for i in range(1, 7):
        with course_cols[i - 1]:
            courses[i] = st.number_input(
                f"{i}号艇",
                min_value=1,
                max_value=6,
                value=i,
                step=1,
                key=f"course_boat_{i}",
            )

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 3. スコア計算
    # -----------------------------------------------------------------------------
    if st.button("🚀 江戸川適性スコアを計算する", type="primary"):
        results = []
        ex_times = []
        start_inputs = []
        boat_scores = {}  # 👈 買い目生成用のスコア辞書

        # 事前収集：展示タイムおよびスタートデータの整理
        for c_idx in range(6):
            col_name = COLUMNS[c_idx]
            
            # 展示タイム
            raw_ex = str(edited_df.loc["展示", col_name]).strip()
            try:
                ex_times.append(float(raw_ex) if raw_ex else 6.80)
            except ValueError:
                ex_times.append(6.80)

            # STデータ収集
            raw_st = str(edited_df.loc["ST", col_name]).strip()
            f_holder = "F" in raw_st.upper()
            st_val_str = re.sub(r"[^\d.]", "", raw_st)
            try:
                avg_st = float(edited_df.loc["今期", col_name]) if str(edited_df.loc["今期", col_name]).strip() else (float(st_val_str) if st_val_str else 0.15)
            except ValueError:
                avg_st = 0.15

            start_inputs.append({
                "avg_st": avg_st,
                "ex_st": raw_st,
                "is_f": f_holder
            })

        # 全6艇分のスタートスコアを一括計算
        start_scores = calc_all_start_scores(start_inputs)
        ex_scores = calc_exhibition_scores(ex_times, is_unreliable_water)

        for c_idx in range(6):
            col_name = COLUMNS[c_idx]
            boat_num = c_idx + 1

            course = int(courses[boat_num])

            rank = str(edited_df.loc["ランク", col_name]).strip()
            if rank not in ["A1", "A2", "B1", "B2"]:
                rank = "B1"

            try:
                nat_rate = float(edited_df.loc["全国", col_name])
            except (ValueError, TypeError):
                nat_rate = 5.00

            try:
                loc_rate = float(edited_df.loc["当地", col_name])
            except (ValueError, TypeError):
                loc_rate = 5.00

            try:
                motor = float(edited_df.loc["2連対率", col_name])
            except (ValueError, TypeError):
                motor = 30.0

            # 各種スコアの取得
            racer_detail = calc_racer_scores_detail(
                course, rank, nat_rate, loc_rate, is_stabilizer=is_stabilizer
            )
            s_racer = racer_detail["total"]
            s_course = racer_detail["course_score"]
            s_rank = racer_detail["rank_score"]
            s_nat_score = racer_detail["nat_score"]
            s_loc_score = racer_detail["loc_score"]

            s_water = calc_water_score(wind_dir, wind_speed, tide_dir, wave_speed, boat_num)
            s_motor = calc_motor_score(motor, tide_dir, boat_num)
            
            s_start = start_scores[c_idx]
            s_exhibition = ex_scores[c_idx]

            total_score = (
                s_racer + s_water + s_motor + s_start + s_exhibition
            )

            # 買い目生成ロジック用に各艇のスコアを保存
            boat_scores[boat_num] = round(total_score, 2)

            results.append(
                {
                    "艇番": f"{boat_num}号艇",
                    "総合スコア": round(total_score, 2),
                    "コース": round(s_course, 2),
                    "階級": round(s_rank, 2),
                    "全国勝率": round(s_nat_score, 2),
                    "当地勝率": round(s_loc_score, 2),
                    "平均ST": round(s_start * 0.5, 2),
                    "水面条件": round(s_water, 2),
                    "モーター": round(s_motor, 2),
                    "展示": round(s_exhibition, 2),
                    "展示ST": round(s_start * 0.5, 2),
                }
            )

        df_res = pd.DataFrame(results)
        df_sorted = df_res.sort_values(
            by="総合スコア", ascending=False
        ).reset_index(drop=True)
        
        # 👑 先頭に「順位」列を挿入
        df_sorted.insert(0, "順位", [f"{i}位" for i in range(1, len(df_sorted) + 1)])
        st.session_state["latest_results"] = df_sorted

# -----------------------------------------------------------------------------
        # 🎯 スコア差ベースの買い目生成（logic_bettingの呼び出し）
        # -----------------------------------------------------------------------------
        wave_height_val = 10 if wave_speed == "強" else (5 if wave_speed == "弱" else 0)
        chassis_1st, c_2nd, c_3rd, formations = generate_edogawa_formation(
            boat_scores, tide=tide_dir, wave_height=wave_height_val
        )

        st.markdown("---")
        
        # 🎯 軸艇と推奨3連単フォーカスを評価指数の上に横並びで配置
        col_top_boat, col_focus = st.columns(2)
        
        with col_top_boat:
            st.subheader("🎯 軸艇（本命）")
            st.success(f"**本命軸艇**: **{chassis_1st}号艇**")
            st.write(f"- **2着候補 (2.0pt以内)**: {[f'{b}号艇' for b in c_2nd]}")
            st.write(f"- **3着候補 (4.0pt以内)**: {[f'{b}号艇' for b in c_3rd]}")

        with col_focus:
            st.subheader("📋 推奨3連単フォーカス")
            if c_2nd and c_3rd:
                # 番号順（昇順）にソート
                sorted_2nd = sorted(c_2nd)
                sorted_3rd = sorted(c_3rd)
                
                # 1着を除いた残りの全艇リスト（5艇分）
                remaining_all = sorted([b for b in range(1, 7) if b != chassis_1st])
                
                # 2着候補が残りの全艇と一致する場合は「全」に置き換え
                if sorted_2nd == remaining_all:
                    str_2nd = "全"
                else:
                    str_2nd = "".join(map(str, sorted_2nd))
                
                # 3着候補が残りの全艇と一致する場合は「全」に置き換え（ご要望のケース）
                if sorted_3rd == remaining_all:
                    str_3rd = "全"
                else:
                    str_3rd = "".join(map(str, sorted_3rd))
                
                # フォーメーション文字列の生成（例: 1-23-全）
                formation_str = f"{chassis_1st}-{str_2nd}-{str_3rd}"
                total_points = len(formations)
                
                # 画面に分かりやすく表示
                st.info(f"### 🎯 3連単フォーメーション\n# **{formation_str}**\n\n（**総点数: {total_points}点**）")
                
                # 全組合せを確認したい場合のドロップダウン
                with st.expander("🔍 すべての個別組合せ（全点数）を見る"):
                    formatted_all = ", ".join([f"{f.replace(' - ', '-')}" for f in formations])
                    st.write(formatted_all)
            else:
                st.warning("条件を満たす買い目が生成されませんでした。")

        st.markdown("---")

        # 2. 予想結果評価指数を画面全幅で表示
        st.subheader("🎯 予想結果評価指数")
        
        column_configuration = {
            "順位": st.column_config.TextColumn("順位", width="small"),
            "艇番": st.column_config.TextColumn("艇番", width="small"),
            "総合スコア": st.column_config.NumberColumn("総合スコア", format="%.2f", width="small"),
            "コース": st.column_config.NumberColumn("コース", format="%.1f", width="small"),
            "階級": st.column_config.NumberColumn("階級", format="%.1f", width="small"),
            "全国勝率": st.column_config.NumberColumn("全国勝率", format="%.2f", width="small"),
            "当地勝率": st.column_config.NumberColumn("当地勝率", format="%.2f", width="small"),
            "平均ST": st.column_config.NumberColumn("平均ST", format="%.2f", width="small"),
            "水面条件": st.column_config.NumberColumn("水面条件", format="%.2f", width="small"),
            "モーター": st.column_config.NumberColumn("モーター", format="%.2f", width="small"),
            "展示": st.column_config.NumberColumn("展示", format="%.2f", width="small"),
            "展示ST": st.column_config.NumberColumn("展示ST", format="%.2f", width="small"),
        }

        st.dataframe(
            df_sorted,
            use_container_width=True,
            hide_index=True,
            column_config=column_configuration
        )