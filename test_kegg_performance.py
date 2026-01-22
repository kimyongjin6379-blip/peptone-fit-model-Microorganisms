"""
KEGG Performance Test Script

Tests KEGG API performance and caching effectiveness for peptone recommendations
"""

import time
from pathlib import Path
import pandas as pd
from typing import Dict, List, Tuple

from src.strain_manager import StrainDatabase
from src.peptone_analyzer import PeptoneDatabase
from src.recommendation_engine import PeptoneRecommender
from src.recommendation_engine_v2 import EnhancedPeptoneRecommender
from src.kegg_connector import KEGGConnector


def measure_time(func, *args, **kwargs):
    """Measure execution time of a function"""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


def test_kegg_api_latency():
    """Test 1: Measure KEGG API latency"""
    print("\n" + "="*80)
    print("TEST 1: KEGG API Latency Test")
    print("="*80)

    connector = KEGGConnector()

    test_organisms = [
        ('Escherichia', 'coli', 'eco'),
        ('Lactobacillus', 'plantarum', 'lpl'),
        ('Bacillus', 'subtilis', 'bsu'),
    ]

    results = []

    for genus, species, expected_code in test_organisms:
        print(f"\n[DNA] Testing {genus} {species}...")

        # Test 1: Find organism (first call - no cache)
        _, find_time = measure_time(connector.find_organism, genus, species)
        print(f"  Find organism: {find_time:.3f}s")

        # Test 2: Get pathways (first call - no cache)
        org_code = connector.find_organism(genus, species)
        if org_code:
            _, pathway_time = measure_time(connector.get_organism_pathways, org_code)
            print(f"  Get pathways: {pathway_time:.3f}s")

            # Test 3: Cached call (should be instant)
            _, cached_time = measure_time(connector.get_organism_pathways, org_code)
            print(f"  Cached call: {cached_time:.6f}s")
            print(f"  Cache speedup: {pathway_time/cached_time:.1f}x faster")

            total_time = find_time + pathway_time

            results.append({
                'organism': f"{genus} {species}",
                'find_time': find_time,
                'pathway_time': pathway_time,
                'cached_time': cached_time,
                'total_first': total_time,
                'speedup': pathway_time/cached_time if cached_time > 0 else 0
            })
        else:
            print(f"  [WARN] Organism not found in KEGG")
            results.append({
                'organism': f"{genus} {species}",
                'find_time': find_time,
                'pathway_time': None,
                'cached_time': None,
                'total_first': find_time,
                'speedup': 0
            })

    # Summary
    print("\n" + "-"*80)
    print("Summary:")
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print(f"\nAverage first call: {df['total_first'].mean():.3f}s")

    return results


def test_single_recommendation_performance(strain_db, peptone_db):
    """Test 2: Single recommendation performance comparison"""
    print("\n" + "="*80)
    print("TEST 2: Single Recommendation Performance")
    print("="*80)

    # Select test strains
    test_strains = strain_db.strains[:5]  # First 5 strains

    results = []

    for strain in test_strains:
        print(f"\n[STRAIN] Testing strain: {strain.strain_id} - {strain.get_full_name()}")

        # Test WITHOUT KEGG
        recommender_no_kegg = PeptoneRecommender(strain_db, peptone_db)
        _, time_no_kegg = measure_time(
            recommender_no_kegg.recommend_single,
            strain.strain_id, top_n=5, sempio_only=True
        )
        print(f"  Without KEGG: {time_no_kegg:.3f}s")

        # Test WITH KEGG
        recommender_kegg = EnhancedPeptoneRecommender(
            strain_db, peptone_db, use_kegg=True
        )

        if not strain.is_nda:
            _, time_kegg_first = measure_time(
                recommender_kegg.recommend_with_pathways,
                strain.strain_id, top_n=5, sempio_only=True
            )
            print(f"  With KEGG (1st): {time_kegg_first:.3f}s")

            # Cached call
            _, time_kegg_cached = measure_time(
                recommender_kegg.recommend_with_pathways,
                strain.strain_id, top_n=5, sempio_only=True
            )
            print(f"  With KEGG (cached): {time_kegg_cached:.3f}s")
            print(f"  Overhead: {time_kegg_first - time_no_kegg:.3f}s ({(time_kegg_first/time_no_kegg):.1f}x)")

            results.append({
                'strain': strain.strain_id,
                'no_kegg': time_no_kegg,
                'kegg_first': time_kegg_first,
                'kegg_cached': time_kegg_cached,
                'overhead': time_kegg_first - time_no_kegg,
                'overhead_pct': ((time_kegg_first/time_no_kegg - 1) * 100)
            })
        else:
            print(f"  [WARN] NDA strain - KEGG skipped")
            results.append({
                'strain': strain.strain_id,
                'no_kegg': time_no_kegg,
                'kegg_first': None,
                'kegg_cached': None,
                'overhead': None,
                'overhead_pct': None
            })

    # Summary
    print("\n" + "-"*80)
    print("Summary:")
    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    valid_results = [r for r in results if r['kegg_first'] is not None]
    if valid_results:
        avg_overhead = sum(r['overhead'] for r in valid_results) / len(valid_results)
        avg_overhead_pct = sum(r['overhead_pct'] for r in valid_results) / len(valid_results)
        print(f"\nAverage overhead: {avg_overhead:.3f}s ({avg_overhead_pct:.1f}%)")

    return results


