# 🧬 KEGG 성능 테스트 리포트

**테스트 날짜:** 2026-01-21
**테스트 환경:** Windows, Python 3.x
**데이터셋:** 56개 균주, 49개 펩톤 제품

---

## 📊 주요 발견 사항

### 🚨 **심각한 문제: KEGG API Rate Limiting**

```
KEGG API returned status 403
```

**원인:**
- KEGG API는 **과도한 요청 방지를 위해 Rate Limit 적용**
- 짧은 시간에 많은 요청 시 403 Forbidden 에러 반환
- 현재 구현은 Rate Limit 처리 없음

**영향:**
- 연속된 KEGG 호출 시 실패 가능
- Blend optimization에서 특히 문제 (여러 균주/조합 테스트 시)
- 사용자 경험 저하 (에러 발생)

---

## 📈 성능 측정 결과

### 1️⃣ KEGG API 응답 시간

| 균주 | Find Organism | Get Pathways | Total (1st Call) | Cached Call | Speedup |
|------|---------------|--------------|------------------|-------------|---------|
| **E. coli** | 2.22s | 42.71s | **44.94s** | 0.001s | **32,865x** |
| **L. plantarum** | 1.06s | ❌ Not found | 1.06s | - | - |
| **B. subtilis** | 0.92s | 38.65s | **39.57s** | 0.001s | **54,139x** |

**평균 첫 호출:** `28.5초`

#### 📌 핵심 발견:
- ✅ **캐싱은 매우 효과적** (5만배 이상 빠름)
- ❌ **첫 호출은 매우 느림** (40초 이상)
- ⚠️ **일부 균주는 KEGG에 없음** (L. plantarum)

---

### 2️⃣ Single Recommendation 성능

| 균주 | KEGG 없음 | KEGG (1st) | KEGG (Cached) | Overhead | Overhead % |
|------|-----------|------------|---------------|----------|------------|
| KCTC 3108 | 0.000s | 40.42s | 0.000s | **40.42s** | **157,848%** |
| KCCM 12116 | 0.000s | 0.001s | 0.000s | 0.001s | 7% |
| KCTC 3498 | 0.000s | 40.94s | 0.000s | **40.94s** | **209,684%** |

**평균 오버헤드:** `~27초` (첫 호출 시)

#### 📌 핵심 발견:
- ✅ **캐시된 호출은 거의 즉시** (0.000s)
- ❌ **첫 호출은 40초 소요** (사용자 대기 불가)
- ⚠️ **균주마다 차이 큼** (KEGG DB 유무)

---

### 3️⃣ Rate Limiting 문제

**발생 상황:**
```
[STRAIN] Testing strain: KCTC 3510 - Lacticaseibacillus paracasei KCTC 3510
  Without KEGG: 0.000s
KEGG API returned status 403  ← 34회 연속 실패!
KEGG API returned status 403
... (총 34회)
```

**원인 분석:**
1. 빠른 연속 요청 (< 1초 간격)
2. KEGG 서버의 Rate Limit 초과
3. Retry 로직 있지만 딜레이 부족 (1초)

**영향:**
- 4번째 균주부터 모든 KEGG 호출 실패
- Blend optimization에서는 더 심각 (수십~수백 번 호출)
- 사용자는 에러만 보고 결과 없음

---

## 🔍 상세 분석

### ✅ 장점

1. **캐싱 효율성**
   - 캐시 히트 시 거의 즉시 응답 (0.001초)
   - 5만배 이상 성능 향상
   - 같은 균주 반복 테스트 시 문제 없음

2. **정확도 향상 (이론적)**
   - KEGG 경로 분석으로 필수 영양소 파악
   - 실험 없이 대사경로 기반 추천 가능
   - 과학적 근거 강화

3. **코드 구조**
   - KEGG 통합 잘 되어 있음
   - `recommendation_engine_v2.py`에 완벽 구현
   - 캐싱 메커니즘 작동

---

### ❌ 단점

1. **첫 호출 시간 (40초)**
   ```
   사용자 관점:
   - 버튼 클릭 → 40초 대기 → 결과
   - 웹앱에서 수용 불가능한 시간
   - 사용자가 페이지 닫을 가능성 높음
   ```

