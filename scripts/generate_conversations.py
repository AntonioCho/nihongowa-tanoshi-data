#!/usr/bin/env python3
"""
vocab.json 예문 → 대화형 예문 변환 스크립트

각 Day의 10개 단어 예문이 자연스러운 실생활 대화를 이루도록 재생성.
- 각 단어의 example.sentence가 대화의 한 줄이 됨
- speaker 필드 추가 (A/B 교번)
- Day 메타에 conversationTopic/conversationTopicKo 추가
- 난이도는 레벨·Day 번호에 따라 점진적 증가
- 체크포인트 지원 (중단 후 재실행 가능)

사용법:
  cd /Users/anton/Documents/projects/nihongowa-tanoshi-data
  python scripts/generate_conversations.py [--level N5] [--dry-run] [--day 1]
"""

import anthropic
import json
import os
import time
import re
import sys
import argparse
from typing import Dict, List, Optional

# =====================
# 설정
# =====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_FILE = os.path.join(BASE_DIR, "vocab.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "scripts", "conv_checkpoint.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "vocab_conversations.json")

SLEEP_BETWEEN_CALLS = 0.5

LEVEL_TOTAL_DAYS = {"N5": 73, "N4": 136, "N3": 214, "N2": 216, "N1": 237}
LEVEL_BASE_PCT = {"N5": 0, "N4": 20, "N3": 40, "N2": 60, "N1": 80}
LEVEL_RANGE_PCT = 20
LEVELS_ORDER = ["N5", "N4", "N3", "N2", "N1"]

SYSTEM_PROMPT = """You are a Japanese language teacher creating conversational example sentences.

주어진 JLPT 레벨과 날짜에 맞는 일본어 단어 10개를 사용하여 다음 조건을 만족하는 10줄 분량의 자연스러운 대화를 작성하세요.
1. 각 문장에는 반드시 해당 단어가 자연스럽게 포함되어야 합니다.
2. 대화는 논리적으로 연결되고, 현실적이며, 실생활에서 사용 가능해야 합니다.
3. 대화 상대에 따라 격식체 또는 비격식체를 일관되게 사용해야 합니다.
4. 주어진 레벨과 날짜에 맞춰 최대한 쉬운 수준이어야 합니다 (난이도는 날짜와 레벨에 따라 점진적으로 증가해야 합니다).
5. 반드시 칸지를 사용합니다.

Output ONLY valid JSON, no markdown fences, no explanation:
{
  "conversationTopic": "Short description in English (e.g., 'Chatting at a coffee shop')",
  "conversationTopicKo": "한국어 주제 (예: '카페에서 대화')",
  "sentences": [
    {
      "sentence": "Japanese sentence using word 1",
      "meaning": "English translation",
      "meaningKo": "한국어 번역",
      "furigana": [["kanji", "reading"], ["hiragana", ""], ["。", ""]]
    }
  ]
}

Furigana rules:
- Array of [text, reading] pairs covering every character of the sentence
- Kanji: ["漢字", "よみ"]
- Hiragana/katakana/punctuation: ["文字", ""]
- Do NOT merge multiple kanji with different readings into one pair"""


# =====================
# 유틸
# =====================
def difficulty_percent(level: str, day_num: int) -> float:
    total = LEVEL_TOTAL_DAYS[level]
    base = LEVEL_BASE_PCT[level]
    return round(base + (day_num / total) * LEVEL_RANGE_PCT, 1)


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(checkpoint: dict) -> None:
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def checkpoint_key(level: str, day_num: int) -> str:
    return f"{level}-{day_num}"


# =====================
# 데이터 추출
# =====================
def extract_day_words(day_entries: List[dict]) -> List[dict]:
    """Day 배열에서 단어 항목만 추출 (subject 메타 객체 제외)."""
    return [e for e in day_entries if "id" in e]


# =====================
# API 호출
# =====================
def build_user_message(level: str, day_num: int, words: list[dict]) -> str:
    diff = difficulty_percent(level, day_num)
    total = LEVEL_TOTAL_DAYS[level]
    lines = [
        f"JLPT Level: {level}",
        f"Day: {day_num}/{total}",
        f"Difficulty: {diff}%",
        f"Topic category: {words[0].get('subject', 'General')}",
        "",
        "Vocabulary words (must appear in this order, one per sentence):",
    ]
    for i, w in enumerate(words, 1):
        lines.append(f"{i}. {w['kanji']} — {w['meaning']} / {w['meaningKo']}")
    return "\n".join(lines)


def parse_api_response(text: str) -> Optional[dict]:
    text = text.strip()
    # 마크다운 코드 블록 제거
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  [JSON 파싱 오류] {e}")
        return None


