# Peptone Fit Model v2.0

균주 기반 펩톤 추천 도구 (Strain-Based Peptone Recommendation Tool)

## 개요

미생물 균주의 대사 특성 및 유전체 정보를 기반으로 최적의 펩톤(및 최대 3종 배합)을 자동 추천하는 Python 도구입니다.

## 주요 기능

### Phase 1: 기본 추천 시스템 ✓
- 56종 미생물 균주 데이터 관리
- 49종 펩톤 성분 분석 (94개 영양 지표)
- 다중 요소 적합도 점수 계산
- 균주별 최적 펩톤 추천 (단일 및 배합)

### Phase 2: 외부 DB 연동 ✓
- KEGG REST API 연동 (24개 대사 경로 분석)
- NCBI Taxonomy 조회
- 경로 기반 영양 요구량 자동 추론
- 로컬 캐싱 시스템 (30일)

### Phase 3: 고급 최적화 ✓
- scipy 기반 과학적 배합비 최적화
- SLSQP 및 Differential Evolution 알고리즘
- 보완성 기반 펩톤 선택
- Interactive 시각화 (plotly)
- HTML 리포트 자동 생성

### Phase 4: Web UI ✓
- Streamlit 기반 웹 애플리케이션
- 6개 주요 페이지 (Home, Single, Blend, Batch, Advanced, About)
- Real-time interactive 차트
- Batch 처리 인터페이스
- CSV/HTML 내보내기

## 빠른 시작

### Web UI 실행 (권장)

```bash
# Streamlit 앱 실행
streamlit run app.py

# 브라우저에서 자동으로 열림: http://localhost:8501
```

**주요 페이지:**
- 🏠 **Home**: 시스템 개요 및 현황
- 🔍 **Single Recommendation**: 개별 균주 추천
- ⚗️ **Blend Optimization**: 최적화된 블렌드
- 📊 **Batch Processing**: 여러 균주 일괄 처리
- 📈 **Advanced Analysis**: 데이터 탐색 및 분석
- ℹ️ **About**: 시스템 정보

### 설치

```bash
# 기본 설치
pip install -r requirements.txt

# NCBI 사용 시 (선택)
pip install biopython
```

### 기본 사용

```python
from src.strain_manager import StrainDatabase
from src.peptone_analyzer import PeptoneDatabase
from src.recommendation_engine_v2 import EnhancedPeptoneRecommender

# 데이터베이스 로드
strain_db = StrainDatabase()
peptone_db = PeptoneDatabase()
strain_db.load_from_excel("균주리스트.xlsx")
peptone_db.load_from_excel("펩톤성분.xlsx")

# Enhanced recommender (최적화 + KEGG 통합)
recommender = EnhancedPeptoneRecommender(strain_db, peptone_db)

# 최적화된 블렌드 추천
recs = recommender.recommend_optimized_blend(
    "KCCM 12116",
    max_components=3,
    use_optimizer=True
)

# 결과 출력
for rec in recs[:3]:
    print(f"{rec.get_description()}: {rec.overall_score:.3f}")
```

### CLI 사용

```bash
# 기본 추천
python peptone_fit.py recommend "KCCM 12116"

# Sempio 제품만
python peptone_fit.py recommend "KCCM 12116" --sempio-only

# 결과 저장
python peptone_fit.py recommend "KCCM 12116" -o results.csv
```

## 프로젝트 구조

```
peptone_fit_model/
├── data/                    # 데이터 파일
│   ├── strains.csv         # 균주 리스트
│   └── peptone_composition.csv  # 펩톤 성분 데이터
├── src/                     # 소스 코드
│   ├── strain_manager.py   # 균주 데이터 관리
│   ├── peptone_analyzer.py # 펩톤 성분 분석
│   ├── kegg_connector.py   # KEGG API 연동
│   ├── recommendation_engine.py  # 추천 알고리즘
│   ├── blend_optimizer.py  # 배합 최적화
│   └── utils.py            # 유틸리티 함수
├── notebooks/               # 데이터 탐색용 노트북
├── tests/                   # 테스트 코드
├── output/                  # 결과 출력 폴더
└── app.py                   # Streamlit UI

```

## 데이터 현황

### 보유 균주 (54종)
- 유산균 (LAB): 34종
- Bacillus: 5종
- E. coli: 5종
- 효모: 2종
- 방선균: 1종
- 기타: 7종

### 펩톤 제품
- Sempio 제품: 15종 (SOY-1, SOY-N+, SOY-L, WHEAT-1, PEA-1, RICE-1 등)
- 타사 제품: 34종

## 알고리즘

### 적합도 점수 계산
- 영양요구성 매칭 (40%)
- 아미노산 프로파일 매칭 (25%)
- 성장인자 충족도 (20%)
- 분자량 분포 적합성 (15%)

### 배합 최적화
- scipy.optimize를 이용한 비율 최적화
- 제약조건: 각 펩톤 10-80%, 최대 3종

## 개발 현황

- [x] **Phase 1**: 데이터 인프라 구축 ✅
- [x] **Phase 2**: 외부 DB 연동 ✅
- [x] **Phase 3**: 고급 추천 및 최적화 ✅
- [x] **Phase 4**: Streamlit Web UI ✅

**🎉 전체 프로젝트 완료!**

## 성능 지표

- **추천 속도**: 단일 < 0.1초, 블렌드 < 5초
- **최적화**: 2-3 펩톤 블렌드 < 0.5초
- **KEGG API**: 첫 조회 2-5초, 캐시 < 0.01초
- **메모리**: 전체 ~50MB

## 문서

### 사용자 가이드
- `RUN_APP.md`: 🌟 Web UI 실행 가이드
- `USAGE_V2.md`: Python API 상세 사용법

### 개발 보고서
- `PHASE1_COMPLETE.md`: Phase 1 (데이터 인프라)
- `PHASE2_3_COMPLETE.md`: Phase 2&3 (DB 연동 & 최적화)
- `PHASE4_COMPLETE.md`: Phase 4 (Web UI)
- `FINAL_SUMMARY.md`: 전체 프로젝트 요약

## 스크린샷

(Web UI 실행 후 각 페이지 캡처)

## FAQ

**Q: 어떤 방식으로 사용하는 것이 좋나요?**
A: 빠른 분석에는 **Web UI** (streamlit run app.py) 추천. 자동화/통합에는 **Python API** 사용.

**Q: KEGG 연동이 안 되는데요?**
A: 인터넷 연결을 확인하고, 첫 조회는 2-5초 소요. 캐시 이후엔 즉시 로드.

**Q: 배치 처리는 몇 개까지 가능한가요?**
A: Web UI는 10개, Python API는 제한 없음 (메모리 고려).

**Q: 결과를 어떻게 저장하나요?**
A: Web UI의 Download 버튼 또는 Python에서 `to_csv()` 사용.

## 라이선스

Internal use only - Sempio
