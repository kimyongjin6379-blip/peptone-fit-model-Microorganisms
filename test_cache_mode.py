"""
캐시 전용 모드 테스트 스크립트

캐시 우선 모드가 제대로 작동하는지 테스트합니다.
"""

import sys
from pathlib import Path
import time

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.strain_manager import StrainDatabase
from src.peptone_analyzer import PeptoneDatabase
from src.recommendation_engine_v2 import EnhancedPeptoneRecommender


def test_cache_mode():
    """Test cache-only mode"""

    print("="*80)
    print("캐시 전용 모드 테스트")
    print("="*80)
    print()

    # Load databases
    print("1. 데이터베이스 로딩 중...")
    strain_db = StrainDatabase()
    peptone_db = PeptoneDatabase()

    # Load from Excel files
    strain_file = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
    peptone_file = Path(r"D:\folder1\composition_template.xlsx")

    strain_db.load_from_excel(str(strain_file))
    peptone_db.load_from_excel(str(peptone_file))

    print(f"   균주 수: {len(strain_db.strains)}")
    print(f"   펩톤 수: {len(peptone_db.peptones)}")
    print()

    # Test strain (Lactiplantibacillus plantarum - has cache)
    # Find a strain with KEGG cache
    test_strain = None
    for strain in strain_db.strains:
        if "Lactiplantibacillus" in strain.genus and "plantarum" in strain.species:
            test_strain = strain
            test_strain_id = strain.strain_id
            break

    if not test_strain:
        print("테스트 균주를 찾을 수 없습니다!")
        return

    print(f"2. 테스트 균주: {test_strain.get_full_name()} (ID: {test_strain_id})")
    print()

    # Test 1: Normal mode (with API calls)
    print("-" * 80)
    print("테스트 1: 일반 모드 (API 호출 허용)")
    print("-" * 80)

    start_time = time.time()
    recommender_normal = EnhancedPeptoneRecommender(
        strain_db, peptone_db,
        use_kegg=True,
        kegg_cache_only=False
    )

    try:
        recs_normal = recommender_normal.recommend_with_pathways(
            test_strain_id, top_n=3, sempio_only=True
        )
        elapsed_normal = time.time() - start_time

        print(f"[OK] 완료 (소요시간: {elapsed_normal:.3f}초)")
        print(f"  추천 수: {len(recs_normal)}")
        if recs_normal:
            print(f"  1위 추천: {recs_normal[0].get_description()}")
            print(f"  1위 점수: {recs_normal[0].overall_score:.3f}")
        print()

    except Exception as e:
        elapsed_normal = time.time() - start_time
        print(f"[X] 오류 발생: {e}")
        print(f"  소요시간: {elapsed_normal:.3f}초")
        print()

    # Test 2: Cache-only mode
    print("-" * 80)
    print("테스트 2: 캐시 전용 모드 (API 호출 없음)")
    print("-" * 80)

    start_time = time.time()
    recommender_cache = EnhancedPeptoneRecommender(
        strain_db, peptone_db,
        use_kegg=True,
        kegg_cache_only=True
    )

    try:
        recs_cache = recommender_cache.recommend_with_pathways(
            test_strain_id, top_n=3, sempio_only=True
        )
        elapsed_cache = time.time() - start_time

        print(f"[OK] 완료 (소요시간: {elapsed_cache:.3f}초)")
        print(f"  추천 수: {len(recs_cache)}")
        if recs_cache:
            print(f"  1위 추천: {recs_cache[0].get_description()}")
            print(f"  1위 점수: {recs_cache[0].overall_score:.3f}")
        print()

        # Compare results
        if 'recs_normal' in locals() and recs_normal and recs_cache:
            print("-" * 80)
            print("결과 비교:")
            print("-" * 80)
            print(f"일반 모드 1위: {recs_normal[0].get_description()} ({recs_normal[0].overall_score:.3f})")
            print(f"캐시 모드 1위: {recs_cache[0].get_description()} ({recs_cache[0].overall_score:.3f})")
            print(f"속도 향상: {elapsed_normal/elapsed_cache:.1f}x")
            print()

    except Exception as e:
        elapsed_cache = time.time() - start_time
        print(f"[X] 오류 발생: {e}")
        print(f"  소요시간: {elapsed_cache:.3f}초")
        print()

    # Test 3: Strain without cache
    print("-" * 80)
    print("테스트 3: 캐시가 없는 균주 (캐시 전용 모드)")
    print("-" * 80)

    # Try a strain that likely doesn't have cache
    no_cache_strain_id = "46"  # Staphylococcus aureus
    no_cache_strain = strain_db.get_strain_by_id(no_cache_strain_id)

    if no_cache_strain:
        print(f"테스트 균주: {no_cache_strain.get_full_name()}")

        start_time = time.time()
        try:
            recs_no_cache = recommender_cache.recommend_with_pathways(
                no_cache_strain_id, top_n=3, sempio_only=True
            )
            elapsed = time.time() - start_time

            print(f"[OK] 완료 (소요시간: {elapsed:.3f}초)")
            print(f"  추천 수: {len(recs_no_cache)}")
            if recs_no_cache:
                print(f"  1위 추천: {recs_no_cache[0].get_description()}")
                print(f"  1위 점수: {recs_no_cache[0].overall_score:.3f}")
            print(f"  -> 캐시 없이도 정상 작동 (KEGG 데이터 없이 추천)")
            print()

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[X] 오류 발생: {e}")
            print(f"  소요시간: {elapsed:.3f}초")
            print()

    print("="*80)
    print("테스트 완료!")
    print("="*80)


if __name__ == "__main__":
    test_cache_mode()
