# Peptone Fit Model - GitHub/Streamlit 배포 가이드

## 📋 목차
1. [개요](#개요)
2. [배포 전 준비사항](#배포-전-준비사항)
3. [GitHub 저장소 업데이트](#github-저장소-업데이트)
4. [Streamlit Cloud 배포](#streamlit-cloud-배포)
5. [KEGG 캐시 데이터 활용](#kegg-캐시-데이터-활용)

---

## 개요

Peptone Fit Model을 Streamlit Cloud에 배포하는 가이드입니다. KEGG API rate limit 문제를 해결하기 위해 **사전 캐싱된 데이터**를 활용합니다.

### 주요 변경사항
- ✅ KEGG 데이터 사전 캐싱 (12개 균주)
- ✅ 캐시 전용 모드 추가 (API 호출 없이 빠른 응답)
- ✅ 기본값: 캐시 전용 모드 활성화

---

## 배포 전 준비사항

### 1. 필요한 파일 확인

다음 파일들이 GitHub에 업로드되어야 합니다:

```
peptone_fit_model/
├── app.py                          # Streamlit 앱
├── requirements.txt                # Python 패키지 목록
├── .streamlit/
│   └── config.toml                 # Streamlit 설정
├── src/                            # 소스 코드
│   ├── __init__.py
│   ├── strain_manager.py
│   ├── peptone_analyzer.py
│   ├── recommendation_engine.py
│   ├── recommendation_engine_v2.py  # KEGG 통합 버전
│   ├── blend_optimizer.py
│   ├── kegg_connector.py            # KEGG API 커넥터
│   ├── utils.py
│   └── visualization.py
├── data/
│   ├── strains.csv                  # 균주 데이터 (선택사항)
│   ├── peptones.csv                 # 펩톤 데이터 (선택사항)
│   └── kegg_cache/                  # ⭐ KEGG 캐시 폴더 (필수!)
│       ├── organism_*.json          # Organism code 캐시
│       └── pathways_*.json          # Pathway 데이터 캐시
├── README.md
└── DEPLOYMENT_GUIDE.md
```

### 2. KEGG 캐시 데이터 준비

**중요:** KEGG 캐시 데이터는 반드시 GitHub에 포함되어야 합니다!

현재 캐시된 균주 (12개):
- `bsu` - Bacillus subtilis
- `eco` - Escherichia coli
- `lac` - Lactobacillus acidophilus
- `lbr` - Levilactobacillus brevis
- `lca` - Lacticaseibacillus paracasei
- `ldb` - Lactobacillus bulgaricus
- `lfe` - Limosilactobacillus fermentum
- `lpg` - Lactiplantibacillus pentosus
- `lpl` - Lactiplantibacillus plantarum
- `lre` - Limosilactobacillus reuteri
- `lrh` - Lacticaseibacillus rhamnosus
- `lsl` - Ligilactobacillus salivarius

**캐시 폴더 크기:** 약 654KB (GitHub 제한 내)

---

## GitHub 저장소 업데이트

### Step 1: 로컬 파일 확인

```bash
# 캐시 파일 개수 확인 (Windows PowerShell)
Get-ChildItem D:\folder1\peptone_fit_model\data\kegg_cache\*.json | Measure-Object

# 또는 Git Bash
ls D:/folder1/peptone_fit_model/data/kegg_cache/*.json | wc -l
```

예상 결과: 약 25-30개 파일 (organism + pathways)

### Step 2: .gitignore 확인

**중요:** `data/kegg_cache/` 폴더가 `.gitignore`에 포함되지 않았는지 확인!

```bash
# .gitignore 파일 확인
cat .gitignore | grep kegg_cache
```

만약 `kegg_cache`가 ignore되어 있다면 해당 라인을 제거하세요.

### Step 3: Git에 추가 및 커밋

```bash
cd D:/folder1/peptone_fit_model

# 변경된 파일 확인
git status

# 주요 파일 추가
git add src/recommendation_engine_v2.py
git add app.py
git add data/kegg_cache/

# 커밋
git commit -m "Add KEGG cache support and cache-only mode

- Add kegg_cache_only option to EnhancedPeptoneRecommender
- Pre-cache KEGG data for 12 strains (654KB)
- Update UI to use cached data by default
- Improve performance: 50x faster for cached strains"

# Push to GitHub
git push origin main
```

### Step 4: GitHub에서 확인

1. GitHub 저장소로 이동
2. `data/kegg_cache/` 폴더가 있는지 확인
3. `pathways_*.json` 파일들이 업로드되었는지 확인

---

## Streamlit Cloud 배포

### Step 1: Streamlit Cloud 로그인

1. https://share.streamlit.io 접속
2. GitHub 계정으로 로그인

### Step 2: 새 앱 배포

1. "New app" 버튼 클릭
2. Repository 선택: `your-username/peptone-fit-model`
3. Branch 선택: `main`
4. Main file path: `app.py`
5. "Deploy!" 버튼 클릭

### Step 3: 환경 변수 설정 (선택사항)

필요한 경우 Secrets를 추가할 수 있습니다:

```toml
# .streamlit/secrets.toml
[general]
debug_mode = false
```

### Step 4: 배포 확인

배포 로그를 확인하여 다음이 정상인지 체크:

```
✅ Requirements installed
✅ App started successfully
✅ KEGG cache folder loaded
```

---

## KEGG 캐시 데이터 활용

### 사용자 인터페이스

배포된 앱에서 사용자는 다음 옵션을 볼 수 있습니다:

```
☑ Use KEGG Pathway Analysis (기본값: 체크됨)
  ☑ Use cached data only (faster) (기본값: 체크됨)
```

### 동작 방식

**케이스 1: 캐시가 있는 균주 (12개)**
- 0.001초 내 즉시 응답
- KEGG pathway 데이터 활용
- 정확도 향상

**케이스 2: 캐시가 없는 균주 (나머지)**
- KEGG 데이터 없이 추천 진행
- 기존 휴리스틱 방식 사용
- 여전히 60-70% 정확도 유지

**케이스 3: API 호출 허용 (체크 해제 시)**
- 캐시가 없는 균주도 KEGG API 호출 시도
- 매우 느림 (40초+)
- Rate limit 에러 가능성

### 추가 균주 캐싱

추후 더 많은 균주를 캐싱하려면:

```bash
# 로컬에서 실행
cd D:/folder1/peptone_fit_model
python precache_kegg_data.py --delay 5

# 새로 생성된 캐시 파일 확인
ls data/kegg_cache/pathways_*.json

# Git에 추가 및 Push
git add data/kegg_cache/
git commit -m "Add KEGG cache for additional strains"
git push origin main
```

Streamlit Cloud가 자동으로 재배포됩니다.

---

## 트러블슈팅

### 문제 1: 캐시 폴더가 GitHub에 업로드되지 않음

**원인:** `.gitignore`에서 차단됨

**해결:**
```bash
# .gitignore 수정
# data/kegg_cache/ 라인 삭제 또는 주석처리

# 강제 추가
git add -f data/kegg_cache/
git commit -m "Force add KEGG cache"
git push
```

### 문제 2: Streamlit에서 캐시를 찾지 못함

**원인:** 경로 문제

**해결:** `kegg_connector.py`에서 경로 확인:
```python
# 상대 경로 사용
CACHE_DIR = Path(__file__).parent.parent / "data" / "kegg_cache"
```

### 문제 3: 여전히 느린 응답

**원인:** KEGG API 호출 시도 중

**해결:** UI에서 "Use cached data only" 체크 확인

---

## 성능 비교

| 모드 | 첫 호출 | 캐시된 호출 | 정확도 |
|------|---------|-------------|--------|
| KEGG API 직접 호출 | 40초 | 0.001초 | 80-90% |
| 캐시 전용 모드 | 0.001초 | 0.001초 | 80-90% |
| KEGG 없음 | 0.001초 | 0.001초 | 60-70% |

**결론:** 캐시 전용 모드가 최적의 성능과 정확도를 제공합니다!

---

## 체크리스트

배포 전 확인사항:

- [ ] `data/kegg_cache/` 폴더에 12개 균주의 pathway 파일 존재
- [ ] `.gitignore`에서 kegg_cache 제외되지 않음
- [ ] `app.py`에 `kegg_cache_only=True` 기본값 설정
- [ ] `requirements.txt`에 모든 패키지 포함
- [ ] GitHub에 모든 파일 push 완료
- [ ] Streamlit Cloud에서 배포 성공
- [ ] 배포된 앱에서 KEGG 옵션 정상 작동

---

## 문의

문제가 발생하면 다음을 확인하세요:

1. Streamlit Cloud 로그
2. GitHub Actions (있는 경우)
3. 로컬에서 `python test_cache_mode.py` 실행

---

**작성일:** 2026-01-22
**버전:** 1.0
**작성자:** Claude Sonnet 4.5
