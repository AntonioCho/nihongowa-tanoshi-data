import json
import argparse
import sys

EMOJI_NUMBERS = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

GRADE_HASHTAGS = {
    "N5": "#JLPTN5 #N5단어 #일본어N5",
    "N4": "#JLPTN4 #N4단어 #일본어N4",
    "N3": "#JLPTN3 #N3단어 #일본어N3",
    "N2": "#JLPTN2 #N2단어 #일본어N2",
    "N1": "#JLPTN1 #N1단어 #일본어N1",
}

def build_caption(grade: str, level: str, items: list) -> str:
    divider = "━━━━━━━━━━━━━━━━━"
    lines = []

    # 헤더
    lines.append(f"🇯🇵 일본어 JLPT {grade} · Lv.{level}")
    lines.append("")
    lines.append(divider)
    lines.append("📚 오늘의 단어")
    lines.append(divider)

    for i, item in enumerate(items):
        emoji = EMOJI_NUMBERS[i] if i < len(EMOJI_NUMBERS) else f"{i+1}."
        kanji = item.get("kanji", "")
        kana = item.get("kana", "")
        meaning_ko = item.get("meaningKo", "")
        meaning_en = item.get("meaning", "")
        parts = item.get("parts", "")
        ex = item.get("example", {})

        lines.append("")
        lines.append(f"{emoji} {kanji}  {kana}")
        lines.append(f"   {meaning_ko}  |  {meaning_en}  ({parts})")
        lines.append("")
        lines.append(f"   {ex.get('sentence', '')}")
        lines.append(f"   {ex.get('kana', '')}")
        lines.append(f"   {ex.get('meaningKo', '')}")

    # 해시태그
    lines.append("")
    lines.append(divider)
    grade_tags = GRADE_HASHTAGS.get(grade, "")
    lines.append(f"#하루10단어 #10Daily #일본어 #일본어공부 #JLPT {grade_tags} #nihongo #일어공부 #어학공부")
    lines.append(divider)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="인스타 릴스용 일본어 단어 캡션 생성기")
    parser.add_argument("grade", help="JLPT 등급 (예: N5, N4, N3, N2, N1)")
    parser.add_argument("level", help="레벨 번호 (예: 1, 2, 3)")
    parser.add_argument("-c", "--copy", action="store_true", help="결과를 클립보드에 복사")
    parser.add_argument("-f", "--file", default="vocabData.json", help="JSON 파일 경로 (기본값: vocabData.json)")
    args = parser.parse_args()

    grade = args.grade.upper()
    level = str(args.level)

    with open(args.file, encoding="utf-8") as f:
        raw = json.load(f)

    data = raw.get("data", raw)  # data 키가 있으면 사용, 없으면 루트 사용

    if grade not in data:
        print(f"오류: 등급 '{grade}'를 찾을 수 없습니다. 사용 가능: {list(data.keys())}", file=sys.stderr)
        sys.exit(1)

    if level not in data[grade]:
        available = sorted(data[grade].keys(), key=lambda x: int(x))
        print(f"오류: {grade}에서 레벨 '{level}'을 찾을 수 없습니다. 사용 가능: {available}", file=sys.stderr)
        sys.exit(1)

    items = data[grade][level]
    caption = build_caption(grade, level, items)

    print(caption)

    if args.copy:
        try:
            import subprocess
            subprocess.run("pbcopy", input=caption.encode("utf-8"), check=True)
            print("\n✅ 클립보드에 복사되었습니다.", file=sys.stderr)
        except Exception as e:
            print(f"\n⚠️ 클립보드 복사 실패: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
