"""
누락된 균주만 캐싱하는 스크립트

이미 캐시된 균주는 건너뛰고, 아직 캐시되지 않은 균주만 수집합니다.
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


def get_cached_organisms(connector: KEGGConnector) -> set:
    """Get set of already cached organism codes"""
    cache_dir = connector.cache_dir
    cached = set()

    for cache_file in cache_dir.glob("pathways_*.json"):
        # Extract org code from filename: pathways_eco.json -> eco
        org_code = cache_file.stem.replace('pathways_', '')
        cached.add(org_code)

    return cached


def precache_missing_strains(delay_seconds: int = 10, max_attempts: int = 3):
    """
    누락된 균주만 캐싱

    Args:
        delay_seconds: API 호출 사이 대기 시간 (초)
        max_attempts: 실패 시 재시도 횟수
    """
    print("="*80)
    print("누락된 균주 KEGG 데이터 캐싱")
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

    # Initialize connector with cache enabled
    connector = KEGGConnector(use_cache=True)

    # Get already cached organisms
    cached_orgs = get_cached_organisms(connector)
    print(f"이미 캐시된 균주: {len(cached_orgs)}개")
    print(f"캐시된 organism codes: {', '.join(sorted(cached_orgs))}")
    print()

    # Find missing organisms
    missing_species = []
    for genus, species in unique_species:
        # Try to find org code
        cache_key = f"organism_{genus}_{species}"
        cached = connector._load_cache(cache_key)

        if cached:
            org_code = cached.get('organism_code')
            if org_code and org_code not in cached_orgs:
                missing_species.append((genus, species, org_code))
        else:
            # Don't know org code yet, need to check
            missing_species.append((genus, species, None))

    print(f"누락된 균주: {len(missing_species)}개")
    print()

    # Statistics
    stats = {
        'total': len(missing_species),
        'success': 0,
        'org_code_not_found': 0,
        'pathway_not_found': 0,
        'failed': 0,
        'already_cached': len(cached_orgs)
    }

    print("누락된 데이터 수집 시작...")
    print("-" * 80)

    for idx, species_info in enumerate(missing_species, 1):
        genus, species = species_info[0], species_info[1]
        known_org_code = species_info[2] if len(species_info) > 2 else None

        print(f"\n[{idx}/{stats['total']}] {genus} {species}")

        try:
            # Step 1: Find organism code (if not known)
            if known_org_code:
                org_code = known_org_code
                print(f"  [O] Organism code 이미 알고 있음: {org_code}")
            else:
                print("  단계 1: KEGG organism code 검색 중...")
                org_code = connector.find_organism(genus, species)

                if not org_code:
                    print(f"  [X] KEGG에서 organism code를 찾을 수 없음")
                    stats['org_code_not_found'] += 1
                    continue

                print(f"  [O] Organism code 발견: {org_code}")

            # Check if this org code is already cached
            cache_key = f"pathways_{org_code}"
            cache_path = connector._get_cache_path(cache_key)

            if connector._is_cache_valid(cache_path):
                print(f"  [O] 이미 캐시됨 (캐시 파일 사용)")
                stats['success'] += 1
                continue

            # Step 2: Get pathways with retry
            print(f"  단계 2: Pathway 데이터 수집 중...")

            success = False
            for attempt in range(max_attempts):
                if attempt > 0:
                    print(f"  재시도 {attempt}/{max_attempts}...")
                    time.sleep(delay_seconds * 2)  # Double delay for retry

                try:
                    start_time = time.time()
                    org_pathways = connector.get_organism_pathways(org_code)
                    elapsed = time.time() - start_time

                    if org_pathways:
                        pathway_count = len(org_pathways.pathways)
                        print(f"  [O] {pathway_count}개 pathway 수집 완료 (소요시간: {elapsed:.1f}초)")
                        stats['success'] += 1
                        success = True
                        break
                    else:
                        print(f"  [X] Pathway 데이터가 비어있음")

                except Exception as e:
                    print(f"  [X] 시도 {attempt + 1} 실패: {e}")

            if not success:
                print(f"  [X] {max_attempts}번 시도 후 실패")
                stats['pathway_not_found'] += 1
                continue

            # Wait before next API call
            if idx < stats['total']:
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
    print(f"  이전 캐시:            {stats['already_cached']}")
    print(f"  누락 균주 수:         {stats['total']}")
    print(f"  새로 캐시됨:          {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    print(f"  실패:")
    print(f"    - Org code 없음:    {stats['org_code_not_found']}")
    print(f"    - Pathway 없음:     {stats['pathway_not_found']}")
    print(f"    - 기타 오류:        {stats['failed']}")
    print()
    print(f"총 캐시된 균주: {stats['already_cached'] + stats['success']}")
    print(f"캐시 디렉토리: {connector.cache_dir}")
    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="누락된 균주만 KEGG 데이터 캐싱"
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=10,
        help='API 호출 사이 대기 시간 (초, 기본값: 10)'
    )
    parser.add_argument(
        '--retry',
        type=int,
        default=3,
        help='실패 시 재시도 횟수 (기본값: 3)'
    )

    args = parser.parse_args()

    precache_missing_strains(
        delay_seconds=args.delay,
        max_attempts=args.retry
    )