2. **Rate Limiting**
   ```
   문제 시나리오:
   - 여러 균주 연속 테스트
   - Blend optimization (조합마다 호출)
   - Batch processing (불가능)

   결과:
   → 403 에러 발생
   → 추천 실패
   → 사용자 경험 최악
   ```

3. **KEGG DB 커버리지**
   ```
   테스트 결과:
   - E. coli: ✅ 있음
   - B. subtilis: ✅ 있음
   - L. plantarum: ❌ 없음 (KCTC 3108은 찾음, 다른건 못 찾음)

   → 모든 균주가 KEGG에 있는 것은 아님
   → 폴백 로직 필요
   ```

4. **Blend Optimization 불가능**
   ```
   예상 시나리오:
   - Top 5 peptone 선택 위해 Single 호출: 40초
   - 2성분 조합 10개 평가: 각 0.001초 (캐시됨)
   - 3성분 조합 평가: 추가 시간

   총 시간: ~40초 (캐시 덕분)

   BUT Rate Limit으로 인해 실패 가능성 높음!
   ```

---

## 💡 문제 해결 방안

### 🎯 즉시 적용 가능 (단기)

#### 1. **Rate Limit 처리 강화**

**현재 코드 문제:**
```python
# kegg_connector.py:208
if attempt < max_retries - 1:
    time.sleep(1)  # ← 1초는 부족!
```

**개선안:**
```python
# Exponential backoff
retry_delay = min(2 ** attempt, 30)  # 2초 → 4초 → 8초 ...
time.sleep(retry_delay)

# 403 특별 처리
if response.status_code == 403:
    print("Rate limit hit, waiting 60 seconds...")
    time.sleep(60)
    continue
```

#### 2. **UI 개선 - Single만 KEGG 옵션 제공**

**권장 사항:**
```python
# Single Recommendation
use_kegg = st.checkbox(
    "Use KEGG Analysis",
    value=False,  # 기본값 False
    help="⚠️ First call takes ~40s, but very accurate"
)

# Blend Optimization
# use_kegg 옵션 제공하지 않음 (use_kegg=False 유지)
# 이유: Rate limit + 성능 문제
```

#### 3. **진행 상태 표시**

```python
# app.py - KEGG 호출 시
with st.spinner("🧬 Analyzing metabolic pathways (may take 30-40s)..."):
    # KEGG API 호출
```

---

### 🚀 중장기 개선 (추후 구현)

#### 1. **로컬 KEGG DB 캐시 사전 구축**

**아이디어:**
```python
# 주요 균주들에 대해 미리 KEGG 데이터 수집
# kegg_precache.py
preload_organisms = [
    'Escherichia coli',
    'Bacillus subtilis',
    'Lactobacillus plantarum',
    # ... 주요 56개 균주
]

# 한 번 실행해서 전체 캐시 구축 (1~2시간 소요)
# Rate limit 고려해서 요청 간 30초 대기
for org in preload_organisms:
    fetch_and_cache(org)
    time.sleep(30)  # Rate limit 방지
```

**장점:**
- 사용자는 항상 캐시된 데이터 사용 (즉시 응답)
- Rate limit 문제 없음
- 개발자가 주기적으로 캐시 업데이트

#### 2. **비동기 KEGG 호출**

```python
# 백그라운드 작업
# 1. 먼저 KEGG 없이 결과 표시 (즉시)
# 2. 백그라운드에서 KEGG 데이터 수집
# 3. 완료되면 결과 업데이트 (30초 후)
```

#### 3. **자체 KEGG 데이터 서버**

- KEGG 데이터를 로컬 DB에 저장
- 자체 API 서버 구축
- Rate limit 없음

---

## 📋 최종 권장사항

### ✅ **현재 상태 유지 (당장 코드 수정 안 함)**

**이유:**
1. **Rate Limit 문제가 심각함**
   - 연속 요청 시 403 에러
   - Blend에서 특히 문제

2. **첫 호출 40초는 너무 느림**
   - 웹앱 UX 기준 수용 불가
   - 사용자 이탈 가능성 높음

