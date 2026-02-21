# fix_vocab_main.py
import json
import re
import os
# 분리된 딕셔너리 모듈 불러오기
from fix_vocab_dict import MANUAL_MEANING_FIXES, MANUAL_POS_FIXES

INPUT_FILE = 'vocabData.json'
OUTPUT_FILE = 'vocabData_fixed.json'

# 형용사 어미(~다, ~이다)를 관형어(~한, ~인)로 자동 변환하는 함수
def fix_adjective_korean(text):
    if not text:
        return text
    
    # 여러 뜻이 콤마로 연결되어 있을 수 있으므로 분리하여 처리
    meanings = [m.strip() for m in text.split(',')]
    fixed_meanings = []
    
    # 빈번하게 사용되는 불규칙 형용사 변환 사전 (하드코딩)
    exact_mapping = {
        "좋다": "좋은", "많다": "많은", "적다": "적은", "크다": "큰", "작다": "작은",
        "높다": "높은", "낮다": "낮은", "깊다": "깊은", "얕다": "얕은", "좁다": "좁은",
        "넓다": "넓은", "멀다": "먼", "같다": "같은", "아름답다": "아름다운",
        "차다": "찬", "길다": "긴", "짧다": "짧은", "젊다": "젊은", "늙다": "늙은",
        "귀엽다": "귀여운", "둥글다": "둥근", "시다": "신", "쓰다": "쓴", "달다": "단", 
        "짜다": "짠", "맵다": "매운", "덥다": "더운", "춥다": "추운", "무겁다": "무거운",
        "가볍다": "가벼운", "무섭다": "무서운", "아프다": "아픈", "기쁘다": "기쁜", "슬프다": "슬픈",
        "빠르다": "빠른", "느리다": "느린", "다르다": "다른", "재미있다": "재미있는", "맛있다": "맛있는",
        "맛없다": "맛없는", "어렵다": "어려운", "쉽다": "쉬운"
    }

    for m in meanings:
        if m in exact_mapping:
            fixed_meanings.append(exact_mapping[m])
            continue
            
        original_m = m
        
        # 정규식을 이용한 일괄 어미 치환
        m = re.sub(r'하다$', '한', m)
        m = re.sub(r'이다$', '인', m)
        m = re.sub(r'스럽다$', '스러운', m)
        m = re.sub(r'롭다$', '로운', m)
        m = re.sub(r'([가-힣])ㅂ다$', r'\1운', m) # ㅂ불규칙 (예: 부드럽다 -> 부드러운)
        m = re.sub(r'쁘다$', '쁜', m)           
        m = re.sub(r'프다$', '픈', m)           
        m = re.sub(r'르다$', '른', m)           
        m = re.sub(r'기다$', '긴', m)           
        m = re.sub(r'있다$', '있는', m)         
        m = re.sub(r'없다$', '없는', m)         
        m = re.sub(r'([가-힣])답다$', r'\1다운', m)
        
        # 위 규칙에 걸리지 않은 일반적인 '다'로 끝나는 형용사의 경우 (단, '~보다' 등 예외 방지)
        if m == original_m and m.endswith('다') and not m.endswith('보다'):
            m = re.sub(r'다$', '은', m)
            
        fixed_meanings.append(m)
        
    return ", ".join(fixed_meanings)

def process_vocabulary():
    if not os.path.exists(INPUT_FILE):
        print(f"오류: '{INPUT_FILE}' 파일을 찾을 수 없습니다. 스크립트와 동일한 폴더에 위치시켜주세요.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # 데이터 계층 순회: data -> Level -> Chapter -> Vocabulary List
    base_data = json_data.get("data", {})
    
    modified_count = 0
    adj_fixed_count = 0

    for level, chapters in base_data.items():
        for chapter, vocab_list in chapters.items():
            for vocab in vocab_list:
                kanji = vocab.get("kanji", "")
                
                # 1. 수동 지정된 치명적 오역 및 문맥 오류 교정 적용
                if kanji in MANUAL_MEANING_FIXES:
                    fixes = MANUAL_MEANING_FIXES[kanji]
                    if "meaning" in fixes:
                        vocab["meaning"] = fixes["meaning"]
                    if "meaningKo" in fixes:
                        vocab["meaningKo"] = fixes["meaningKo"]
                    modified_count += 1
                
                # 2. 잘못 지정된 품사 교정 적용
                if kanji in MANUAL_POS_FIXES:
                    vocab["parts"] = MANUAL_POS_FIXES[kanji]
                    modified_count += 1

                # 3. 형용사 한글 뜻 끝맺음 자동 변환 (~다 -> ~한 등)
                if "adjective" in vocab.get("parts", "").lower():
                    original_ko = vocab.get("meaningKo", "")
                    fixed_ko = fix_adjective_korean(original_ko)
                    
                    if original_ko != fixed_ko:
                        vocab["meaningKo"] = fixed_ko
                        adj_fixed_count += 1

    # 변경된 JSON 데이터를 새 파일로 저장 (한글 깨짐 방지를 위해 ensure_ascii=False 설정)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print("="*50)
    print("🎉 단어장 자동 교정 작업이 성공적으로 완료되었습니다!")
    print(f"- 다의어/오역 및 품사 수동 교정 건수: {modified_count}건")
    print(f"- 형용사 어미(~다 -> ~한) 자동 변환 건수: {adj_fixed_count}건")
    print(f"- 결과 파일: '{OUTPUT_FILE}'가 생성되었습니다.")
    print("="*50)

if __name__ == "__main__":
    process_vocabulary()