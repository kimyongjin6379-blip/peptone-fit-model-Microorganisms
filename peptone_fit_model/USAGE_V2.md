# Peptone Fit Model v2.0 - 사용 가이드

## 새로운 기능 (Phase 2 & 3)

### Phase 2: 외부 DB 연동
- ✓ KEGG 대사 경로 분석
- ✓ NCBI Taxonomy 조회
- ✓ 경로 기반 영양 요구량 추론

### Phase 3: 고급 추천 및 최적화
- ✓ scipy 기반 배합비 최적화
- ✓ 보완성 기반 펩톤 선택
- ✓ Interactive 시각화 (plotly)
- ✓ HTML 리포트 자동 생성

---

## 설치

### 기본 설치
```bash
pip install -r requirements.txt
```

### 선택적 설치 (NCBI 사용 시)
```bash
pip install biopython
```

---

## 사용법

### 1. 기본 추천 (Phase 1)

```python
from src.strain_manager import StrainDatabase
from src.peptone_analyzer import PeptoneDatabase
from src.recommendation_engine import PeptoneRecommender

# 데이터베이스 로드
strain_db = StrainDatabase()
peptone_db = PeptoneDatabase()

strain_db.load_from_excel("균주리스트.xlsx")
peptone_db.load_from_excel("펩톤성분.xlsx")

# 기본 추천
recommender = PeptoneRecommender(strain_db, peptone_db)
recs = recommender.recommend_single("KCCM 12116", top_n=5)

# 결과 출력
for i, rec in enumerate(recs, 1):
    print(f"{i}. {rec.get_description()}: {rec.overall_score:.3f}")
```

### 2. KEGG 경로 기반 추천 (Phase 2)

```python
from src.recommendation_engine_v2 import EnhancedPeptoneRecommender

# Enhanced recommender 생성 (KEGG 활성화)
recommender = EnhancedPeptoneRecommender(
    strain_db,
    peptone_db,
    use_kegg=True  # KEGG 연동
)

# 경로 분석 기반 추천
recs = recommender.recommend_with_pathways(
    "KCCM 12116",
    top_n=5,
    sempio_only=True
)

# 결과에 경로 정보 포함
for rec in recs:
    print(f"{rec.get_description()}")
    print(f"  Score: {rec.overall_score:.3f}")
    if 'pathway_match' in rec.detailed_scores:
        print(f"  Pathway match: {rec.detailed_scores['pathway_match']:.3f}")
    print(f"  {rec.rationale}")
```

### 3. 최적화된 블렌드 추천 (Phase 3)

```python
# 최적화 알고리즘 사용
recs = recommender.recommend_optimized_blend(
    "KCCM 12116",
    max_components=3,
    top_n=5,
    use_optimizer=True  # scipy 최적화 사용
)

# 최적 배합비 확인
for rec in recs[:3]:
    print(f"\n{rec.get_description()}")
    print(f"Score: {rec.overall_score:.3f}")
    print("Composition:")
    for pep, ratio in zip(rec.peptones, rec.ratios):
        print(f"  {pep.name:15} {ratio*100:6.2f}%")
```

### 4. 시각화

```python
from src.visualization import RecommendationVisualizer

visualizer = RecommendationVisualizer()

# 1) 점수 비교 차트
fig = visualizer.plot_score_comparison(recs, title="추천 결과")
fig.show()  # 브라우저에서 열기
# fig.write_html("scores.html")  # 파일로 저장

# 2) 상세 점수 레이더 차트
fig = visualizer.plot_detailed_scores(recs[0])
fig.show()

# 3) 아미노산 프로파일 히트맵
peptones = [rec.peptones[0] for rec in recs[:5]]
fig = visualizer.plot_amino_acid_profile(peptones, profile_type='free')
fig.show()

# 4) 종합 HTML 리포트
strain = strain_db.get_strain_by_id("KCCM 12116")
visualizer.create_recommendation_report(
    strain, recs,
    output_file="report.html"
)
print("리포트가 생성되었습니다: report.html")
```

