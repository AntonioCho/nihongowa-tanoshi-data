# generate_vocab.py 실행 가이드

## 필요 파일 (같은 폴더에 두기)
- generate_vocab.py   ← 메인 스크립트
- VOCAB_PROMPT.md     ← API 프롬프트
- N5_words.txt        ← N5 단어 목록

## 환경 설정

### 1. Python 패키지 설치
```bash
pip install anthropic
```

### 2. API 키 설정
```bash
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."

# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-...
```

## 실행

```bash
python generate_vocab.py
```

## 동작 방식

1. N5_words.txt를 Day 단위(10개)로 파싱
2. 각 Day마다 Claude API 호출 → 영문 뜻, furigana, 예문 생성
3. 중간 결과를 **n5_progress.json**에 저장 (resume 지원)
4. 완료 후 **vocabData_N5.json** 생성

## Resume (중단 후 재실행)

중간에 끊겨도 그냥 다시 실행하면 됩니다.
완료된 Day는 자동으로 스킵합니다.

```
Day  1: 완료 (10개)
Day  2: 완료 (10개)
Day  3: 처리 중...  ← 여기서 끊겼다면
...
# 재실행 시
Day  1: 스킵 (완료)
Day  2: 스킵 (완료)
Day  3: 처리 중...  ← 이어서 시작
```

## 처음부터 다시 하려면

```bash
rm n5_progress.json
python generate_vocab.py
```

## 출력 파일

- **n5_progress.json**: 중간 저장 (Day별 결과)
- **vocabData_N5.json**: 최종 결과 (sample.json 형식)

## 예상 소요 시간

- N5: 75 Day × ~2초 = 약 2~3분

## API 비용 참고

- N5 750단어 기준 약 0.10~0.15 USD (Sonnet 4.6 기준)
