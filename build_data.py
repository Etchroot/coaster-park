"""data/clean.csv -> web/data.js (3D 페이지가 읽는 유형별 통계)

숫자는 모두 여기서 계산하고, 페이지는 받은 숫자를 그리기만 해요 (검산할 곳이 한 군데).
비율·중앙값 옆에는 항상 분모 n(값이 있는 코스터 수)을 같이 넣어요.
"""
import json
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
df = pd.read_csv("data/clean.csv")

ZONE_INFO = {
    "launched":   ("발사형 코스터", "Launch Coaster", "언덕 대신 모터로 쏘아 올린다", "#ff4d4d"),
    "inverted":   ("인버티드 코스터", "Inverted Coaster", "레일 아래에 매달려 발이 허공에", "#7c5cff"),
    "flying":     ("플라잉 · 윙 코스터", "Flying / Wing", "엎드리거나 레일 옆에 날개처럼", "#20c4e8"),
    "wooden":     ("우든 코스터", "Wooden Coaster", "나무 구조물의 덜컹거림", "#c98a4b"),
    "steel":      ("클래식 스틸 코스터", "Steel Sit-down", "가장 흔한 기본형 · 하이퍼 포함", "#4f8cff"),
    "wild_mouse": ("와일드 마우스", "Wild Mouse", "급커브를 꺾는 작은 1인 카", "#ffb020"),
    "spinning":   ("스피닝 코스터", "Spinning Coaster", "카가 빙글빙글 돈다", "#ff5fb0"),
    "mine_train": ("마인 트레인", "Mine Train", "광산 열차 테마의 가족형", "#8f6a3a"),
    "shuttle":    ("셔틀 · 부메랑", "Shuttle / Boomerang", "갔던 길을 뒤로 되돌아온다", "#2fd17a"),
    "family":     ("패밀리 · 주니어", "Family / Junior", "키 작은 친구도 탈 수 있는", "#9ad94a"),
}
ORDER = ["launched", "inverted", "flying", "steel", "wooden",
         "shuttle", "spinning", "wild_mouse", "mine_train", "family"]


def med(s):
    s = s.dropna()
    return {"v": None if s.empty else round(float(s.median()), 1), "n": int(len(s))}


def stat_block(g):
    inv = g["inversions"]
    return {
        "count": int(len(g)),
        "operating": int((g["status_group"] == "운영중").sum()),
        "speed": med(g["speed_kmh"]),
        "height": med(g["height_m"]),
        "length": med(g["length_m"]),
        "duration": med(g["duration_s"]),
        "gforce": med(g["gforce"]),
        "inv_mean": round(float(inv.mean()), 2),
        "inv_share": round(float((inv > 0).mean() * 100), 1),
        "speed_max": None if g["speed_kmh"].dropna().empty else float(g["speed_kmh"].max()),
        "height_max": None if g["height_m"].dropna().empty else float(g["height_m"].max()),
    }


def ride(r):
    def clean(v):
        if pd.isna(v):
            return None
        if hasattr(v, "item"):  # numpy 숫자 -> 파이썬 숫자
            v = v.item()
        return round(v, 1) if isinstance(v, float) else v
    return {k: clean(r[c]) for k, c in [("name", "name"), ("park", "park"), ("maker", "maker"),
                                         ("year", "year"), ("speed", "speed_kmh"), ("height", "height_m"),
                                         ("length", "length_m"), ("inv", "inversions")]}


zones = []
for key in ORDER:
    g = df[df["zone"] == key]
    ko, en, tagline, color = ZONE_INFO[key]
    decades = (g["year"] // 10 * 10).value_counts().sort_index()
    top = g.dropna(subset=["speed_kmh"]).nlargest(5, "speed_kmh")
    makers = g["maker"].value_counts().head(3)
    zones.append({
        "key": key, "name": ko, "en": en, "tagline": tagline, "color": color,
        "stats": stat_block(g),
        "decades": [{"decade": int(d), "n": int(n)} for d, n in decades.items() if d >= 1950],
        "top": [ride(r) for _, r in top.iterrows()],
        "makers": [{"name": m, "n": int(n)} for m, n in makers.items()],
    })

overall = stat_block(df)
overall["fastest"] = ride(df.loc[df["speed_kmh"].idxmax()])
overall["tallest"] = ride(df.loc[df["height_m"].idxmax()])
overall["most_inv"] = ride(df.loc[df["inversions"].idxmax()])

out = {
    "source": "Kaggle · robikscube/rollercoaster-database (coaster_db.csv, Wikipedia 기반)",
    "license": "CC0: Public Domain",
    "rows_raw": 1087, "rows_clean": int(len(df)),
    "overall": overall, "zones": zones,
}
os.makedirs("web", exist_ok=True)
with open("web/data.js", "w", encoding="utf-8") as f:
    f.write("window.PARK_DATA = ")
    json.dump(out, f, ensure_ascii=False, indent=1)
    f.write(";\n")

print("저장: web/data.js")
for z in zones:
    s = z["stats"]
    print(f"{z['name']:<12} {s['count']:>4}개  속도 중앙값 {s['speed']['v']}km/h(n={s['speed']['n']})  "
          f"높이 {s['height']['v']}m  역회전 있는 비율 {s['inv_share']}%")
print("최고 속도:", overall["fastest"]["name"], overall["fastest"]["speed"])
print("최고 높이:", overall["tallest"]["name"], overall["tallest"]["height"])
print("최다 역회전:", overall["most_inv"]["name"], overall["most_inv"]["inv"])