### 5. 커스텀 블렌드 최적화

```python
from src.blend_optimizer import BlendOptimizer

# 최적화기 생성
optimizer = BlendOptimizer(
    min_ratio=0.1,  # 최소 10%
    max_ratio=0.8   # 최대 80%
)

# 펩톤 선택
peptones = [
    peptone_db.get_peptone_by_name("SOY-N+"),
    peptone_db.get_peptone_by_name("PEA-1"),
    peptone_db.get_peptone_by_name("WHEAT-1")
]

# 목표 프로파일 정의
target_profile = {
    'TN': 0.8,              # Total nitrogen 80%
    'AN': 0.7,              # Amino nitrogen 70%
    'essential_aa': 0.65,   # Essential AA ratio
    'free_aa': 0.55,        # Free AA ratio
    'nucleotide': 0.4,      # Nucleotide content
    'vitamin': 0.3          # Vitamin content
}

# 가중치 설정 (중요도)
weights = {
    'TN': 1.0,
    'AN': 1.5,              # AN 더 중요
    'essential_aa': 1.2,
    'free_aa': 1.0,
    'nucleotide': 0.8,
    'vitamin': 0.6
}

# 최적화 실행
result = optimizer.optimize_ratio(
    peptones,
    target_profile,
    weights=weights,
    method='SLSQP'  # or 'differential_evolution'
)

# 결과 확인
if result.success:
    print(f"✓ 최적화 성공!")
    print(f"반복 횟수: {result.iterations}")
    print(f"최종 점수: {result.final_score:.6f}")
    print(f"\n최적 배합:")
    for pep, ratio in zip(result.peptones, result.optimal_ratios):
        print(f"  {pep.name:15} {ratio*100:6.2f}%")
else:
    print(f"✗ 최적화 실패: {result.message}")

# 배합 평가
metrics = optimizer.evaluate_blend(
    result.peptones,
    result.optimal_ratios,
    target_profile
)

print(f"\n배합 평가:")
for metric, value in metrics.items():
    print(f"  {metric:20} {value:.3f}")
```

### 6. 보완 펩톤 찾기

```python
# 기본 펩톤 선택
base_peptone = peptone_db.get_peptone_by_name("SOY-N+")

# 보완 펩톤 찾기
complementary = optimizer.find_complementary_peptones(
    base_peptone,
    peptone_db.get_sempio_peptones(),
    top_n=5
)

print(f"{base_peptone.name}를 보완하는 펩톤:")
for pep, score in complementary:
    print(f"  {pep.name:15} 보완성 점수: {score:.3f}")
    print(f"    원료: {pep.raw_material}")
```

### 7. KEGG 경로 직접 조회

```python
from src.kegg_connector import KEGGConnector

connector = KEGGConnector(use_cache=True)

# 균주 찾기
org_code = connector.find_organism('Lactobacillus', 'plantarum')
if org_code:
    print(f"KEGG code: {org_code}")

    # 경로 정보 조회
    pathways = connector.get_organism_pathways(org_code)

    if pathways:
        print(f"\n총 {len(pathways.pathways)}개 경로 발견")

        # 아미노산 생합성 경로 확인
        aa_pathways = ['map00260', 'map00270', 'map00290', 'map00300']
        print("\n아미노산 생합성 경로:")
        for pid in aa_pathways:
            if pathways.has_pathway(pid):
                info = pathways.pathways[pid]
                print(f"  ✓ {pid}: {info.name}")
            else:
                print(f"  ✗ {pid}: 없음")

        # 영양 요구량 추론
        requirements = connector.infer_nutritional_requirements(pathways)

        print("\n추론된 영양 요구량:")
        for nutrient, level in list(requirements.items())[:10]:
            print(f"  {nutrient:25} {level}")
```

### 8. NCBI Taxonomy 조회

