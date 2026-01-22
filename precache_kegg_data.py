"""
KEGG 데이터 사전 캐싱 스크립트

모든 균주에 대한 KEGG 데이터를 미리 다운로드하여 캐시에 저장합니다.
이렇게 하면 사용자가 블렌드 최적화를 실행할 때 빠르게 응답할 수 있습니다.
"""

import sys
import time
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from kegg_connector import KEGGConnector


def load_strains(csv_path: str = None) -> pd.DataFrame:
    """Load strain data from CSV"""
    if csv_path is None:
        csv_path = Path(__file__).parent / "data" / "strains.csv"

    df = pd.read_csv(csv_path)
    return df


def extract_unique_species(df: pd.DataFrame) -> list:
    """Extract unique genus-species combinations"""
    # Remove asterisks from genus and species names
    df['genus_clean'] = df['genus'].str.replace('*', '').str.strip()
    df['species_clean'] = df['species'].str.replace('*', '').str.strip()

    # Get unique combinations
    unique = df[['genus_clean', 'species_clean']].drop_duplicates()

    return [(row['genus_clean'], row['species_clean'])
            for _, row in unique.iterrows()]


def precache_all_strains(delay_seconds: int = 2):
    """
    사전에 모든 균주 데이터를 캐시에 저장

    Args:
        delay_seconds: API 호출 사이 대기 시간 (초)
    """
    print("="*80)
    print("KEGG 데이터 사전 캐싱 시작")
    print("="*80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load strains
    print("균주 데이터 로딩 중...")
    df = load_strains()
    print(f"총 {len(df)}개 균주 로드됨")

    # Extract unique species
    unique_species = extract_unique_species(df)
    print(f"고유 종 수: {len(unique_species)}")
    print()

    # Initialize connector with cache enabled
    connector = KEGGConnector(use_cache=True)

    # Statistics
    stats = {
        'total': len(unique_species),
        'success': 0,
        'org_code_not_found': 0,
        'pathway_not_found': 0,
        'failed': 0,
        'cached': 0
    }

    print("데이터 수집 시작...")
    print("-" * 80)

    for idx, (genus, species) in enumerate(unique_species, 1):
        print(f"\n[{idx}/{stats['total']}] {genus} {species}")
        print("  단계 1: KEGG organism code 검색 중...")

        try:
            # Step 1: Find organism code
            org_code = connector.find_organism(genus, species)

            if not org_code:
                print(f"  [X] KEGG에서 organism code를 찾을 수 없음")
                stats['org_code_not_found'] += 1
                continue

            print(f"  [O] Organism code 발견: {org_code}")

            # Step 2: Get pathways (this will cache automatically)
            print(f"  단계 2: Pathway 데이터 수집 중...")

            # Check if already cached
            cache_key = f"pathways_{org_code}"
            cache_path = connector._get_cache_path(cache_key)

            if connector._is_cache_valid(cache_path):
                print(f"  [O] 이미 캐시됨 (캐시 파일 사용)")
                stats['cached'] += 1
                stats['success'] += 1
                continue

            # Get pathways (will trigger API calls and caching)
            start_time = time.time()
            org_pathways = connector.get_organism_pathways(org_code)
            elapsed = time.time() - start_time

            if not org_pathways:
                print(f"  [X] Pathway 데이터를 가져올 수 없음")
                stats['pathway_not_found'] += 1
                continue

            # Success
            pathway_count = len(org_pathways.pathways)
            print(f"  [O] {pathway_count}개 pathway 수집 완료 (소요시간: {elapsed:.1f}초)")
            stats['success'] += 1

            # Wait before next API call to respect rate limits
            if idx < stats['total']:  # Don't wait after last one
                print(f"  대기 중... ({delay_seconds}초)")
                time.sleep(delay_seconds)

        except Exception as e:
            print(f"  [X] 오류 발생: {e}")
            stats['failed'] += 1
            continue

    # Print summary
    print("\n" + "="*80)
    print("수집 완료!")
    print("="*80)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("통계:")
    print(f"  총 균주 수:           {stats['total']}")
    print(f"  성공:                 {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    print(f"    - 새로 캐시됨:      {stats['success'] - stats['cached']}")
    print(f"    - 이미 캐시됨:      {stats['cached']}")
    print(f"  실패:")
    print(f"    - Org code 없음:    {stats['org_code_not_found']}")
    print(f"    - Pathway 없음:     {stats['pathway_not_found']}")
    print(f"    - 기타 오류:        {stats['failed']}")
    print()
    print(f"캐시 디렉토리: {connector.cache_dir}")
    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="KEGG 데이터 사전 캐싱 스크립트"
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=2,
        help='API 호출 사이 대기 시간 (초, 기본값: 2)'
    )

    args = parser.parse_args()

    precache_all_strains(delay_seconds=args.delay)