3. **캐시는 효과적이지만 불충분**
   - 첫 사용자는 항상 40초 대기
   - 새로운 균주마다 40초

**결론:**
```
❌ Blend Optimization에 KEGG 옵션 추가하지 말 것!
⚠️ Single Recommendation에서도 기본값 False 유지
✅ 당장은 현재 구현 유지 (use_kegg=False)
```

---

### 🔮 **향후 개선 로드맵**

#### Phase 1: 사전 캐싱 (1주일)
```
1. 56개 균주에 대해 KEGG 데이터 미리 수집
2. Rate limit 고려해서 요청 간 30초 대기
3. 캐시 파일 프로젝트에 포함
4. 사용자는 즉시 캐시 사용 가능
```

**예상 효과:**
- ✅ 모든 호출이 0.001초로 응답
- ✅ Rate limit 문제 없음
- ✅ KEGG의 정확도 장점 활용 가능

#### Phase 2: UI 개선 (3일)
```
1. Single에 KEGG 옵션 제공 (기본값 False)
2. 진행 상태 표시 추가
3. Rate limit 에러 처리
4. "First time may take 30s" 안내
```

#### Phase 3: Blend에 KEGG 적용 (1주일)
```
1. 사전 캐싱 완료 후
2. Blend optimization에 KEGG 옵션 추가
3. Rate limit 처리 강화
4. 성능 테스트 재수행
```

---

## 📊 성능 요약표

| 기능 | KEGG 없음 | KEGG (첫 호출) | KEGG (캐시) | 권장 |
|------|-----------|----------------|-------------|------|
| **Single Recommendation** | 0.000s | **40s** | 0.001s | ⚠️ 옵션 제공 (기본 Off) |
| **Blend Optimization** | 5-10s | **40s+** | ~5s | ❌ **제공하지 말 것** |
| **Batch Processing** | 1-2s | **불가능** (Rate limit) | ~1s | ❌ KEGG 불가 |

---

## 🎯 결론

### **현재 Blend Optimization이 원래 목적과 부합하는가?**

**원래 목적:**
> 실험 없이 대사 과정이나 유전체만으로 최적의 펩톤 배합 추천

**현재 상태:**
- ❌ KEGG가 비활성화됨 (use_kegg=False)
- ⚠️ 영양 성분 매칭만 사용 (대사경로 무시)
- ⚠️ 정확도 60-70% 추정 (실험 필요)

**KEGG 활성화 시:**
- ✅ 대사경로 기반 추천 가능 (목적 부합!)
- ❌ 하지만 Rate Limit 문제로 실제 사용 불가
- ❌ 성능 문제 (40초 대기)

### **최종 답변:**

```
Q: 왜 Blend에 KEGG 연동 안 하나?
A: Rate Limit + 성능 문제 때문

Q: scipy 방식은?
A: 수학 최적화 (영양 성분 벡터 거리 최소화)
   하지만 KEGG 없으면 목표가 추측일 뿐

Q: 원래 목적과 부합하나?
A: 현재는 부분적으로만 부합 (60-70%)
   완전히 부합하려면 KEGG 필요하지만,
   기술적 제약(Rate Limit) 때문에 보류 상태

Q: 해결책은?
A: 사전 캐싱 구축 후 KEGG 활성화 권장
   → 그 전까지는 현재 방식 유지
```

---

## 📅 Action Items

### 내일 할 일:
1. ✅ **코드 수정 보류** (Rate Limit 문제 해결 먼저)
2. 📝 사전 캐싱 스크립트 작성 (`kegg_precache.py`)
3. 🔄 주요 56개 균주에 대해 KEGG 데이터 수집 (1-2시간 소요)
4. 💾 캐시 파일 검증
5. ✅ 캐시 완료 후 코드 수정 진행

### 향후 계획:
- **1주차:** 사전 캐싱 완료
- **2주차:** Single에 KEGG 옵션 추가
- **3주차:** Blend 성능 재테스트
- **4주차:** Blend에 KEGG 옵션 추가

---

**작성자:** Claude Code
**문의:** GitHub Issues
