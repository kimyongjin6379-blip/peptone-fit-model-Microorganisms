"""
Enhanced Recommendation Engine (v2)

Integrates KEGG pathway data and advanced blend optimization
"""

from typing import List, Dict, Optional, Tuple
import numpy as np

from .strain_manager import StrainProfile, StrainDatabase
from .peptone_analyzer import PeptoneProduct, PeptoneDatabase
from .recommendation_engine import (
    PeptoneRecommender, RecommendationResult,
    SCORING_WEIGHTS, OPTIMAL_MW_PROFILES
)
from .blend_optimizer import BlendOptimizer, BlendOptimizationResult
from .kegg_connector import KEGGConnector, OrganismPathways
from .utils import normalize_score


class EnhancedPeptoneRecommender(PeptoneRecommender):
    """Enhanced recommender with KEGG integration and advanced optimization"""

    def __init__(self,
                 strain_db: StrainDatabase,
                 peptone_db: PeptoneDatabase,
                 use_kegg: bool = True,
                 kegg_connector: Optional[KEGGConnector] = None,
                 kegg_cache_only: bool = False):
        """
        Initialize enhanced recommender

        Args:
            strain_db: Strain database
            peptone_db: Peptone database
            use_kegg: Whether to use KEGG pathway data
            kegg_connector: Optional KEGGConnector instance
            kegg_cache_only: If True, only use cached KEGG data (no API calls)
        """
        super().__init__(strain_db, peptone_db)

        self.use_kegg = use_kegg
        self.kegg_cache_only = kegg_cache_only
        self.kegg_connector = kegg_connector or KEGGConnector() if use_kegg else None
        self.blend_optimizer = BlendOptimizer()

        # Cache for organism pathways
        self._pathway_cache: Dict[str, OrganismPathways] = {}

    def recommend_with_pathways(self,
                                strain_id: str,
                                top_n: int = 5,
                                sempio_only: bool = True) -> List[RecommendationResult]:
        """
        Recommend with KEGG pathway analysis

        Args:
            strain_id: Strain identifier
            top_n: Number of recommendations
            sempio_only: Only recommend Sempio products

        Returns:
            List of recommendations with pathway-based scoring
        """
        strain = self.strain_db.get_strain_by_id(strain_id)
        if not strain:
            raise ValueError(f"Strain not found: {strain_id}")

        # Get pathway information if available
        pathway_requirements = None
        if self.use_kegg and self.kegg_connector and not strain.is_nda:
            pathway_requirements = self._get_pathway_requirements(strain)

        # Get candidate peptones
        candidates = (self.peptone_db.get_sempio_peptones()
                     if sempio_only else self.peptone_db.peptones)

        # Score each peptone
        results = []
        for peptone in candidates:
            score, detailed = self._calculate_enhanced_score(
                strain, peptone, pathway_requirements
            )

            rec = RecommendationResult(
                strain=strain,
                peptones=[peptone],
                ratios=[1.0],
                overall_score=score,
                detailed_scores=detailed,
                rationale=self._generate_enhanced_rationale(
                    strain, [peptone], [1.0], detailed, pathway_requirements
                )
            )
            results.append(rec)

        # Sort by score
        results.sort(key=lambda x: x.overall_score, reverse=True)

        return results[:top_n]

    def recommend_optimized_blend(self,
                                 strain_id: str,
                                 max_components: int = 3,
                                 top_n: int = 5,
                                 sempio_only: bool = True,
                                 use_optimizer: bool = True) -> List[RecommendationResult]:
        """
        Recommend optimized blends using scipy optimization

        Args:
            strain_id: Strain identifier
            max_components: Maximum components in blend
            top_n: Number of recommendations
            sempio_only: Only Sempio products
            use_optimizer: Use scipy optimizer for ratio optimization

        Returns:
            List of optimized blend recommendations
        """
        strain = self.strain_db.get_strain_by_id(strain_id)
        if not strain:
            raise ValueError(f"Strain not found: {strain_id}")

        # Get pathway requirements if available
        pathway_requirements = None
        if self.use_kegg and self.kegg_connector and not strain.is_nda:
            pathway_requirements = self._get_pathway_requirements(strain)

        # Get top single peptones as base
        single_recs = self.recommend_with_pathways(
            strain_id, top_n=min(6, top_n + 1), sempio_only=sempio_only
        )
        top_peptones = [r.peptones[0] for r in single_recs]

        all_results = []

        # Generate blends using complementary peptones
        for base_peptone in top_peptones[:3]:
            # Find complementary peptones
            complementary = self.blend_optimizer.find_complementary_peptones(
                base_peptone,
                [p for p in top_peptones if p.name != base_peptone.name],
                top_n=min(3, max_components - 1)
            )

            for comp_peptone, _ in complementary:
                if max_components >= 2:
                    # 2-component blend
                    blend_peptones = [base_peptone, comp_peptone]

                    if use_optimizer:
                        # Optimize ratios
                        opt_result = self._optimize_blend_for_strain(
                            strain, blend_peptones, pathway_requirements
                        )

                        if opt_result.success:
                            rec = self._create_recommendation_from_optimization(
                                strain, opt_result, pathway_requirements
                            )
                            all_results.append(rec)
                    else:
                        # Use predefined ratios
                        for ratio1 in [0.4, 0.5, 0.6, 0.7]:
                            ratio2 = 1.0 - ratio1
                            score, detailed = self._evaluate_blend_enhanced(
                                strain, blend_peptones, [ratio1, ratio2],
                                pathway_requirements
                            )

                            rec = RecommendationResult(
                                strain=strain,
                                peptones=blend_peptones,
                                ratios=[ratio1, ratio2],
                                overall_score=score,
                                detailed_scores=detailed,
                                rationale=self._generate_enhanced_rationale(
                                    strain, blend_peptones, [ratio1, ratio2],
                                    detailed, pathway_requirements
                                )
                            )
                            all_results.append(rec)

                if max_components >= 3 and len(complementary) >= 2:
                    # 3-component blend
                    third_peptone = complementary[1][0]
                    blend_peptones = [base_peptone, comp_peptone, third_peptone]

                    if use_optimizer:
                        opt_result = self._optimize_blend_for_strain(
                            strain, blend_peptones, pathway_requirements
                        )

                        if opt_result.success:
                            rec = self._create_recommendation_from_optimization(
                                strain, opt_result, pathway_requirements
                            )
                            all_results.append(rec)

        # Sort and return top results
        all_results.sort(key=lambda x: x.overall_score, reverse=True)
        return all_results[:top_n]

    def _get_pathway_requirements(self, strain: StrainProfile) -> Optional[Dict[str, str]]:
        """Get pathway-based nutritional requirements"""
        if not self.kegg_connector:
            return None

        # Check cache
        cache_key = f"{strain.genus}_{strain.species}"
        if cache_key in self._pathway_cache:
            org_pathways = self._pathway_cache[cache_key]
        else:
            # If cache-only mode, try to load from disk cache without API calls
            if self.kegg_cache_only:
                # Try to find organism code from cache
                org_code = self._try_load_from_cache(strain.genus, strain.species)
                if not org_code:
                    return None

                # Try to load pathways from cache
                org_pathways = self._try_load_pathways_from_cache(org_code)
                if not org_pathways:
                    return None
            else:
                # Normal mode: Use API calls
                # Find organism in KEGG
                org_code = self.kegg_connector.find_organism(strain.genus, strain.species)
                if not org_code:
                    return None

                # Get pathways
                org_pathways = self.kegg_connector.get_organism_pathways(org_code)
                if not org_pathways:
                    return None

            # Cache result in memory
            self._pathway_cache[cache_key] = org_pathways

        # Infer requirements
        return self.kegg_connector.infer_nutritional_requirements(org_pathways)

    def _try_load_from_cache(self, genus: str, species: str) -> Optional[str]:
        """Try to load organism code from disk cache only"""
        cache_key = f"organism_{genus}_{species}"
        cached = self.kegg_connector._load_cache(cache_key)
        if cached:
            return cached.get('organism_code')
        return None

    def _try_load_pathways_from_cache(self, org_code: str) -> Optional[OrganismPathways]:
        """Try to load pathways from disk cache only"""
        cache_key = f"pathways_{org_code}"
        cached = self.kegg_connector._load_cache(cache_key)

        if cached:
            # Reconstruct from cache
            from datetime import datetime
            org_pathways = OrganismPathways(
                organism_code=cached['organism_code'],
                organism_name=cached['organism_name'],
                retrieved_at=datetime.fromisoformat(cached['retrieved_at'])
            )
            from .kegg_connector import PathwayInfo
            for pid, pdata in cached['pathways'].items():
                org_pathways.pathways[pid] = PathwayInfo(**pdata)
            return org_pathways

        return None

    def _calculate_enhanced_score(self,
                                  strain: StrainProfile,
                                  peptone: PeptoneProduct,
                                  pathway_requirements: Optional[Dict[str, str]]) -> Tuple[float, Dict[str, float]]:
        """Calculate fitness score with pathway data"""
        # Start with base score
        base_score, detailed = self.calculate_fitness_score(strain, peptone)

        # If pathway data available, adjust score
        if pathway_requirements:
            pathway_bonus = self._calculate_pathway_bonus(peptone, pathway_requirements)
            base_score = base_score * (1.0 + pathway_bonus * 0.15)  # Up to 15% bonus
            detailed['pathway_match'] = pathway_bonus

        return normalize_score(base_score), detailed

    def _calculate_pathway_bonus(self,
                                peptone: PeptoneProduct,
                                pathway_requirements: Dict[str, str]) -> float:
        """Calculate bonus based on pathway requirements"""
        bonus = 0.0
        count = 0

        # Check amino acid requirements
        for aa_name in ['Threonine', 'Methionine', 'Lysine', 'Tryptophan']:
            req_key = f'{aa_name}_requirement'
            if req_key in pathway_requirements:
                requirement_level = pathway_requirements[req_key]

                # Check if peptone provides this amino acid
                faa_key = f'faa_{aa_name}'
                taa_key = f'taa_{aa_name}'

                faa_amount = peptone.profile.free_amino_acids.get(faa_key, 0)
                taa_amount = peptone.profile.total_amino_acids.get(taa_key, 0)

                if requirement_level == 'high':
                    # Need high amounts
                    if faa_amount > 0.5 or taa_amount > 2.0:
                        bonus += 1.0
                    elif faa_amount > 0.2 or taa_amount > 1.0:
                        bonus += 0.5
                elif requirement_level == 'medium':
                    if faa_amount > 0.2 or taa_amount > 1.0:
                        bonus += 0.7
                    elif faa_amount > 0.1 or taa_amount > 0.5:
                        bonus += 0.3

                count += 1

        # Check vitamin requirement
        if 'vitamin_requirement' in pathway_requirements:
            vitamin_total = sum(peptone.profile.vitamins.values())
            req_level = pathway_requirements['vitamin_requirement']

            if req_level == 'high' and vitamin_total > 5:
                bonus += 1.0
            elif req_level == 'medium' and vitamin_total > 2:
                bonus += 0.5

            count += 1

        # Normalize
        return bonus / count if count > 0 else 0.0

    def _optimize_blend_for_strain(self,
                                   strain: StrainProfile,
                                   peptones: List[PeptoneProduct],
                                   pathway_requirements: Optional[Dict[str, str]]) -> BlendOptimizationResult:
        """Optimize blend ratios for a strain"""

        def scoring_function(s, peps, ratios):
            score, _ = self._evaluate_blend_enhanced(s, peps, ratios, pathway_requirements)
            return score

        return self.blend_optimizer.optimize_for_strain(
            peptones, strain, scoring_function, method='SLSQP'
        )

    def _evaluate_blend_enhanced(self,
                                strain: StrainProfile,
                                peptones: List[PeptoneProduct],
                                ratios: List[float],
                                pathway_requirements: Optional[Dict[str, str]]) -> Tuple[float, Dict[str, float]]:
        """Evaluate blend with pathway consideration"""
        # Use base evaluation
        base_score, detailed = self._evaluate_blend(strain, peptones, ratios)

        # Add pathway bonus if available
        if pathway_requirements:
            # Calculate weighted pathway bonus
            total_bonus = 0.0
            for peptone, ratio in zip(peptones, ratios):
                bonus = self._calculate_pathway_bonus(peptone, pathway_requirements)
                total_bonus += bonus * ratio

            base_score = base_score * (1.0 + total_bonus * 0.15)
            detailed['pathway_match'] = total_bonus

        return normalize_score(base_score), detailed

    def _create_recommendation_from_optimization(self,
                                                strain: StrainProfile,
                                                opt_result: BlendOptimizationResult,
                                                pathway_requirements: Optional[Dict[str, str]]) -> RecommendationResult:
        """Create recommendation from optimization result"""
        score, detailed = self._evaluate_blend_enhanced(
            strain,
            opt_result.peptones,
            opt_result.optimal_ratios,
            pathway_requirements
        )

        return RecommendationResult(
            strain=strain,
            peptones=opt_result.peptones,
            ratios=opt_result.optimal_ratios,
            overall_score=score,
            detailed_scores=detailed,
            rationale=self._generate_enhanced_rationale(
                strain,
                opt_result.peptones,
                opt_result.optimal_ratios,
                detailed,
                pathway_requirements
            )
        )

    def _generate_enhanced_rationale(self,
                                    strain: StrainProfile,
                                    peptones: List[PeptoneProduct],
                                    ratios: List[float],
                                    detailed_scores: Dict[str, float],
                                    pathway_requirements: Optional[Dict[str, str]]) -> str:
        """Generate rationale with pathway information"""
        # Start with base rationale
        rationale_parts = []

        # Identify strengths
        strengths = []
        if detailed_scores.get('amino_acid_match', 0) > 0.7:
            strengths.append("excellent amino acid profile")
        if detailed_scores.get('growth_factor_match', 0) > 0.7:
            strengths.append("rich in growth factors")
        if detailed_scores.get('nutritional_match', 0) > 0.7:
            strengths.append("optimal nitrogen content")

        if 'pathway_match' in detailed_scores and detailed_scores['pathway_match'] > 0.5:
            strengths.append("matches metabolic pathway requirements")

        if strengths:
            rationale_parts.append("Strengths: " + ", ".join(strengths))

        # Complementarity
        if len(peptones) > 1:
            materials = set(p.raw_material for p in peptones)
            if len(materials) > 1:
                rationale_parts.append(f"Complementary sources: {', '.join(materials)}")

        # Pathway-specific notes
        if pathway_requirements:
            high_req = [k.replace('_requirement', '') for k, v in pathway_requirements.items()
                       if v == 'high']
            if high_req:
                rationale_parts.append(f"Addresses requirements: {', '.join(high_req[:3])}")

        return "; ".join(rationale_parts) if rationale_parts else "Good overall match"


if __name__ == "__main__":
    print("Testing Enhanced Recommendation Engine...")

    from pathlib import Path

    strain_file = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
    peptone_file = Path(r"D:\folder1\composition_template.xlsx")

    if strain_file.exists() and peptone_file.exists():
        # Load databases
        strain_db = StrainDatabase()
        peptone_db = PeptoneDatabase()

        strain_db.load_from_excel(str(strain_file))
        peptone_db.load_from_excel(str(peptone_file))

        # Create enhanced recommender (without KEGG for testing)
        recommender = EnhancedPeptoneRecommender(
            strain_db, peptone_db, use_kegg=False
        )

        print("\n" + "="*80)
        print("Testing Optimized Blend Recommendations")
        print("="*80)

        recs = recommender.recommend_optimized_blend(
            "KCCM 12116",
            max_components=3,
            top_n=3,
            sempio_only=True,
            use_optimizer=True
        )

        for i, rec in enumerate(recs, 1):
            print(f"\n{i}. {rec.get_description()}")
            print(f"   Score: {rec.overall_score:.3f}")
            print(f"   Rationale: {rec.rationale}")

    else:
        print("Data files not found. Skipping test.")

    print("\n\nEnhanced recommender test complete!")
