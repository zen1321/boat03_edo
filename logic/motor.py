import json
from pathlib import Path

# data_json フォルダのパス
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_JSON_DIR = PROJECT_ROOT / "data_json"

def load_json_config(filename: str):
    path = DATA_JSON_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def calc_motor_score(motor_rate: float, tide_dir: str = "", boat_num: int = 1) -> float:
    """モーターの2連対率スコアをJSONの定義に基づいて計算する"""
    rules = load_json_config("motor_score_points.json")
    
    # デフォルトスコア
    score = 0.0
    
    # 2連対率の降順にソートして上から判定（例: 40以上 -> 30以上 -> 0以上）
    sorted_rules = sorted(rules, key=lambda x: x.get("min_rate", 0), reverse=True)
    
    for rule in sorted_rules:
        if motor_rate >= rule.get("min_rate", 0):
            score = rule.get("score", 0.0)
            break
            
    # 必要に応じて潮回りや艇番に応じた補正（従来ロジックとの組み合わせ）を加えることも可能です
    return score