def test_blend_optimization_performance(strain_db, peptone_db):
    """Test 3: Blend optimization performance simulation"""
    print("\n" + "="*80)
    print("TEST 3: Blend Optimization Performance Simulation")
    print("="*80)

    # Select one test strain
    strain = strain_db.strains[0]
    print(f"\n[STRAIN] Test strain: {strain.strain_id} - {strain.get_full_name()}")

    results = {}

    # Test WITHOUT KEGG
    print("\n[TEST] Testing WITHOUT KEGG...")
    recommender_no_kegg = EnhancedPeptoneRecommender(
        strain_db, peptone_db, use_kegg=False
    )

    _, time_no_kegg = measure_time(
        recommender_no_kegg.recommend_optimized_blend,
        strain.strain_id,
        max_components=2,
        top_n=3,
        sempio_only=True,
        use_optimizer=True
    )
    print(f"  2-component blend (no KEGG): {time_no_kegg:.3f}s")
    results['blend_2_no_kegg'] = time_no_kegg

    # Test WITH KEGG (if not NDA)
    if not strain.is_nda:
        print("\n[TEST] Testing WITH KEGG...")
        recommender_kegg = EnhancedPeptoneRecommender(
            strain_db, peptone_db, use_kegg=True
        )

        # First call (no cache)
        _, time_kegg_first = measure_time(
            recommender_kegg.recommend_optimized_blend,
            strain.strain_id,
            max_components=2,
            top_n=3,
            sempio_only=True,
            use_optimizer=True
        )
        print(f"  2-component blend (KEGG, 1st): {time_kegg_first:.3f}s")

        # Cached call
        _, time_kegg_cached = measure_time(
            recommender_kegg.recommend_optimized_blend,
            strain.strain_id,
            max_components=2,
            top_n=3,
            sempio_only=True,
            use_optimizer=True
        )
        print(f"  2-component blend (KEGG, cached): {time_kegg_cached:.3f}s")

        results['blend_2_kegg_first'] = time_kegg_first
        results['blend_2_kegg_cached'] = time_kegg_cached

        # 3-component test
        print("\n[TEST] Testing 3-component blend WITH KEGG...")
        _, time_3comp = measure_time(
            recommender_kegg.recommend_optimized_blend,
            strain.strain_id,
            max_components=3,
            top_n=3,
            sempio_only=True,
            use_optimizer=True
        )
        print(f"  3-component blend (KEGG, cached): {time_3comp:.3f}s")
        results['blend_3_kegg_cached'] = time_3comp

        # Calculate overhead
        overhead = time_kegg_first - time_no_kegg
        overhead_pct = ((time_kegg_first/time_no_kegg - 1) * 100)

        print("\n" + "-"*80)
        print("Summary:")
        print(f"  Overhead for blend: {overhead:.3f}s ({overhead_pct:.1f}%)")
        print(f"  Cache benefit: {time_kegg_first - time_kegg_cached:.3f}s")
        print(f"  3-comp vs 2-comp: {time_3comp - time_kegg_cached:.3f}s")
    else:
        print(f"\n[WARN] NDA strain - KEGG tests skipped")

    return results


def test_cache_effectiveness():
    """Test 4: Cache effectiveness"""
    print("\n" + "="*80)
    print("TEST 4: Cache Effectiveness Test")
    print("="*80)

    connector = KEGGConnector()

    # Test organism
    genus, species = 'Escherichia', 'coli'

    print(f"\n[DNA] Testing cache for {genus} {species}")

    # First call - cold cache
    print("\n1. Cold cache (first call):")
    org_code, time1 = measure_time(connector.find_organism, genus, species)
    print(f"   Time: {time1:.3f}s")

    pathways, time2 = measure_time(connector.get_organism_pathways, org_code)
    print(f"   Pathways: {time2:.3f}s")
    print(f"   Total: {time1 + time2:.3f}s")

    # Second call - warm cache
    print("\n2. Warm cache (repeated call):")
    _, time3 = measure_time(connector.find_organism, genus, species)
    print(f"   Time: {time3:.6f}s")

    _, time4 = measure_time(connector.get_organism_pathways, org_code)
    print(f"   Pathways: {time4:.6f}s")
    print(f"   Total: {time3 + time4:.6f}s")

    # Calculate speedup
    cold_total = time1 + time2
    warm_total = time3 + time4
    speedup = cold_total / warm_total if warm_total > 0 else 0

    print("\n" + "-"*80)
    print("Cache Performance:")
    print(f"  Cold cache: {cold_total:.3f}s")
    print(f"  Warm cache: {warm_total:.6f}s")
    print(f"  Speedup: {speedup:.0f}x faster")
    print(f"  Time saved: {cold_total - warm_total:.3f}s")

    return {
        'cold_time': cold_total,
        'warm_time': warm_total,
        'speedup': speedup
    }