def call_api(client: anthropic.Anthropic, level: str, day_num: int, words: List[dict], retries: int = 3) -> Optional[dict]:
    user_msg = build_user_message(level, day_num, words)
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            result = parse_api_response(response.content[0].text)
            if result is None:
                raise ValueError("JSON 파싱 실패")
            if "sentences" not in result or len(result["sentences"]) != len(words):
                raise ValueError(f"sentences 수 불일치: {len(result.get('sentences', []))} ≠ {len(words)}")
            return result
        except Exception as e:
            print(f"  [오류] 시도 {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


# =====================
# vocab.json 업데이트
# =====================
SPEAKERS = ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"]


def apply_conversation_to_day(day_entries: list, api_result: dict) -> list:
    """
    Day 배열을 업데이트:
    - 메타 객체에 conversationTopic/Ko 추가
    - 각 단어의 example을 대화 문장으로 교체 + speaker 추가
    """
    sentences = api_result["sentences"]
    word_idx = 0
    updated = []

    for entry in day_entries:
        if "id" not in entry:
            # 메타 객체 → topic 추가
            meta = dict(entry)
            meta["conversationTopic"] = api_result.get("conversationTopic", "")
            meta["conversationTopicKo"] = api_result.get("conversationTopicKo", "")
            updated.append(meta)
        else:
            # 단어 항목 → example 교체
            word = dict(entry)
            if word_idx < len(sentences):
                s = sentences[word_idx]
                word["example"] = {
                    "speaker": SPEAKERS[word_idx],
                    "sentence": s.get("sentence", ""),
                    "meaning": s.get("meaning", ""),
                    "meaningKo": s.get("meaningKo", ""),
                    "furigana": s.get("furigana", []),
                }
                word_idx += 1
            updated.append(word)

    return updated


# =====================
# 메인
# =====================
def main():
    parser = argparse.ArgumentParser(description="vocab.json 예문 → 대화형 예문 변환")
    parser.add_argument("--level", choices=LEVELS_ORDER, help="처리할 레벨 (기본: 전체)")
    parser.add_argument("--day", type=int, help="특정 Day만 처리 (--level 필수)")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 구조만 출력")
    parser.add_argument("--reset", action="store_true", help="체크포인트 초기화 후 처음부터")
    args = parser.parse_args()

    print("=== vocab.json 대화형 예문 변환 ===\n")

    if not os.path.exists(VOCAB_FILE):
        print(f"[오류] {VOCAB_FILE} 없음")
        sys.exit(1)

    checkpoint = {} if args.reset else load_checkpoint()

    # 이미 진행 중인 작업이 있으면 OUTPUT_FILE에서 로드 (이전 작업 누락 방지)
    if not args.reset and checkpoint and os.path.exists(OUTPUT_FILE):
        print(f"이전 작업 이어받기: {OUTPUT_FILE} 로드 중...", end=" ", flush=True)
        vocab = load_json(OUTPUT_FILE)
    else:
        print("vocab.json 로드 중...", end=" ", flush=True)
        vocab = load_json(VOCAB_FILE)
    print("완료")
    if args.reset:
        print("체크포인트 초기화")
    elif checkpoint:
        done = sorted(checkpoint.keys())
        print(f"완료된 Day: {len(done)}개 스킵")

    client = None if args.dry_run else anthropic.Anthropic()

    levels = [args.level] if args.level else LEVELS_ORDER

    total_processed = 0
    total_failed = 0

    for level in levels:
        level_data = vocab["data"].get(level, {})
        days = sorted(level_data.keys(), key=lambda x: int(x))

        if args.day:
            days = [str(args.day)]

        print(f"\n[{level}] {len(days)} Day 처리")

        for day_str in days:
            day_num = int(day_str)
            ck = checkpoint_key(level, day_num)

            if ck in checkpoint:
                continue  # 이미 완료

            day_entries = level_data[day_str]
            words = extract_day_words(day_entries)

            if len(words) != 10:
                print(f"  Day {day_num:3d}: 단어 수 {len(words)} ≠ 10 → 스킵")
                continue

            if args.dry_run:
                print(f"  Day {day_num:3d}: [dry-run] {words[0].get('kanji')} ... {words[-1].get('kanji')}")
                print(f"           난이도: {difficulty_percent(level, day_num)}%")
                continue

            print(f"  Day {day_num:3d}: 생성 중...", end=" ", flush=True)
            result = call_api(client, level, day_num, words)

            if result is None:
                print("실패")
                total_failed += 1
                continue

            # vocab 데이터 인메모리 업데이트
            vocab["data"][level][day_str] = apply_conversation_to_day(day_entries, result)

            checkpoint[ck] = True
            save_checkpoint(checkpoint)
            save_json(OUTPUT_FILE, vocab)  # 매 Day 완료 후 즉시 저장

            total_processed += 1
            topic = result.get("conversationTopicKo", "")
            print(f"완료 [{topic}]")
            time.sleep(SLEEP_BETWEEN_CALLS)

    if args.dry_run:
        print("\n[dry-run 완료] 실제 파일 변경 없음")
        return

    if total_processed > 0:
        print(f"\n완료: {total_processed}개 Day 처리, {total_failed}개 실패")
        print(f"\n검토 후 vocab.json 교체:")
        print(f"  cp {OUTPUT_FILE} {VOCAB_FILE}")
    else:
        print("\n새로 처리된 Day 없음 (이미 완료되었거나 --dry-run)")


if __name__ == "__main__":
    main()
