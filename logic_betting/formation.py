import pandas as pd
from typing import Dict, List, Tuple

def generate_edogawa_formation(boat_scores: Dict[int, float], tide: str, wave_height: int) -> Tuple[int, List[int], List[int], List[str]]:
    """
    各艇の総合スコアを基に、江戸川の難水面特性およびスコア差ルールに従って
    1着（軸）、2着候補、3着候補、および推奨買い目（フォーメーション）を生成する。
    
    スコア差ルール：
    - 2着：2位のスコアからスコア差 2.0pt 以内の選手
    - 3着：2位のスコアからスコア差 4.0pt 以内の選手
    """
    # スコアが高い順にソート (艇番号, スコア)
    sorted_boats = sorted(boat_scores.items(), key=lambda x: x[1], reverse=True)
    
    if len(sorted_boats) < 2:
        raise ValueError("スコアデータが不足しています（最低6艇分必要です）")
        
    rank1_boat, rank1_score = sorted_boats[0]
    rank2_boat, rank2_score = sorted_boats[1]
    
    # 【1着の選定】原則は最高スコア艇
    # 江戸川の特殊条件（例：下げ潮大荒れで1位と2位が僅差の場合のスライド等）
    chassis_1st = rank1_boat
    if "下げ潮" in tide and wave_height >= 10:
        if (rank1_score - rank2_score) <= 1.5:
            chassis_1st = rank2_boat

    # 【2着の選定】2位のスコアから「2.0pt以内」の選手（1着に選ばれた艇を除く）
    candidates_2nd = []
    for boat, score in sorted_boats:
        if boat == chassis_1st:
            continue
        if (rank2_score - score) <= 2.0 or score >= (rank2_score - 2.0):
            candidates_2nd.append(boat)
            
    # 【3着の選定】2位のスコアから「4.0pt以内」の選手（1着に選ばれた艇を除く）
    candidates_3rd = []
    for boat, score in sorted_boats:
        if boat == chassis_1st:
            continue
        if (rank2_score - score) <= 4.0 or score >= (rank2_score - 4.0):
            candidates_3rd.append(boat)

    candidates_2nd = list(dict.fromkeys(candidates_2nd))
    candidates_3rd = list(dict.fromkeys(candidates_3rd))

    # 【買い目（3連単フォーメーション文字列）の生成】
    formations = []
    for b2 in candidates_2nd:
        for b3 in candidates_3rd:
            if b2 != b3:
                formations.append(f"{chassis_1st} - {b2} - {b3}")
                
    return chassis_1st, candidates_2nd, candidates_3rd, formations