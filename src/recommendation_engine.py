"""
Recommendation Engine

Core module for recommending optimal peptone products based on strain requirements
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd
from itertools import combinations

from .strain_manager import StrainProfile, StrainDatabase, STRAIN_CATEGORIES
from .peptone_analyzer import PeptoneProduct, PeptoneDatabase, ESSENTIAL_AMINO_ACIDS
from .utils import normalize_score, calculate_deviation, calculate_weighted_average


# Scoring weights for fitness calculation
SCORING_WEIGHTS = {
    'nutritional_match': 0.40,      # 40% - Overall nutritional requirement matching
    'amino_acid_match': 0.25,       # 25% - Amino acid profile matching
    'growth_factor_match': 0.20,    # 20% - Growth factors (nucleotides, vitamins)
    'mw_distribution_match': 0.15   # 15% - Molecular weight distribution
}

# Optimal molecular weight profiles by strain category
OPTIMAL_MW_PROFILES = {
    'LAB': {
        'mw_pct_lt250Da': 0.25,     # 25% or more
        'mw_pct_250_500Da': 0.30,   # 30% or more
        'mw_pct_gt1000Da': 0.20      # 20% or less (prefer lower MW)
    },
    'Bacillus': {
        'mw_pct_lt250Da': 0.15,
        'mw_pct_gt1000Da': 0.40      # Can utilize high MW
    },
    'E_coli': {
        'mw_pct_lt250Da': 0.20,
        'mw_pct_250_500Da': 0.35,
        'mw_pct_gt1000Da': 0.25
    },
    'Yeast': {
        'mw_pct_lt250Da': 0.20,
        'mw_pct_250_500Da': 0.30,
        'mw_pct_500_750Da': 0.20,
        'mw_pct_gt1000Da': 0.30
    },
    'Actinomycetes': {
        'mw_pct_250_500Da': 0.25,
        'mw_pct_500_750Da': 0.25,
        'mw_pct_gt1000Da': 0.35       # Complex nitrogen sources
    },
    'Other': {
        'mw_pct_250_500Da': 0.30,
        'mw_pct_500_750Da': 0.25,
        'mw_pct_gt1000Da': 0.30
    }
}


@dataclass
class RecommendationResult:
    """Result of a peptone recommendation"""

    strain: StrainProfile
    peptones: List[PeptoneProduct]
    ratios: List[float]  # Mixing ratios (sum to 1.0)
    overall_score: float
    detailed_scores: Dict[str, float] = field(default_factory=dict)
    rationale: str = ""

    def get_description(self) -> str:
        """Get human-readable description"""
        if len(self.peptones) == 1:
            return f"{self.peptones[0].name}"
        else:
            parts = []
            for pep, ratio in zip(self.peptones, self.ratios):
                parts.append(f"{pep.name} {ratio*100:.0f}%")
            return " + ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'strain_id': self.strain.strain_id,
            'strain_name': self.strain.get_full_name(),
            'description': self.get_description(),
            'peptones': [p.name for p in self.peptones],
            'ratios': [float(r) for r in self.ratios],
            'overall_score': float(self.overall_score),
            'detailed_scores': {k: float(v) for k, v in self.detailed_scores.items()},
            'rationale': self.rationale
        }


class PeptoneRecommender:
    """Main recommendation engine"""

    def __init__(self,
                 strain_db: StrainDatabase,
                 peptone_db: PeptoneDatabase):
        """
        Initialize recommender

        Args:
            strain_db: Strain database
            peptone_db: Peptone database
        """
        self.strain_db = strain_db
        self.peptone_db = peptone_db

    def recommend_single(self,
                        strain_id: str,
                        top_n: int = 5,
                        sempio_only: bool = True) -> List[RecommendationResult]:
        """
        Recommend single peptone products

        Args:
            strain_id: Strain identifier
            top_n: Number of recommendations
            sempio_only: Only recommend Sempio products

        Returns:
            List of recommendations sorted by score
        """
        strain = self.strain_db.get_strain_by_id(strain_id)
        if not strain:
            raise ValueError(f"Strain not found: {strain_id}")

        # Get candidate peptones
        if sempio_only:
            candidates = self.peptone_db.get_sempio_peptones()
        else:
            candidates = self.peptone_db.peptones

        # Score each peptone
        results = []
        for peptone in candidates:
            score, detailed = self.calculate_fitness_score(strain, peptone)

            # Create recommendation
            rec = RecommendationResult(
                strain=strain,
                peptones=[peptone],
                ratios=[1.0],
                overall_score=score,
                detailed_scores=detailed,
                rationale=self._generate_rationale(strain, [peptone], [1.0], detailed)
            )
            results.append(rec)

        # Sort by score
        results.sort(key=lambda x: x.overall_score, reverse=True)

        return results[:top_n]

    def recommend_blend(self,
                       strain_id: str,
                       max_components: int = 3,
                       top_n: int = 5,
                       sempio_only: bool = True) -> List[RecommendationResult]:
        """
        Recommend peptone blends (2-3 components)

        Args:
            strain_id: Strain identifier
            max_components: Maximum number of peptones in blend (2 or 3)
            top_n: Number of recommendations
            sempio_only: Only recommend Sempio products

        Returns:
            List of blend recommendations sorted by score
        """
        strain = self.strain_db.get_strain_by_id(strain_id)
        if not strain:
            raise ValueError(f"Strain not found: {strain_id}")

        # Get candidate peptones
        if sempio_only:
            candidates = self.peptone_db.get_sempio_peptones()
        else:
            candidates = self.peptone_db.peptones

        # First get top single peptones to use as base
        single_recs = self.recommend_single(strain_id, top_n=5, sempio_only=sempio_only)
        top_singles = [r.peptones[0] for r in single_recs]

        all_results = []

        # Generate 2-component blends
        if max_components >= 2:
            for pep1, pep2 in combinations(top_singles, 2):
                # Try different ratios
                for ratio1 in [0.3, 0.4, 0.5, 0.6, 0.7]:
                    ratio2 = 1.0 - ratio1
                    if ratio2 < 0.1 or ratio2 > 0.8:  # Constraint check
                        continue

                    score, detailed = self._evaluate_blend(
                        strain, [pep1, pep2], [ratio1, ratio2]
                    )

                    rec = RecommendationResult(
                        strain=strain,
                        peptones=[pep1, pep2],
                        ratios=[ratio1, ratio2],
                        overall_score=score,
                        detailed_scores=detailed,
                        rationale=self._generate_rationale(
                            strain, [pep1, pep2], [ratio1, ratio2], detailed
                        )
                    )
                    all_results.append(rec)

        # Generate 3-component blends
        if max_components >= 3:
            for pep1, pep2, pep3 in combinations(top_singles[:4], 3):
                # Try different ratios
                for r1 in [0.2, 0.3, 0.4, 0.5]:
                    for r2 in [0.2, 0.3, 0.4]:
                        r3 = 1.0 - r1 - r2
                        if r3 < 0.1 or r3 > 0.8:  # Constraint check
                            continue
                        if r1 < 0.1 or r1 > 0.8 or r2 < 0.1 or r2 > 0.8:
                            continue

                        score, detailed = self._evaluate_blend(
                            strain, [pep1, pep2, pep3], [r1, r2, r3]
                        )

                        rec = RecommendationResult(
                            strain=strain,
                            peptones=[pep1, pep2, pep3],
                            ratios=[r1, r2, r3],
                            overall_score=score,
                            detailed_scores=detailed,
                            rationale=self._generate_rationale(
                                strain, [pep1, pep2, pep3], [r1, r2, r3], detailed
                            )
                        )
                        all_results.append(rec)

        # Sort and return top results
        all_results.sort(key=lambda x: x.overall_score, reverse=True)
        return all_results[:top_n]

    def calculate_fitness_score(self,
                                strain: StrainProfile,
                                peptone: PeptoneProduct) -> Tuple[float, Dict[str, float]]:
        """
        Calculate fitness score between strain and peptone

        Args:
            strain: Strain profile
            peptone: Peptone product

        Returns:
            Tuple of (overall_score, detailed_scores)
        """
        detailed_scores = {}

        # 1. Nutritional requirement matching (40%)
        nut_score = self._match_nutritional_requirements(strain, peptone)
        detailed_scores['nutritional_match'] = nut_score

        # 2. Amino acid profile matching (25%)
        aa_score = self._match_amino_acid_profile(strain, peptone)
        detailed_scores['amino_acid_match'] = aa_score

        # 3. Growth factors matching (20%)
        gf_score = self._match_growth_factors(strain, peptone)
        detailed_scores['growth_factor_match'] = gf_score

        # 4. Molecular weight distribution (15%)
        mw_score = self._match_molecular_weight(strain, peptone)
        detailed_scores['mw_distribution_match'] = mw_score

        # Calculate weighted overall score
        overall = (
            nut_score * SCORING_WEIGHTS['nutritional_match'] +
            aa_score * SCORING_WEIGHTS['amino_acid_match'] +
            gf_score * SCORING_WEIGHTS['growth_factor_match'] +
            mw_score * SCORING_WEIGHTS['mw_distribution_match']
        )

        return overall, detailed_scores

    def _match_nutritional_requirements(self,
                                       strain: StrainProfile,
                                       peptone: PeptoneProduct) -> float:
        """Match overall nutritional requirements"""
        score = 0.0

        # Get strain category info
        category_info = STRAIN_CATEGORIES.get(strain.category, {})
        nutritional_type = category_info.get('nutritional_type', 'moderate')

        # High TN and AN are generally good
        tn = peptone.profile.general.get('general_TN', 0)
        an = peptone.profile.general.get('general_AN', 0)

        # Fastidious strains need high AN
        if nutritional_type == 'fastidious':
            an_score = min(1.0, an / 15.0)  # Normalize to 15% as good
            score += an_score * 0.6

            # Also need high TN
            tn_score = min(1.0, tn / 80.0)  # Normalize to 80% as good
            score += tn_score * 0.4

        # Minimal strains are less demanding
        elif nutritional_type == 'minimal':
            tn_score = min(1.0, tn / 60.0)
            score += tn_score * 0.7
            an_score = min(1.0, an / 8.0)
            score += an_score * 0.3

        else:  # moderate or variable
            tn_score = min(1.0, tn / 70.0)
            an_score = min(1.0, an / 12.0)
            score += (tn_score + an_score) / 2

        return normalize_score(score)

    def _match_amino_acid_profile(self,
                                  strain: StrainProfile,
                                  peptone: PeptoneProduct) -> float:
        """Match amino acid profile"""
        score = 0.0

        # Essential amino acids are important for all strains
        essential_ratio = peptone.profile.get_essential_aa_ratio()
        score += essential_ratio * 0.4

        # Free amino acids are immediately available
        free_ratio = peptone.profile.get_free_aa_ratio()
        score += free_ratio * 0.3

        # BCAA are important for growth
        bcaa_ratio = peptone.profile.get_bcaa_ratio()
        score += bcaa_ratio * 0.3

        return normalize_score(score)

    def _match_growth_factors(self,
                             strain: StrainProfile,
                             peptone: PeptoneProduct) -> float:
        """Match growth factors (nucleotides, vitamins)"""
        score = 0.0

        category_info = STRAIN_CATEGORIES.get(strain.category, {})
        requirements = category_info.get('key_requirements', [])

        # Check nucleotides
        if 'nucleotides' in requirements or 'B_vitamins' in requirements:
            nucleotide_sum = sum(peptone.profile.nucleotides.values())
            nucleotide_score = min(1.0, nucleotide_sum / 20.0)
            score += nucleotide_score * 0.5

            # Check vitamins
            vitamin_sum = sum(peptone.profile.vitamins.values())
            vitamin_score = min(1.0, vitamin_sum / 10.0)
            score += vitamin_score * 0.5
        else:
            # Less critical but still beneficial
            nucleotide_sum = sum(peptone.profile.nucleotides.values())
            vitamin_sum = sum(peptone.profile.vitamins.values())
            score = min(1.0, (nucleotide_sum + vitamin_sum) / 30.0)

        return normalize_score(score)

    def _match_molecular_weight(self,
                               strain: StrainProfile,
                               peptone: PeptoneProduct) -> float:
        """Match molecular weight distribution"""
        # Get optimal profile for strain category
        optimal = OPTIMAL_MW_PROFILES.get(strain.category, OPTIMAL_MW_PROFILES['Other'])

        # Get actual profile from peptone
        actual = peptone.profile.molecular_weight

        # Calculate deviation
        deviation = calculate_deviation(optimal, actual)

        # Convert deviation to score (lower deviation = higher score)
        score = 1.0 - min(1.0, deviation)

        return normalize_score(score)

    def _evaluate_blend(self,
                       strain: StrainProfile,
                       peptones: List[PeptoneProduct],
                       ratios: List[float]) -> Tuple[float, Dict[str, float]]:
        """
        Evaluate a peptone blend

        Args:
            strain: Strain profile
            peptones: List of peptones in blend
            ratios: Mixing ratios

        Returns:
            Tuple of (score, detailed_scores)
        """
        # Create virtual blended profile by weighted averaging
        # This is a simplified approach - actual blending would be more complex

        # For now, use weighted average of individual scores
        total_score = 0.0
        detailed_scores = {
            'nutritional_match': 0.0,
            'amino_acid_match': 0.0,
            'growth_factor_match': 0.0,
            'mw_distribution_match': 0.0
        }

        for peptone, ratio in zip(peptones, ratios):
            score, details = self.calculate_fitness_score(strain, peptone)
            total_score += score * ratio

            for key in detailed_scores:
                detailed_scores[key] += details[key] * ratio

        # Add synergy bonus for complementary blends (up to 10% boost)
        synergy = self._calculate_synergy(peptones, ratios)
        total_score = total_score * (1.0 + synergy * 0.1)

        return normalize_score(total_score), detailed_scores

    def _calculate_synergy(self,
                          peptones: List[PeptoneProduct],
                          ratios: List[float]) -> float:
        """
        Calculate synergy score for peptone blend

        Returns value between 0 and 1, where higher means better complementarity
        """
        if len(peptones) < 2:
            return 0.0

        # Check if peptones have different raw materials (more complementary)
        materials = set(p.raw_material for p in peptones)
        material_diversity = len(materials) / len(peptones)

        # Check amino acid profile diversity
        # (simplified - could be more sophisticated)
        aa_profiles = []
        for peptone in peptones:
            profile_vec = []
            for aa in ESSENTIAL_AMINO_ACIDS:
                faa_val = peptone.profile.free_amino_acids.get(f'faa_{aa}', 0)
                profile_vec.append(faa_val)
            aa_profiles.append(np.array(profile_vec))

        # Calculate diversity as average pairwise distance
        if len(aa_profiles) >= 2:
            distances = []
            for i in range(len(aa_profiles)):
                for j in range(i+1, len(aa_profiles)):
                    dist = np.linalg.norm(aa_profiles[i] - aa_profiles[j])
                    distances.append(dist)
            aa_diversity = np.mean(distances) / 10.0  # Normalize
        else:
            aa_diversity = 0.0

        # Combine factors
        synergy = (material_diversity * 0.6 + min(1.0, aa_diversity) * 0.4)

        return normalize_score(synergy)

    def _generate_rationale(self,
                           strain: StrainProfile,
                           peptones: List[PeptoneProduct],
                           ratios: List[float],
                           detailed_scores: Dict[str, float]) -> str:
        """Generate explanation for recommendation"""
        parts = []

        # Identify strengths
        strengths = []
        if detailed_scores.get('amino_acid_match', 0) > 0.7:
            strengths.append("excellent amino acid profile")
        if detailed_scores.get('growth_factor_match', 0) > 0.7:
            strengths.append("rich in growth factors")
        if detailed_scores.get('nutritional_match', 0) > 0.7:
            strengths.append("optimal nitrogen content")
        if detailed_scores.get('mw_distribution_match', 0) > 0.7:
            strengths.append("suitable peptide size distribution")

        if strengths:
            parts.append("Strengths: " + ", ".join(strengths))

        # Mention blend complementarity
        if len(peptones) > 1:
            materials = [p.raw_material for p in peptones]
            if len(set(materials)) > 1:
                parts.append(f"Complementary sources: {', '.join(set(materials))}")

        return "; ".join(parts) if parts else "Good overall match"


if __name__ == "__main__":
    # Test recommendation engine
    print("Testing recommendation engine...")

    # Load databases
    from pathlib import Path
    import sys

    strain_db = StrainDatabase()
    peptone_db = PeptoneDatabase()

    strain_file = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
    peptone_file = Path(r"D:\folder1\composition_template.xlsx")

    if strain_file.exists() and peptone_file.exists():
        strain_db.load_from_excel(str(strain_file))
        peptone_db.load_from_excel(str(peptone_file))

        # Create recommender
        recommender = PeptoneRecommender(strain_db, peptone_db)

        # Test single peptone recommendation
        print("\n" + "="*80)
        print("Single Peptone Recommendations for KCCM 12116")
        print("="*80)

        recs = recommender.recommend_single("KCCM 12116", top_n=5, sempio_only=True)

        for i, rec in enumerate(recs, 1):
            print(f"\n{i}. {rec.get_description()}")
            print(f"   Score: {rec.overall_score:.3f}")
            print(f"   Details: {', '.join(f'{k}: {v:.3f}' for k, v in rec.detailed_scores.items())}")
            print(f"   Rationale: {rec.rationale}")

        # Test blend recommendation
        print("\n" + "="*80)
        print("Blend Recommendations for KCCM 12116")
        print("="*80)

        blend_recs = recommender.recommend_blend("KCCM 12116", max_components=3, top_n=3, sempio_only=True)

        for i, rec in enumerate(blend_recs, 1):
            print(f"\n{i}. {rec.get_description()}")
            print(f"   Score: {rec.overall_score:.3f}")
            print(f"   Rationale: {rec.rationale}")

    else:
        print("Data files not found. Skipping test.")
