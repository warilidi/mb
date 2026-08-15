import json
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent
DATA_DIR = PACKAGE_DIR / "data"


def load_activities() -> dict:
    path = DATA_DIR / "activities.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key, act in data.items():
        rate = act.get("rate", 1.0)
        act["calc_pts"] = lambda q, r=rate: max(1, round(q * r))
    return data


def load_achievements() -> list:
    path = DATA_DIR / "achievements.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ranks() -> list:
    path = DATA_DIR / "ranks.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_rule(rule: dict, ctx: dict) -> bool:
    r_type = rule.get("type")
    val = rule.get("val", 0)

    if r_type == "total_activities_min":
        return ctx["count"] >= val

    if r_type == "stat_min":
        stat = rule.get("stat")
        return ctx["stats"].get(stat, 0) >= val

    if r_type == "total_xp_min":
        return ctx["stats"].get("total_xp", 0) >= val

    if r_type == "streak_min":
        return ctx["stats"].get("streak_days", 0) >= val

    if r_type == "act_count_min":
        act = rule.get("act")
        return ctx["act_counts"].get(act, 0) >= val

    if r_type == "hour_range":
        min_h = rule.get("min_hour", 0)
        max_h = rule.get("max_hour", 24)
        return min_h <= ctx["hour"] < max_h

    if r_type == "all_stats_min":
        s = ctx["stats"]
        return (
            s.get("strength", 0) >= val and
            s.get("intelligence", 0) >= val and
            s.get("agility", 0) >= val and
            s.get("wisdom", 0) >= val and
            s.get("health", 0) >= val
        )

    if r_type == "today_activities_min":
        return ctx["today_count"] >= val

    return False
