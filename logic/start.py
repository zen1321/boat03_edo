def calc_start_score(avg_st: float, ex_st_raw: str, is_f_holder: bool, rank_in_race: int = 3) -> float:
    """4. スタート力スコア（互換性維持のための個別計算用）"""
    # 従来通りの個別計算（順位が直接渡されない場合はデフォルト3位扱い等）
    return _calc_single_start(avg_st, ex_st_raw, is_f_holder, rank_in_race)


def calc_all_start_scores(st_data_list: list) -> list:
    """
    全6艇分のスタートデータをまとめて受け取り、F持ちを除外して順位を判定した上で
    正確なスタート力スコアのリストを返す関数
    st_data_listの要素: {"avg_st": float, "ex_st": str, "is_f": bool}
    """
    # 1. 各艇の有効な直前ST数値とF状態を抽出し、F持ち（直前STでFを切っている、またはFホルダー）を特定
    parsed_entries = []
    for i, data in enumerate(st_data_list):
        avg_st = data.get("avg_st", 0.15)
        ex_st_raw = str(data.get("ex_st", "")).strip().upper()
        is_f_holder = data.get("is_f", False)
        
        has_f = "F" in ex_st_raw or is_f_holder
        
        # 数値としてのSTを抽出（Fの場合は数値化）
        val = 99.0  # データなし用のおきあがり値
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
                val = 99.0  # 欠損
                
        parsed_entries.append({
            "index": i,
            "avg_st": avg_st,
            "ex_st_raw": ex_st_raw,
            "is_f": has_f,
            "val": val
        })

    # 2. 「直前STがF持ち」を除外したグループで直前STの順位付けを行う
    # ※F持ちを除いて順位をつけるため、F持ち以外の艇だけでソート
    non_f_entries = [e for e in parsed_entries if not e["is_f"] and e["val"] != 99.0]
    non_f_entries.sort(key=lambda x: x["val"]) # タイムが小さい（速い）順

    # 順位を割り当て (1位〜)
    rank_map = {}
    for rank_idx, entry in enumerate(non_f_entries, start=1):
        rank_map[entry["index"]] = rank_idx
        
    # F持ちやデータなしの艇には仮の順位（圏外の3位以下など、例えば5位など）を割り振る
    for entry in parsed_entries:
        if entry["index"] not in rank_map:
            rank_map[entry["index"]] = 99 # 3位以下扱い

    # 3. 各艇のスコアを計算
    scores = []
    for i, data in enumerate(parsed_entries):
        r_num = rank_map[i]
        score = _calc_single_start(data["avg_st"], data["ex_st_raw"], data["is_f"], rank_in_race=r_num)
        scores.append(score)

    return scores


def _calc_single_start(avg_st: float, ex_st_raw: str, is_f_holder: bool, rank_in_race: int) -> float:
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
    if "F" in ex_st_str or is_f_holder:
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
        return avg_score + f_score

    # ③ 通常の直前STデータの判定
    try:
        val = float(ex_st_str)
    except ValueError:
        # 直前STデータなし(欠損) : 0.0点
        return avg_score + 0.0

    is_top_2 = rank_in_race <= 2

    # 直前STが2位以内 ＆ 平均ST 0.14以下 : 1.5点
    if is_top_2 and avg_st <= 0.14:
        st_cond_score = 1.5
    # 直前STが2位以内 ＆ 平均ST 0.15以上 : 0.5点
    elif is_top_2 and avg_st >= 0.15:
        st_cond_score = 0.5
    # 直前STが3位以内 ＆ 平均ST 0.14以下 : 1.0点
    elif (not is_top_2) and avg_st <= 0.14:
        st_cond_score = 1.0
    # それ以外（3位以内 ＆ 平均ST 0.15以上）: 0.0点
    else:
        st_cond_score = 0.0

    return avg_score + st_cond_score