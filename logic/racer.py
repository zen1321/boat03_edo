import json
from pathlib import Path

# data_json フォルダのパスを正しく解決
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_JSON_DIR = PROJECT_ROOT / "data_json"

def _load_json_config(filename: str) -> dict:
    path = DATA_JSON_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def calc_racer_scores_detail(course: int, rank: str, nat_rate: float, loc_rate: float, is_stabilizer: bool = False):
    """1. 選手の実力・適性スコア（JSONから配点を取得）"""
    
    # JSONからコース点数を取得
    course_points = _load_json_config("course_points.json")
    course_score = course_points.get(str(course), 0.5)
    
    # JSONから級別ランク点数を取得
    rank_points = _load_json_config("rank_points.json")
    rank_score = rank_points.get(rank, 0.0)
    
    # ③ 全国勝率スコア
    nat_score = nat_rate * 0.5
    # ④ 当地勝率スコア (0の場合は「全国勝率」×0.75)
    if loc_rate > 0:
        loc_score = loc_rate * 1.0
        # 安定板装着時は当地勝率の価値を1.2倍に強調
        if is_stabilizer:
            loc_score *= 1.2
    else:
        loc_score = nat_rate * 0.75
        
    total = course_score + rank_score + nat_score + loc_score
    
    return {
        "total": total,
        "course_score": course_score,
        "rank_score": rank_score,
        "nat_score": nat_score,
        "loc_score": loc_score
    }

def calc_racer_score(course: int, rank: str, nat_rate: float, loc_rate: float) -> float:
    """互換性のための従来関数"""
    detail = calc_racer_scores_detail(course, rank, nat_rate, loc_rate)
    return detail["total"]