```python
from src.ncbi_connector import NCBIConnector

# 이메일 설정 필요 (NCBI 정책)
connector = NCBIConnector(email="your_email@example.com")

# Taxonomy 정보 조회
tax_info = connector.get_taxonomy_by_name(
    'Lactobacillus',
    'plantarum',
    strain='KCCM 12116'
)

if tax_info:
    print(f"Taxonomy ID: {tax_info.tax_id}")
    print(f"Scientific Name: {tax_info.scientific_name}")
    print(f"Rank: {tax_info.rank}")
    print(f"Lineage: {' > '.join(tax_info.lineage[-5:])}")
```

---

## 고급 사용법

### Batch Processing

```python
# 여러 균주에 대해 일괄 처리
strain_ids = ["KCCM 12116", "KCTC 3108", "KCTC 3510"]

results_dict = {}

for strain_id in strain_ids:
    print(f"\n처리 중: {strain_id}")

    recs = recommender.recommend_optimized_blend(
        strain_id,
        max_components=3,
        top_n=3,
        use_optimizer=True
    )

    results_dict[strain_id] = recs

    # 각 균주별 리포트 생성
    strain = strain_db.get_strain_by_id(strain_id)
    visualizer.create_recommendation_report(
        strain, recs,
        output_file=f"report_{strain_id}.html"
    )

print("\n\n✓ 모든 균주 처리 완료!")
```

### CSV 내보내기

```python
import pandas as pd

# 결과를 DataFrame으로 변환
data = []
for strain_id, recs in results_dict.items():
    for rec in recs:
        data.append({
            'strain_id': strain_id,
            'description': rec.get_description(),
            'score': rec.overall_score,
            'peptones': ', '.join(p.name for p in rec.peptones),
            'ratios': ', '.join(f"{r:.2f}" for r in rec.ratios),
            'rationale': rec.rationale
        })

df = pd.DataFrame(data)
df.to_csv("batch_results.csv", index=False, encoding='utf-8-sig')
print("✓ 결과를 batch_results.csv로 저장했습니다")
```

### 민감도 분석

```python
# 배합비 변화에 따른 점수 변화 분석
strain = strain_db.get_strain_by_id("KCCM 12116")
peptones = [
    peptone_db.get_peptone_by_name("SOY-N+"),
    peptone_db.get_peptone_by_name("PEA-1")
]

# 다양한 배합비 테스트
ratios_list = []
scores = []

for ratio1 in np.linspace(0.1, 0.9, 17):  # 10% ~ 90%
    ratio2 = 1.0 - ratio1
    ratios = [ratio1, ratio2]

    score, _ = recommender._evaluate_blend(strain, peptones, ratios)

    ratios_list.append(ratio1)
    scores.append(score)

# 시각화
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=[r*100 for r in ratios_list],
    y=scores,
    mode='lines+markers',
    name='Fitness Score'
))

fig.update_layout(
    title=f"배합비 민감도 분석: {peptones[0].name} vs {peptones[1].name}",
    xaxis_title=f"{peptones[0].name} 비율 (%)",
    yaxis_title="Fitness Score"
)

fig.show()
```

---

## 설정 및 튜닝

### KEGG 캐시 관리

```python
# 캐시 위치
cache_dir = Path("data/kegg_cache")

# 캐시 삭제 (다시 조회하려면)
import shutil
if cache_dir.exists():
    shutil.rmtree(cache_dir)

# 캐시 없이 사용
connector = KEGGConnector(use_cache=False)
```

### 최적화 알고리즘 선택

```python
# SLSQP: 빠르지만 로컬 최적해
result_slsqp = optimizer.optimize_ratio(
    peptones, target, method='SLSQP'
)

# Differential Evolution: 느리지만 글로벌 최적해
result_de = optimizer.optimize_ratio(
    peptones, target, method='differential_evolution'
)

# 비교
print(f"SLSQP score: {result_slsqp.final_score:.6f}")
print(f"DE score: {result_de.final_score:.6f}")
```

### 점수 가중치 조정

```python
# recommendation_engine.py에서 수정
SCORING_WEIGHTS = {
    'nutritional_match': 0.50,      # 40% → 50% 증가
    'amino_acid_match': 0.25,
    'growth_factor_match': 0.15,    # 20% → 15% 감소
    'mw_distribution_match': 0.10   # 15% → 10% 감소
}
```

