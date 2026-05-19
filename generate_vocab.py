#!/usr/bin/env python3
"""
JLPT N5 단어 목록 → vocabData.json 변환 스크립트
- Claude API로 영문 뜻, furigana, 예문 자동 생성
- Day 단위 배치 처리 (10개씩)
- Resume 지원 (중단 후 재실행 시 완료된 Day 스킵)
- 완료 후 sample.json 형식으로 최종 JSON 출력
"""

import anthropic
import json
import os
import time
import re
import sys

# =====================
# 설정
# =====================
WORDS_FILE = "vocab/N3_words.txt"           # 단어 목록 파일
PROMPT_FILE = "VOCAB_PROMPT.md"       # API 프롬프트 파일
PROGRESS_FILE = "n3_progress.json"    # 중간 저장 파일
OUTPUT_FILE = "vocabData_N3.json"     # 최종 출력 파일

LEVEL = "N3"
SLEEP_BETWEEN_CALLS = 1.0             # API 호출 간격(초)

# 품사 한→영 매핑
PARTS_MAP = {
    "동사": "verb",
    "명사": "noun",
    "い형용사": "i-adjective",
    "な형용사": "na-adjective",
    "부사": "adverb",
    "접속사": "conjunction",
    "대명사": "pronoun",
    "표현": "expression",
    "연체사": "prenoun adjective",
    "접미사": "suffix",
    "감탄사": "interjection",
}


# =====================
# 파일 파싱
# =====================
def parse_words_file(filepath):
    """
    N5_words.txt 파싱 → {day_num: [(word, parts_ko, meaning_ko), ...]} 반환
    형식: N5:Day1:いる:동사:있다(사람·동물)
    """
    days = {}
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 5:
                continue
            level, day_str, word, parts_ko, meaning_ko = (
                parts[0], parts[1], parts[2], parts[3], ":".join(parts[4:])
            )
            if level != LEVEL:
                continue
            # Day 번호 추출
            m = re.match(r"Day(\d+)", day_str)
            if not m:
                continue
            day_num = int(m.group(1))
            if day_num not in days:
                days[day_num] = []
            days[day_num].append((word, parts_ko, meaning_ko))
    return days


def load_prompt(filepath):
    with open(filepath, encoding="utf-8") as f:
        return f.read()


# =====================
# 진행 상황 저장/로드
# =====================
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# =====================
# API 호출
# =====================
def build_user_message(word_list):
    """
    [(word, parts_ko, meaning_ko), ...] → API 입력 텍스트
    """
    lines = []
    for word, parts_ko, meaning_ko in word_list:
        lines.append(f"{word}|{parts_ko}|{meaning_ko}")
    return "\n".join(lines)


def call_api(client, system_prompt, word_list, retries=3):
    user_msg = build_user_message(word_list)
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = response.content[0].text.strip()
            # JSON 파싱
            # 마크다운 코드블록 제거
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
            data = json.loads(text)
            if isinstance(data, dict):
                data = [data]
            return data
        except json.JSONDecodeError as e:
            print(f"  [오류] JSON 파싱 실패 (시도 {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
        except Exception as e:
            print(f"  [오류] API 호출 실패 (시도 {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


# =====================
# 데이터 조합
# =====================
def make_entry(day_num, idx, word, parts_ko, meaning_ko, api_data):
    """
    단어 + API 응답 → vocabData.json 형식의 단일 항목
    """
    level_lower = LEVEL.lower()
    entry_id = f"{level_lower}-{day_num}-{idx}"
    parts_en = PARTS_MAP.get(parts_ko, parts_ko)

    return {
        "id": entry_id,
        "kanji": api_data.get("kanji", word),
        "meaning": api_data.get("meaning", ""),
        "meaningKo": meaning_ko,
        "parts": parts_en,
        "subject": api_data.get("subject", ""),
        "furigana": api_data.get("furigana", [[word, ""]]),
        "example": api_data.get("example", {}),
    }


# =====================
# 메인
# =====================
def main():
    print(f"=== {LEVEL} vocabData.json 생성 시작 ===\n")

    # 파일 로드
    if not os.path.exists(WORDS_FILE):
        print(f"[오류] 단어 파일 없음: {WORDS_FILE}")
        sys.exit(1)
    if not os.path.exists(PROMPT_FILE):
        print(f"[오류] 프롬프트 파일 없음: {PROMPT_FILE}")
        sys.exit(1)

    days = parse_words_file(WORDS_FILE)
    prompt = load_prompt(PROMPT_FILE)
    progress = load_progress()

    print(f"총 {len(days)} Day, {sum(len(v) for v in days.values())} 단어 로드 완료")
    print(f"이미 완료된 Day: {sorted([int(k) for k in progress.keys()])}\n")

    # Anthropic 클라이언트
    client = anthropic.Anthropic()

    # Day별 처리
    sorted_days = sorted(days.keys())
    for day_num in sorted_days:
        day_key = str(day_num)
        if day_key in progress:
            print(f"Day {day_num:3d}: 스킵 (완료)")
            continue

        word_list = days[day_num]
        print(f"Day {day_num:3d}: {len(word_list)}개 처리 중...", end=" ", flush=True)

        # API 호출
        api_results = call_api(client, prompt, word_list)

        if api_results is None:
            print("실패 → 스킵")
            continue

        if len(api_results) != len(word_list):
            print(f"경고: 응답 수({len(api_results)}) ≠ 요청 수({len(word_list)})")

        # 항목 조합
        entries = []
        for idx, (word, parts_ko, meaning_ko) in enumerate(word_list, start=1):
            if idx - 1 < len(api_results):
                api_data = api_results[idx - 1]
            else:
                api_data = {"kanji": word, "meaning": "", "furigana": [[word, ""]], "subject": "", "example": {}}
            entry = make_entry(day_num, idx, word, parts_ko, meaning_ko, api_data)
            entries.append(entry)

        progress[day_key] = entries
        save_progress(progress)
        print(f"완료 ({len(entries)}개)")
        time.sleep(SLEEP_BETWEEN_CALLS)

    # 최종 JSON 조합
    print(f"\n=== 최종 JSON 생성 중 ===")
    result_data = {}
    for day_num in sorted_days:
        day_key = str(day_num)
        if day_key in progress:
            result_data[str(day_num)] = progress[day_key]

    output = {
        "version": "1.0.0",
        "updatedAt": "2026-05-19T00:00:00Z",
        "data": {
            LEVEL: result_data
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in result_data.values())
    print(f"완료: {OUTPUT_FILE} ({len(result_data)} Day, {total} 단어)")


if __name__ == "__main__":
    main()
