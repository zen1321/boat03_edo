def calc_start_score(avg_st: float, ex_st_raw: str, is_f_holder_flag: bool = False, rank_in_race: int = 3, is_f_holder: bool = False) -> float:
    """4. スタート力スコア（互換性維持のための個別計算用）"""
    return _calc_single_start(avg_st, ex_st_raw, is_f_holder, rank_in_race, is_f_holder_flag)


def calc_all_start_scores(st_data_list: list) -> list:
    """
    全6艇分のスタートデータをまとめて受け取り、F持ちを除外して順位を判定した上で
    正確なスタート力スコアのリストを返す関数
    st_data_listの要素: {"avg_st": float, "ex_st": str, "is_f": bool, "is_f_holder": bool}
    """
    parsed_entries = []
    for i, data in enumerate(st_data_list):
        avg_st = data.get("avg_st", 0.15)
        ex_st_raw = str(data.get("ex_st", "")).strip().upper()
        is_ex_f = data.get("is_f", False)  # 展示などでFを切っている状態
        is_f_holder = data.get("is_f_holder", False)  # 👈 画面の「F持ち」チェックボックス
        
        has_f = "F" in ex_st_raw or is_ex_f
        
        # 数値としてのSTを抽出
        val = 99.0
        if has_f:
            f_val_str = ex_st_raw.replace("F", "").replace(".", "0.")
            try:
                val = float(f_val_str)
            except ValueError:
                val = 0.10
        else:
            try:
                val = float(ex_st_raw)
            except ValueError:
                val = 99.0
                
        parsed_entries.append({
            "index": i,
            "avg_st": avg_st,
            "ex_st_raw": ex_st_raw,
            "is_f": has_f,
            "is_f_holder": is_f_holder,  # 保持
            "val": val
        })

    # 「直前STがF持ち」を除外したグループで直前STの順位付けを行う
    non_f_entries = [e for e in parsed_entries if not e["is_f"] and e["val"] != 99.0]
    non_f_entries.sort(key=lambda x: x["val"])

    rank_map = {}
    for rank_idx, entry in enumerate(non_f_entries, start=1):
        rank_map[entry["index"]] = rank_idx
        
    for entry in parsed_entries:
        if entry["index"] not in rank_map:
            rank_map[entry["index"]] = 99

    # 各艇のスコアを計算
    scores = []
    for i, data in enumerate(parsed_entries):
        r_num = rank_map[i]
        score = _calc_single_start(
            data["avg_st"], 
            data["ex_st_raw"], 
            data["is_f"], 
            rank_in_race=r_num,
            is_f_holder_flag=data["is_f_holder"]  # 👈 ペナルティフラグを渡す
        )
        scores.append(score)

    return scores


def _calc_single_start(avg_st: float, ex_st_raw: str, is_f: bool, rank_in_race: int, is_f_holder_flag: bool = False) -> float:
    # ① 平均STの調整
    if avg_st <= 0.12:
        avg_score = 2.0
    elif avg_st <= 0.14:
        avg_score = 1.0
    elif avg_st <= 0.16:
        avg_score = 0.0
    elif avg_st <= 0.18:
        avg_score = -0.5
    else:
        avg_score = -1.5

    ex_st_str = str(ex_st_raw).strip().upper()
    
    # ② 直前STでFを切っている場合の調整
    if "F" in ex_st_str or is_f:
        f_val_str = ex_st_str.replace("F", "").replace(".", "0.")
        try:
            f_val = float(f_val_str)
        except ValueError:
            f_val = 0.10
            
        if f_val <= 0.05:
            f_score = 1.0
        elif f_val <= 0.09:
            f_score = 0.5
        else:
            f_score = 0.0
        base_score = avg_score + f_score
    else:
        # ③ 通常の直前STデータの判定
        try:
            val = float(ex_st_str)
        except ValueError:
            val = 99.0

        is_top_2 = rank_in_race <= 2

        if is_top_2 and avg_st <= 0.14:
            st_cond_score = 1.5
        elif is_top_2 and avg_st >= 0.15:
            st_cond_score = 0.5
        elif (not is_top_2) and avg_st <= 0.14:
            st_cond_score = 1.0
        else:
            st_cond_score = 0.0

        base_score = avg_score + st_cond_score

    # ④ 🚨 画面でチェックされた「F持ち」ペナルティの適用
    if is_f_holder_flag:
        base_score -= 1.0  # 👈 F持ちによる慎重化ペナルティ（必要に応じて -1.5 などに変更可能）

    return base_score