---

## 문제 해결

### KEGG API 오류

**증상**: "Connection timeout" 또는 "Failed to fetch"

**해결:**
```python
# 재시도 횟수 증가
connector = KEGGConnector()
connector._kegg_request(endpoint, max_retries=5)

# 또는 캐시 사용
connector = KEGGConnector(use_cache=True)
```

### Biopython 오류 (NCBI)

**증상**: "ImportError: No module named 'Bio'"

**해결:**
```bash
pip install biopython
```

### 최적화 실패

**증상**: `result.success = False`

**원인**: 제약조건을 만족하는 해가 없음

**해결:**
```python
# 제약조건 완화
optimizer = BlendOptimizer(
    min_ratio=0.05,  # 10% → 5%
    max_ratio=0.9    # 80% → 90%
)

# 또는 초기값 변경
result = optimizer.optimize_ratio(
    peptones, target,
    initial_ratios=[0.4, 0.3, 0.3]  # Custom initial guess
)
```

### 시각화 에러

**증상**: "Plotly not found"

**해결:**
```bash
pip install plotly kaleido  # kaleido는 static export용
```

---

## 성능 최적화 팁

1. **KEGG 캐시 사용**: `use_cache=True` (기본값)
2. **Batch 처리 시**: 멀티프로세싱 고려
3. **많은 조합 테스트 시**: SLSQP 사용 (DE보다 빠름)
4. **메모리 절약**: 필요한 펩톤만 로드

```python
# 메모리 효율적 로딩
peptone_db = PeptoneDatabase()
peptone_db.load_from_excel("peptones.xlsx")

# Sempio만 필터링
sempio_only = peptone_db.get_sempio_peptones()
```

---

## 예제 스크립트

### 완전한 워크플로우

```python
#!/usr/bin/env python
"""
완전한 펩톤 추천 워크플로우
"""

from pathlib import Path
from src.strain_manager import StrainDatabase
from src.peptone_analyzer import PeptoneDatabase
from src.recommendation_engine_v2 import EnhancedPeptoneRecommender
from src.visualization import RecommendationVisualizer

def main():
    # 1. 데이터 로드
    print("데이터 로딩 중...")
    strain_db = StrainDatabase()
    peptone_db = PeptoneDatabase()

    strain_db.load_from_excel("균주리스트.xlsx")
    peptone_db.load_from_excel("펩톤성분.xlsx")

    # 2. 추천 엔진 초기화
    print("추천 엔진 초기화...")
    recommender = EnhancedPeptoneRecommender(
        strain_db, peptone_db,
        use_kegg=False  # 빠른 테스트를 위해 비활성화
    )

    # 3. 추천 실행
    strain_id = "KCCM 12116"
    print(f"\n{strain_id} 균주에 대한 추천 생성 중...")

    recs = recommender.recommend_optimized_blend(
        strain_id,
        max_components=3,
        top_n=5,
        use_optimizer=True
    )

    # 4. 결과 출력
    print("\n" + "="*80)
    print("추천 결과")
    print("="*80)

    for i, rec in enumerate(recs, 1):
        print(f"\n{i}. {rec.get_description()}")
        print(f"   점수: {rec.overall_score:.3f}")
        print(f"   근거: {rec.rationale}")

    # 5. 시각화
    print("\n시각화 생성 중...")
    visualizer = RecommendationVisualizer()

    strain = strain_db.get_strain_by_id(strain_id)
    visualizer.create_recommendation_report(
        strain, recs,
        output_file="final_report.html"
    )

    print("\n✓ 완료! final_report.html을 확인하세요.")

if __name__ == "__main__":
    main()
```

---

## 추가 리소스

- README.md: 프로젝트 개요
- PHASE1_COMPLETE.md: Phase 1 완료 보고서
- PHASE2_3_COMPLETE.md: Phase 2 & 3 완료 보고서
- requirements.txt: 필요한 패키지 목록

## 지원

문의사항은 Sempio R&D Team에 문의하세요.
