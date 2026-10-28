from typing import List

def calc_exhibition_scores(ex_times: List[float], is_unreliable_water: bool) -> List[float]:
    """5. 当日の気配／展示タイムスコア"""
    scores = [0.0] * 6
    
    # タイムの有効性を確認しつつ、タイムが小さい（速い）順にソートして順位を決定
    # 同タイムの場合は同じ順位になるように処理
    valid_times = []
    for t in ex_times:
        try:
            valid_times.append(float(t))
        except (ValueError, TypeError):
            valid_times.append(6.80)  # 欠損時のデフォルト
            
    # ソートしてユニークなタイム一覧を作成
    sorted_unique_times = sorted(list(set(valid_times)))
    
    for i in range(6):
        t = valid_times[i]
        # 順位の算出 (1位始まり)
        rank = sorted_unique_times.index(t) + 1
        
        # ご指定の配点ルール
        if rank == 1:
            base_score = 1.5
        elif rank == 2:
            base_score = 0.5
        elif 3 <= rank <= 5:
            base_score = 0.0
        else:  # 6位以降
            base_score = -1.0
            
        # 難水面警告（下げ潮＋強追い風）時の影響度50%割引も継続して反映
        if is_unreliable_water:
            base_score *= 0.5
            
        scores[i] = base_score
        
    return scores