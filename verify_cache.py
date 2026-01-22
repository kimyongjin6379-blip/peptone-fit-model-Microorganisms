"""
KEGG 캐시 파일 검증 스크립트

캐시된 KEGG 데이터의 품질과 완전성을 검증합니다.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from kegg_connector import KEGGConnector, AMINO_ACID_PATHWAYS


def verify_cache():
    """캐시 파일들을 검증하고 통계를 출력"""

    print("="*80)
    print("KEGG 캐시 파일 검증")
    print("="*80)
    print()

    connector = KEGGConnector(use_cache=True)
    cache_dir = connector.cache_dir

    print(f"캐시 디렉토리: {cache_dir}")
    print()

    # Find all pathway cache files
    pathway_files = list(cache_dir.glob("pathways_*.json"))

    if not pathway_files:
        print("캐시 파일이 없습니다!")
        return

    print(f"발견된 캐시 파일: {len(pathway_files)}개")
    print("-" * 80)

    # Statistics
    stats = {
        'total_organisms': 0,
        'total_pathways': 0,
        'amino_acid_pathways': 0,
        'organisms_with_aa': 0
    }

    organism_details = []

    # Process each file
    for cache_file in sorted(pathway_files):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            org_code = data['organism_code']
            org_name = data['organism_name']
            pathways = data['pathways']
            retrieved_at = data.get('retrieved_at', 'Unknown')

            # Count pathways
            pathway_count = len(pathways)

            # Check for amino acid biosynthesis pathways
            aa_pathways_present = []
            for aa_name, pathway_id in AMINO_ACID_PATHWAYS.items():
                # Convert map to organism-specific code
                org_pathway_id = pathway_id.replace('map', org_code)

                # Check if present in data
                if org_pathway_id in pathways or pathway_id in pathways:
                    aa_pathways_present.append(aa_name)

            aa_count = len(aa_pathways_present)

            # Update stats
            stats['total_organisms'] += 1
            stats['total_pathways'] += pathway_count
            stats['amino_acid_pathways'] += aa_count

            if aa_count > 0:
                stats['organisms_with_aa'] += 1

            organism_details.append({
                'org_code': org_code,
                'org_name': org_name,
                'pathway_count': pathway_count,
                'aa_count': aa_count,
                'aa_pathways': aa_pathways_present,
                'retrieved_at': retrieved_at
            })

        except Exception as e:
            print(f"[X] {cache_file.name}: 오류 - {e}")
            continue

    # Print organism details
    print()
    print("균주별 상세 정보:")
    print("-" * 80)

    for detail in organism_details:
        print(f"\n균주: {detail['org_code']} ({detail['org_name']})")
        print(f"  총 Pathway 수: {detail['pathway_count']}")
        print(f"  아미노산 생합성 Pathway 수: {detail['aa_count']}/{len(AMINO_ACID_PATHWAYS)}")

        if detail['aa_count'] > 0:
            print(f"  발견된 아미노산 경로:")
            for aa in detail['aa_pathways'][:5]:  # Show first 5
                print(f"    - {aa}")
            if len(detail['aa_pathways']) > 5:
                print(f"    ... 외 {len(detail['aa_pathways']) - 5}개")

        print(f"  수집 시간: {detail['retrieved_at'][:19] if len(detail['retrieved_at']) > 19 else detail['retrieved_at']}")

    # Print summary
    print()
    print("="*80)
    print("요약 통계")
    print("="*80)
    print(f"총 캐시된 균주 수:              {stats['total_organisms']}")
    print(f"총 Pathway 수:                  {stats['total_pathways']}")
    print(f"평균 Pathway/균주:              {stats['total_pathways']/stats['total_organisms']:.1f}")
    print(f"총 아미노산 생합성 경로:        {stats['amino_acid_pathways']}")
    print(f"AA 경로 보유 균주:              {stats['organisms_with_aa']}/{stats['total_organisms']}")
    print()

    # Recommendations
    print("권장사항:")
    print("-" * 80)

    if stats['total_organisms'] < 10:
        print("- 캐시된 균주가 10개 미만입니다. precache_kegg_data.py를 다시 실행하여")
        print("  더 많은 데이터를 수집하는 것을 권장합니다.")
    else:
        print("- 충분한 캐시 데이터가 있습니다!")

    if stats['organisms_with_aa'] < stats['total_organisms']:
        missing = stats['total_organisms'] - stats['organisms_with_aa']
        print(f"- {missing}개 균주에 아미노산 생합성 경로 정보가 부족합니다.")

    print()
    print("="*80)


if __name__ == "__main__":
    verify_cache()
