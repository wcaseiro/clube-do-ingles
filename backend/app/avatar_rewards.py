EVOLUTION_AVATARS = [
    {"stage": 1, "min_xp": 0, "avatar": "🤖", "name": "Luma Aprendiz"},
    {"stage": 2, "min_xp": 100, "avatar": "🛸", "name": "Explorador"},
    {"stage": 3, "min_xp": 250, "avatar": "🚀", "name": "Cadete"},
    {"stage": 4, "min_xp": 500, "avatar": "🦾", "name": "Robô Pro"},
    {"stage": 5, "min_xp": 900, "avatar": "🌟", "name": "Super Star"},
    {"stage": 6, "min_xp": 1400, "avatar": "👑", "name": "Mestre do Inglês"},
]

def avatar_stage_for_xp(xp: int | None) -> dict:
    xp = int(xp or 0)
    current = EVOLUTION_AVATARS[0]
    for item in EVOLUTION_AVATARS:
        if xp >= item["min_xp"]:
            current = item
    next_item = None
    for item in EVOLUTION_AVATARS:
        if item["min_xp"] > xp:
            next_item = item
            break
    return {
        **current,
        "current_xp": xp,
        "next": next_item,
        "progress_to_next": 100 if not next_item else max(0, min(100, round((xp - current["min_xp"]) / max(1, next_item["min_xp"] - current["min_xp"]) * 100))),
        "unlocked": [item for item in EVOLUTION_AVATARS if xp >= item["min_xp"]],
    }
