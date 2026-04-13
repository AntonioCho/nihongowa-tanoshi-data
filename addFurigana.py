"""
vocabData.json의 각 단어에 furigana 필드를 추가합니다.

word.furigana  : word.kanji를 kana 필드 기반으로 정렬
example.furigana: example.sentence를 MeCab으로 형태소 분석

furigana 형식: [["원문세그먼트", "히라가나"], ...]
- 한자 포함 세그먼트: ["着き", "つき"]
- 히라가나/카타카나/기호:  ["に", ""]

사용법:
    python3 addFurigana.py
    python3 addFurigana.py --overwrite   # 기존 furigana 덮어쓰기
"""

import json
import argparse
import re
import fugashi

tagger = fugashi.Tagger()

def contains_kanji(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def kata_to_hira(text):
    """카타카나 → 히라가나 변환."""
    return ''.join(
        chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c
        for c in text
    )

def get_clean_kana(kana):
    """kana 필드에서 로마자 발음 제거."""
    return re.sub(r'\s*\[.*?\]', '', kana).strip()

def build_word_furigana(kanji: str, clean_kana: str) -> list:
    """
    word.kanji + 정제된 kana를 정렬해 furigana 리스트 반환.
    뒤에서부터 공통 히라가나 suffix를 찾아 한자 부분에만 독음을 매핑.
    예: 着く + つく → [["着", "つ"], ["く", ""]]
        眼鏡 + めがね → [["眼鏡", "めがね"]]
        あげる + あげる → [["あげる", ""]]
    """
    if not kanji or not clean_kana:
        return [[kanji, '']]
    if not contains_kanji(kanji):
        return [[kanji, '']]

    # 뒤에서부터 히라가나 공통 suffix 탐색
    suffix_len = 0
    for i in range(1, min(len(kanji), len(clean_kana)) + 1):
        k_char = kanji[-i]
        r_char = clean_kana[-i]
        if re.match(r'[\u3041-\u3096]', k_char) and k_char == r_char:
            suffix_len = i
        else:
            break

    if suffix_len == 0:
        return [[kanji, clean_kana]]

    result = []
    stem_kanji = kanji[:-suffix_len]
    stem_kana = clean_kana[:-suffix_len]
    if stem_kanji:
        result.append([stem_kanji, stem_kana])
    result.append([kanji[-suffix_len:], ''])
    return result

def build_sentence_furigana(sentence: str) -> list:
    """문장을 형태소 분리해 [원문, 후리가나] 리스트 반환."""
    furigana = []
    for word in tagger(sentence):
        orig = word.surface
        try:
            yomi = word.feature.kana if word.feature.kana else ''
        except Exception:
            yomi = ''
        hira = kata_to_hira(yomi)
        if contains_kanji(orig) and hira and hira != orig:
            furigana.append([orig, hira])
        else:
            furigana.append([orig, ''])
    return furigana

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--overwrite', action='store_true', help='기존 furigana 덮어쓰기')
    parser.add_argument('--input', default='vocabData.json')
    parser.add_argument('--output', default='vocabData.json')
    args = parser.parse_args()

    with open(args.input, encoding='utf-8') as f:
        data = json.load(f)

    word_added = 0
    example_added = 0
    skipped = 0

    for grade, levels in data['data'].items():
        for level_key, words in levels.items():
            for word in words:
                # word.furigana
                if 'furigana' not in word or args.overwrite:
                    clean_kana = get_clean_kana(word.get('kana', ''))
                    word['furigana'] = build_word_furigana(word.get('kanji', ''), clean_kana)
                    word_added += 1
                else:
                    skipped += 1

                # example.furigana
                ex = word.get('example')
                if ex:
                    sentence = ex.get('sentence', '')
                    if sentence and ('furigana' not in ex or args.overwrite):
                        ex['furigana'] = build_sentence_furigana(sentence)
                        example_added += 1

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'완료: word.furigana {word_added}개, example.furigana {example_added}개 추가, {skipped}개 건너뜀')

if __name__ == '__main__':
    main()
