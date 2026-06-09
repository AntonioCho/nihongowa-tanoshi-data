# vocabData.json 배포 가이드

## 개요

앱의 단어 데이터는 jsDelivr CDN을 통해 배포됩니다. 앱 업데이트 없이 단어 데이터를 수정할 수 있습니다.

- **저장소**: https://github.com/AntonioCho/nihongowa-tanoshi-data
- **CDN URL**: https://cdn.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@main/vocabData.json

---

## 배포 단계

### 1. 데이터 수정

vocabData.json 파일을 수정합니다. 파일 구조:

```json
{
  "version": "1.0.1",
  "updatedAt": "2026-02-08T12:00:00Z",
  "data": {
    "N5": {
      "1": [
        {
          "id": "n5_1_1",
          "word": "私",
          "reading": "わたし",
          "meaning": "I, me",
          "parts": "noun"
        }
      ]
    }
  }
}
```

**중요**:
- `version` 필드를 업데이트하세요 (예: 1.0.0 → 1.0.1)
- `updatedAt` 필드를 현재 시간으로 업데이트하세요

### 2. GitHub에 푸시

```bash
# 저장소 클론 (처음인 경우)
git clone https://github.com/AntonioCho/nihongowa-tanoshi-data.git
cd nihongowa-tanoshi-data

# 또는 기존 저장소 업데이트
cd nihongowa-tanoshi-data
git pull origin main

# 파일 수정 후 커밋
git add vocabData.json
git commit -m "Update vocab data to v1.0.1"
git push origin main
```

### 3. CDN 캐시 갱신

jsDelivr는 기본적으로 파일을 캐시합니다. 즉시 갱신하려면:

#### 방법 A: 캐시 퍼지 API 사용 (권장)

```bash
curl "https://purge.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@main/vocabData.json"
```

#### 방법 B: 버전 태그 사용

특정 버전을 고정하려면 Git 태그를 사용:

```bash
# 태그 생성
git tag v1.0.1
git push origin v1.0.1

# CDN URL에서 태그 사용
# https://cdn.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@v1.0.1/vocabData.json
```

### 4. 배포 확인

브라우저 또는 curl로 확인:

```bash
curl -I "https://cdn.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@main/vocabData.json"
```

버전 확인:

```bash
curl -s "https://cdn.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@main/vocabData.json" | head -c 100
```

---

## 앱에서의 동작

### 데이터 로딩 순서

1. **앱 시작 시**: CDN에서 최신 데이터 확인 (24시간마다)
2. **CDN 성공**: 데이터 캐시 후 사용
3. **CDN 실패**: 로컬 캐시 사용
4. **캐시 없음**: 번들된 데이터 사용

### 강제 새로고침

앱 내 설정에서 "데이터 새로고침" 버튼을 누르면 즉시 CDN에서 최신 데이터를 가져옵니다.

---

## 문제 해결

### CDN에서 이전 버전이 표시되는 경우

1. 캐시 퍼지 실행:
   ```bash
   curl "https://purge.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@main/vocabData.json"
   ```

2. 5-10분 후 다시 확인

### 앱에서 업데이트가 반영되지 않는 경우

1. 앱 설정에서 "데이터 새로고침" 실행
2. 앱 완전 종료 후 재시작
3. 앱 데이터 삭제 후 재설치 (최후의 수단)

### JSON 형식 오류

업로드 전 JSON 유효성 검사:

```bash
# jq 사용
cat vocabData.json | jq . > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Node.js 사용
node -e "require('./vocabData.json'); console.log('Valid JSON')"
```

---

## 주의사항

1. **저장소는 Public 유지**: jsDelivr는 public 저장소만 지원
2. **파일 크기**: 현재 약 1MB, 과도하게 커지지 않도록 관리
3. **하위 호환성**: 기존 필드 삭제 시 앱 충돌 가능
4. **버전 관리**: 항상 version 필드 업데이트

---

## 빠른 참조

| 작업 | 명령어 |
|------|--------|
| 저장소 클론 | `git clone https://github.com/AntonioCho/nihongowa-tanoshi-data.git` |
| 변경사항 푸시 | `git add . && git commit -m "message" && git push` |
| 캐시 퍼지 | `curl "https://purge.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@main/vocabData.json"` |
| CDN 확인 | `curl -s "https://cdn.jsdelivr.net/gh/AntonioCho/nihongowa-tanoshi-data@main/vocabData.json" \| head -c 100` |
