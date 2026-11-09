"""coaster_db.csv(원본) -> data/clean.csv (정제본)

정제 규칙 (README.md '정제 기록'과 같은 내용)
1. 같은 coaster_name 이 여러 행 = 이전·재설치 기록 -> 가장 최근(year_introduced 최대) 1행만 남김
2. Height / Length / Drop : "50 ft (15 m)" 같은 글자 -> 미터(m) 숫자
   (원본의 height_ft 칸은 1,087행 중 171행만 차 있어서 쓰지 않고 Height 글자에서 다시 뽑음)
3. Speed : speed_mph -> km/h 숫자
4. Duration : "1:32" / "2 minutes" / "90 seconds" -> 초(s) 숫자
5. Type -> 존(zone) 10개로 묶음 (키워드 우선순위 순서로 첫 번째 맞는 것)
6. Status -> 운영중 / 철거·폐쇄 / 기타 3개로 묶음
7. 이상치: 높이 > 200 m, 속도 > 260 km/h, 길이 > 3,000 m 는 단위 오류로 보고 비움(NaN)
"""
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

raw = pd.read_csv("data/coaster_db.csv")
df = raw.copy()

# 1) 중복 이름: 최근 설치 1행만
df = df.sort_values("year_introduced").drop_duplicates("coaster_name", keep="last")

NUM_UNIT = re.compile(r"([\d][\d,]*\.?\d*)\s*(m|ft|km|mi)\b")


def to_meters(text):
    """'72.5 ft (22.1 m)' -> 22.1 . m 값이 있으면 m, 없으면 ft 를 환산"""
    if not isinstance(text, str):
        return None
    found = {}
    for num, unit in NUM_UNIT.findall(text):
        found.setdefault(unit, float(num.replace(",", "")))
    if "m" in found:
        return found["m"]
    if "ft" in found:
        return round(found["ft"] * 0.3048, 1)
    if "km" in found:
        return found["km"] * 1000
    return None


def to_seconds(text):
    if not isinstance(text, str):
        return None
    t = text.lower()
    m = re.search(r"(\d+):(\d{2})", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    mins = re.search(r"([\d.]+)\s*min", t)
    secs = re.search(r"([\d.]+)\s*s", t)
    total = 0.0
    if mins:
        total += float(mins.group(1)) * 60
    if secs and (not mins or secs.start() > mins.end()):
        total += float(secs.group(1))
    return total or None


df["height_m"] = df["Height"].map(to_meters)
df["length_m"] = df["Length"].map(to_meters)
df["drop_m"] = df["Drop"].map(to_meters)
df["speed_kmh"] = (df["speed_mph"] * 1.609344).round(1)
df["duration_s"] = df["Duration"].map(to_seconds)
df["inversions"] = df["Inversions_clean"]
df["gforce"] = df["Gforce_clean"]

# 7) 단위 오류로 보이는 값 비우기
df.loc[df["height_m"] > 200, "height_m"] = None
df.loc[df["drop_m"] > 200, "drop_m"] = None
df.loc[df["speed_kmh"] > 260, "speed_kmh"] = None
df.loc[df["length_m"] > 3000, "length_m"] = None
df.loc[(df["duration_s"] > 600) | (df["duration_s"] < 10), "duration_s"] = None

# 5) 존 나누기 (위에서부터 먼저 맞는 것)
ZONES = [
    ("wild_mouse", r"wild mouse"),
    ("spinning", r"spinning"),
    ("mine_train", r"mine train"),
    ("flying", r"flying|wing|4th dimension"),
    ("inverted", r"inverted|suspended"),
    ("launched", r"launch"),
    ("shuttle", r"shuttle|boomerang"),
    ("family", r"family|junior|kiddie"),
]


def zone_of(row):
    t = str(row["Type"]).lower()
    for key, pat in ZONES:
        if re.search(pat, t):
            return key
    if row["Type_Main"] == "Wood":
        return "wooden"
    return "steel"


df["zone"] = df.apply(zone_of, axis=1)

# 6) 상태 묶기
status = df["Status"].fillna("").str.lower()
df["status_group"] = "기타"
df.loc[status.str.startswith("operating"), "status_group"] = "운영중"
df.loc[status.str.contains("removed|closed|demolish|dismantl|sbno|discontinued"), "status_group"] = "철거·폐쇄"

keep = ["coaster_name", "Location", "Manufacturer", "Model", "Type", "Type_Main", "zone",
        "status_group", "year_introduced", "latitude", "longitude",
        "height_m", "length_m", "drop_m", "speed_kmh", "duration_s", "inversions", "gforce"]
clean = df[keep].rename(columns={"coaster_name": "name", "Location": "park", "Manufacturer": "maker",
                                 "Model": "model", "Type": "type_raw", "Type_Main": "material",
                                 "year_introduced": "year"})
clean.to_csv("data/clean.csv", index=False, encoding="utf-8-sig")

print(f"행: {len(raw)} -> {len(clean)} (중복 이름 {len(raw) - len(clean)}행 제거)")
print("칸별 채워진 개수:")
print(clean[["height_m", "length_m", "drop_m", "speed_kmh", "duration_s", "gforce"]].notnull().sum().to_string())
print("\n존별 개수:")
print(clean["zone"].value_counts().to_string())
print("\n상태:")
print(clean["status_group"].value_counts().to_string())