def generate_performance_report(test_results: Dict):
    """Generate comprehensive performance report"""
    print("\n" + "="*80)
    print("[TEST] PERFORMANCE TEST REPORT")
    print("="*80)

    print("\n## 1. KEGG API Latency")
    if 'api_latency' in test_results:
        results = test_results['api_latency']
        valid_results = [r for r in results if r['pathway_time'] is not None]
        if valid_results:
            avg_total = sum(r['total_first'] for r in valid_results) / len(valid_results)
            avg_speedup = sum(r['speedup'] for r in valid_results) / len(valid_results)
            print(f"   Average first call: {avg_total:.3f}s")
            print(f"   Average cache speedup: {avg_speedup:.1f}x")

    print("\n## 2. Single Recommendation Overhead")
    if 'single_perf' in test_results:
        results = test_results['single_perf']
        valid_results = [r for r in results if r['kegg_first'] is not None]
        if valid_results:
            avg_overhead = sum(r['overhead'] for r in valid_results) / len(valid_results)
            avg_pct = sum(r['overhead_pct'] for r in valid_results) / len(valid_results)
            print(f"   Average KEGG overhead: {avg_overhead:.3f}s ({avg_pct:.1f}%)")

    print("\n## 3. Blend Optimization Performance")
    if 'blend_perf' in test_results:
        results = test_results['blend_perf']
        if 'blend_2_kegg_first' in results:
            overhead = results['blend_2_kegg_first'] - results['blend_2_no_kegg']
            overhead_pct = ((results['blend_2_kegg_first']/results['blend_2_no_kegg'] - 1) * 100)
            print(f"   2-component blend overhead: {overhead:.3f}s ({overhead_pct:.1f}%)")

            cache_benefit = results['blend_2_kegg_first'] - results['blend_2_kegg_cached']
            print(f"   Cache benefit: {cache_benefit:.3f}s")

    print("\n## 4. Cache Effectiveness")
    if 'cache_test' in test_results:
        results = test_results['cache_test']
        print(f"   Speedup: {results['speedup']:.0f}x faster")
        print(f"   Time saved per cached call: {results['cold_time'] - results['warm_time']:.3f}s")

    print("\n## 5. Recommendations")
    print("\n### For Single Recommendation:")
    if 'single_perf' in test_results:
        valid_results = [r for r in test_results['single_perf'] if r['kegg_first'] is not None]
        if valid_results:
            avg_overhead = sum(r['overhead'] for r in valid_results) / len(valid_results)
            if avg_overhead < 2.0:
                print("   [OK] KEGG overhead is acceptable (<2s)")
                print("   [OK] Recommend enabling KEGG by default")
            elif avg_overhead < 5.0:
                print("   [WARN] KEGG overhead is moderate (2-5s)")
                print("   [WARN] Recommend as optional feature")
            else:
                print("   [ERROR] KEGG overhead is high (>5s)")
                print("   [ERROR] Recommend keeping disabled by default")

    print("\n### For Blend Optimization:")
    if 'blend_perf' in test_results:
        results = test_results['blend_perf']
        if 'blend_2_kegg_first' in results:
            overhead = results['blend_2_kegg_first'] - results['blend_2_no_kegg']
            if overhead < 5.0:
                print("   [OK] KEGG overhead is acceptable for blends")
                print("   [OK] Recommend enabling KEGG option")
            elif overhead < 10.0:
                print("   [WARN] KEGG overhead is moderate for blends")
                print("   [WARN] Recommend as optional feature with warning")
            else:
                print("   [ERROR] KEGG overhead is high for blends")
                print("   [ERROR] May need optimization before enabling")

    print("\n" + "="*80)


def main():
    """Main test execution"""
    print("KEGG Performance Test Suite")
    print("="*80)

    # Load databases
    print("\n[DB] Loading databases...")
    strain_file = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
    peptone_file = Path(r"D:\folder1\composition_template.xlsx")

    if not strain_file.exists() or not peptone_file.exists():
        print("[ERROR] Data files not found!")
        return

    strain_db = StrainDatabase()
    peptone_db = PeptoneDatabase()

    strain_db.load_from_excel(str(strain_file))
    peptone_db.load_from_excel(str(peptone_file))

    print(f"   Loaded {len(strain_db.strains)} strains")
    print(f"   Loaded {len(peptone_db.peptones)} peptones")

    # Run tests
    test_results = {}

    try:
        # Test 1: API Latency
        test_results['api_latency'] = test_kegg_api_latency()

        # Test 2: Single Recommendation
        test_results['single_perf'] = test_single_recommendation_performance(
            strain_db, peptone_db
        )

        # Test 3: Blend Optimization
        test_results['blend_perf'] = test_blend_optimization_performance(
            strain_db, peptone_db
        )

        # Test 4: Cache Effectiveness
        test_results['cache_test'] = test_cache_effectiveness()

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    # Generate report
    generate_performance_report(test_results)

    print("\n[OK] Performance test complete!")


if __name__ == "__main__":
    main()
