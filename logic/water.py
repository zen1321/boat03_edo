import json
from pathlib import Path

def load_water_master():
    path = Path("data_json/water_conditions.json")
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def calc_water_score(wind_dir: str, wind_speed: int, tide_dir: str, wave_speed: str, boat_num: int) -> float:
    """水面条件データ（JSON）から該当する艇の加点値を取得する"""
    conditions = load_water_master()
    
    # 条件に一致するデータを探索
    matched = None
    for cond in conditions:
        if (cond.get("wind_dir") == wind_dir and 
            cond.get("wind_speed") == wind_speed and 
            cond.get("tide_dir") == tide_dir and 
            cond.get("wave_speed") == wave_speed):
            matched = cond
            break
            
    # 一致するデータがない場合のデフォルト値
    if not matched:
        return 0.0
        
    # 艇番に応じた個別スコアを取得 (boat_1_score 〜 boat_6_score)
    score_key = f"boat_{boat_num}_score"
    return float(matched.get(score_key, 0.0))