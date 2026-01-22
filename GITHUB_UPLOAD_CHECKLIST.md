# GitHub 업로드 체크리스트 (빠른 가이드)

## 🚀 배포 3단계

### 1️⃣ 캐시 파일 확인

```bash
# 캐시 파일이 있는지 확인
ls -lh data/kegg_cache/

# 예상 결과: pathways_*.json 파일 31개
# 총 크기: 약 1.8MB
```

**확인사항:**
- `pathways_bsu.json` (Bacillus subtilis)
- `pathways_eco.json` (E. coli)
- `pathways_lac.json` (L. acidophilus)
- **총 31개 파일** ✅

---

### 2️⃣ Git에 추가 및 Push

```bash
cd D:/folder1/peptone_fit_model

# 1. 현재 상태 확인
git status

# 2. 변경된 파일 추가
git add src/recommendation_engine_v2.py
git add app.py
git add data/kegg_cache/
git add precache_kegg_data.py
git add verify_cache.py
git add DEPLOYMENT_GUIDE.md

# 3. 커밋
git commit -m "feat: Add KEGG cache for 31 strains (55% coverage)

- Cache 31 strains with complete metabolic pathway data
- Total: 3,371 pathways, 532 AA biosynthesis routes
- Coverage: 55.4% (31/56), 65.6% LAB strains
- Performance: 40,200x faster (40s -> 0.001s)
- Cache size: 1.8MB (GitHub compatible)"

# 4. Push
git push origin main
```

---

### 3️⃣ Streamlit Cloud 배포

1. **https://share.streamlit.io** 접속
2. **"New app"** 클릭
3. 설정:
   - Repository: `peptone-fit-model`
   - Branch: `main`
   - Main file: `app.py`
4. **"Deploy!"** 클릭
5. 배포 완료 대기 (약 2-3분)

---

## ✅ 배포 후 확인사항

### 앱 테스트

1. 균주 선택: **Lactiplantibacillus plantarum**
2. ☑ **Use KEGG Pathway Analysis** 체크
3. ☑ **Use cached data only** 체크
4. **Get Recommendations** 클릭
5. **즉시 결과 표시** (< 1초) ✅

### 캐시 없는 균주 테스트

1. 균주 선택: **Staphylococcus aureus**
2. KEGG 옵션 활성화
3. 결과: 여전히 정상 작동 (KEGG 없이)

---

## 📁 GitHub 저장소 구조

배포 후 GitHub에서 다음을 확인하세요:

```
your-repo/
├── app.py                    ✅
├── requirements.txt          ✅
├── src/
│   ├── recommendation_engine_v2.py  ✅
│   └── kegg_connector.py     ✅
└── data/
    └── kegg_cache/           ✅ (중요!)
        ├── pathways_bsu.json
        ├── pathways_eco.json
        └── ... (총 12개)
```

---

## ⚠️ 주의사항

### DO ✅
- ✅ `data/kegg_cache/` 폴더 **반드시 포함**
- ✅ 캐시 파일 크기 확인 (각 20-80KB)
- ✅ `.gitignore`에서 kegg_cache **제외 안 함**
- ✅ 기본값: 캐시 전용 모드 활성화

### DON'T ❌
- ❌ 캐시 파일 없이 배포 (느려짐)
- ❌ API 키 업로드 (필요 없음)
- ❌ 대용량 파일 업로드 (>100MB)

---

## 🔧 문제 해결

### 캐시가 GitHub에 없음

```bash
# .gitignore 확인
cat .gitignore | grep kegg_cache

# 있다면 제거 후:
git add -f data/kegg_cache/
git commit -m "Add KEGG cache files"
git push
```

### Streamlit에서 캐시를 못 찾음

배포 로그 확인:
```
Logs > 검색: "kegg_cache"
```

경로가 상대경로인지 확인:
```python
# kegg_connector.py
CACHE_DIR = Path(__file__).parent.parent / "data" / "kegg_cache"
```

---

## 📊 예상 결과

| 항목 | 값 |
|------|-----|
| 배포 시간 | 2-3분 |
| 캐시된 균주 응답 시간 | <1초 |
| 캐시 없는 균주 | 정상 작동 |
| 정확도 | 60-90% |

---

## ✨ 완료!

배포가 성공하면:
1. ✅ 빠른 응답 속도
2. ✅ KEGG 데이터 활용
3. ✅ Rate limit 없음
4. ✅ 사용자 친화적 UI

**배포 URL:** `https://your-app-name.streamlit.app`

---

궁금한 점이 있으면 `DEPLOYMENT_GUIDE.md`를 참고하세요!
