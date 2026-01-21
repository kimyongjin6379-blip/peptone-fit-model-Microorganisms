"""
Blend Optimizer Module

Optimizes peptone blend ratios using scipy optimization algorithms
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from typing import List, Tuple, Dict, Callable, Optional
from dataclasses import dataclass

from .peptone_analyzer import PeptoneProduct, NutritionalProfile
from .strain_manager import StrainProfile


@dataclass
class BlendOptimizationResult:
    """Result of blend optimization"""

    peptones: List[PeptoneProduct]
    optimal_ratios: List[float]
    final_score: float
    optimization_method: str
    iterations: int
    success: bool
    message: str = ""

    def get_description(self) -> str:
        """Get human-readable description"""
        parts = []
        for pep, ratio in zip(self.peptones, self.optimal_ratios):
            parts.append(f"{pep.name} {ratio*100:.1f}%")
        return " + ".join(parts)


class BlendOptimizer:
    """Optimizes peptone blend ratios"""

    def __init__(self,
                 min_ratio: float = 0.1,
                 max_ratio: float = 0.8):
        """
        Initialize blend optimizer

        Args:
            min_ratio: Minimum ratio for each component (default 0.1 = 10%)
            max_ratio: Maximum ratio for each component (default 0.8 = 80%)
        """
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio

    def optimize_ratio(self,
                      peptones: List[PeptoneProduct],
                      target_profile: Dict[str, float],
                      weights: Optional[Dict[str, float]] = None,
                      method: str = 'SLSQP',
                      initial_ratios: Optional[List[float]] = None) -> BlendOptimizationResult:
        """
        Optimize blend ratios to match target nutritional profile

        Args:
            peptones: List of peptones to blend
            target_profile: Target nutritional profile
            weights: Optional weights for different nutrients
            method: Optimization method ('SLSQP', 'differential_evolution')
            initial_ratios: Initial guess for ratios

        Returns:
            BlendOptimizationResult object
        """
        n_peptones = len(peptones)

        if n_peptones < 2:
            raise ValueError("Need at least 2 peptones for blending")

        if n_peptones > 5:
            raise ValueError("Maximum 5 peptones supported")

        # Extract feature vectors from peptones
        peptone_vectors = [self._extract_features(p) for p in peptones]
        target_vector = self._dict_to_vector(target_profile)

        # Set default weights if not provided
        if weights is None:
            weights = {k: 1.0 for k in target_profile.keys()}

        weight_vector = self._dict_to_vector(weights)

        # Define objective function
        def objective(ratios):
            """Calculate deviation from target profile"""
            # Create blended profile
            blended = np.zeros_like(target_vector)
            for i, ratio in enumerate(ratios):
                if i < len(peptone_vectors):
                    blended += ratio * peptone_vectors[i]

            # Calculate weighted euclidean distance
            diff = (blended - target_vector) * weight_vector
            return np.sum(diff ** 2)

        # Define constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}  # Sum = 1.0
        ]

        # Define bounds
        bounds = [(self.min_ratio, self.max_ratio) for _ in range(n_peptones)]

        # Initial guess
        if initial_ratios is None:
            initial_ratios = [1.0 / n_peptones] * n_peptones

        # Optimize
        if method.upper() == 'SLSQP':
            result = minimize(
                objective,
                initial_ratios,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-6}
            )

            return BlendOptimizationResult(
                peptones=peptones,
                optimal_ratios=result.x.tolist(),
                final_score=float(result.fun),
                optimization_method='SLSQP',
                iterations=result.nit if hasattr(result, 'nit') else 0,
                success=result.success,
                message=result.message if hasattr(result, 'message') else ""
            )

        elif method.upper() == 'DIFFERENTIAL_EVOLUTION':
            # Use differential evolution (global optimizer)
            def constraint_penalty(ratios):
                """Add penalty for constraint violation"""
                penalty = 0.0
                sum_penalty = abs(np.sum(ratios) - 1.0) * 1000
                penalty += sum_penalty
                return objective(ratios) + penalty

            result = differential_evolution(
                constraint_penalty,
                bounds,
                maxiter=500,
                popsize=15,
                tol=1e-6,
                seed=42
            )

            # Normalize to ensure sum = 1.0
            optimal = result.x / np.sum(result.x)

            return BlendOptimizationResult(
                peptones=peptones,
                optimal_ratios=optimal.tolist(),
                final_score=float(result.fun),
                optimization_method='Differential Evolution',
                iterations=result.nit if hasattr(result, 'nit') else 0,
                success=result.success,
                message=result.message if hasattr(result, 'message') else ""
            )

        else:
            raise ValueError(f"Unknown optimization method: {method}")

    def optimize_for_strain(self,
                           peptones: List[PeptoneProduct],
                           strain: StrainProfile,
                           scoring_function: Callable,
                           method: str = 'SLSQP') -> BlendOptimizationResult:
        """
        Optimize blend to maximize fitness score for a strain

        Args:
            peptones: List of peptones to blend
            strain: Target strain
            scoring_function: Function(strain, peptone_list, ratios) -> score
            method: Optimization method

        Returns:
            BlendOptimizationResult object
        """
        n_peptones = len(peptones)

        # Define objective (negative score since we minimize)
        def objective(ratios):
            score = scoring_function(strain, peptones, ratios)
            return -score  # Negative because we minimize

        # Constraints and bounds
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}
        ]
        bounds = [(self.min_ratio, self.max_ratio) for _ in range(n_peptones)]

        # Initial guess - equal ratios
        initial = [1.0 / n_peptones] * n_peptones

        # Optimize
        if method.upper() == 'SLSQP':
            result = minimize(
                objective,
                initial,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-6}
            )

            return BlendOptimizationResult(
                peptones=peptones,
                optimal_ratios=result.x.tolist(),
                final_score=-float(result.fun),  # Convert back to positive
                optimization_method='SLSQP',
                iterations=result.nit if hasattr(result, 'nit') else 0,
                success=result.success,
                message=result.message if hasattr(result, 'message') else ""
            )

        else:
            raise ValueError(f"Unknown optimization method: {method}")

    def find_complementary_peptones(self,
                                   base_peptone: PeptoneProduct,
                                   candidates: List[PeptoneProduct],
                                   top_n: int = 3) -> List[Tuple[PeptoneProduct, float]]:
        """
        Find peptones that complement the base peptone

        Args:
            base_peptone: Base peptone
            candidates: Candidate peptones
            top_n: Number of results

        Returns:
            List of (peptone, complementarity_score) tuples
        """
        base_vector = self._extract_features(base_peptone)

        complementarity_scores = []

        for candidate in candidates:
            if candidate.name == base_peptone.name:
                continue

            cand_vector = self._extract_features(candidate)

            # Complementarity = diversity + coverage
            # Diversity: how different the profiles are
            diversity = np.linalg.norm(base_vector - cand_vector)

            # Coverage: whether candidate fills gaps in base
            base_low = base_vector < 0.3  # Identify weak areas in base
            cand_coverage = np.mean(cand_vector[base_low]) if np.any(base_low) else 0

            complementarity = diversity * 0.6 + cand_coverage * 0.4

            complementarity_scores.append((candidate, complementarity))

        # Sort by complementarity
        complementarity_scores.sort(key=lambda x: x[1], reverse=True)

        return complementarity_scores[:top_n]

    def evaluate_blend(self,
                      peptones: List[PeptoneProduct],
                      ratios: List[float],
                      target_profile: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Evaluate a peptone blend

        Args:
            peptones: List of peptones
            ratios: Mixing ratios
            target_profile: Optional target profile for comparison

        Returns:
            Dictionary with evaluation metrics
        """
        # Create blended profile
        blended = self._create_blended_profile(peptones, ratios)

        metrics = {
            'total_nitrogen': blended.general.get('general_TN', 0),
            'amino_nitrogen': blended.general.get('general_AN', 0),
            'essential_aa_ratio': blended.get_essential_aa_ratio(),
            'free_aa_ratio': blended.get_free_aa_ratio(),
            'bcaa_ratio': blended.get_bcaa_ratio(),
            'nucleotide_total': sum(blended.nucleotides.values()),
            'vitamin_total': sum(blended.vitamins.values()),
        }

        if target_profile:
            # Calculate deviation from target
            target_vector = self._dict_to_vector(target_profile)
            blended_vector = self._extract_features_from_profile(blended)
            deviation = np.linalg.norm(blended_vector - target_vector)
            metrics['target_deviation'] = float(deviation)

        return metrics

    def _extract_features(self, peptone: PeptoneProduct) -> np.ndarray:
        """Extract numerical features from peptone"""
        features = []

        # General composition
        features.extend([
            peptone.profile.general.get('general_TN', 0) / 100.0,
            peptone.profile.general.get('general_AN', 0) / 20.0,
        ])

        # Amino acid ratios
        features.extend([
            peptone.profile.get_essential_aa_ratio(),
            peptone.profile.get_free_aa_ratio(),
            peptone.profile.get_bcaa_ratio(),
        ])

        # Growth factors (normalized)
        features.append(sum(peptone.profile.nucleotides.values()) / 30.0)
        features.append(sum(peptone.profile.vitamins.values()) / 15.0)

        return np.array(features)

    def _extract_features_from_profile(self, profile: NutritionalProfile) -> np.ndarray:
        """Extract features from nutritional profile"""
        features = []

        features.extend([
            profile.general.get('general_TN', 0) / 100.0,
            profile.general.get('general_AN', 0) / 20.0,
        ])

        features.extend([
            profile.get_essential_aa_ratio(),
            profile.get_free_aa_ratio(),
            profile.get_bcaa_ratio(),
        ])

        features.append(sum(profile.nucleotides.values()) / 30.0)
        features.append(sum(profile.vitamins.values()) / 15.0)

        return np.array(features)

    def _dict_to_vector(self, d: Dict[str, float]) -> np.ndarray:
        """Convert dictionary to numpy array"""
        return np.array(list(d.values()))

    def _create_blended_profile(self,
                                peptones: List[PeptoneProduct],
                                ratios: List[float]) -> NutritionalProfile:
        """
        Create a blended nutritional profile

        Args:
            peptones: List of peptones
            ratios: Mixing ratios

        Returns:
            Blended NutritionalProfile
        """
        from copy import deepcopy

        # Start with empty profile
        blended = NutritionalProfile()

        # Categories to blend
        categories = [
            'general', 'sugars', 'minerals', 'nucleotides',
            'organic_acids', 'vitamins', 'molecular_weight',
            'total_amino_acids', 'free_amino_acids'
        ]

        for category in categories:
            blended_dict = {}

            # Get all keys from all peptones
            all_keys = set()
            for peptone in peptones:
                cat_dict = getattr(peptone.profile, category)
                all_keys.update(cat_dict.keys())

            # Blend each component
            for key in all_keys:
                blended_value = 0.0
                for peptone, ratio in zip(peptones, ratios):
                    cat_dict = getattr(peptone.profile, category)
                    blended_value += cat_dict.get(key, 0.0) * ratio

                blended_dict[key] = blended_value

            setattr(blended, category, blended_dict)

        return blended


if __name__ == "__main__":
    # Test blend optimizer
    print("Testing blend optimizer...")

    # This would normally use real peptone data
    # For now, just test the optimization logic

    from .peptone_analyzer import PeptoneDatabase
    from pathlib import Path

    peptone_file = Path(r"D:\folder1\composition_template.xlsx")
    if peptone_file.exists():
        print("\nLoading peptone database...")
        db = PeptoneDatabase()
        db.load_from_excel(str(peptone_file))

        # Get Sempio peptones
        sempio = db.get_sempio_peptones()
        print(f"Loaded {len(sempio)} Sempio peptones")

        if len(sempio) >= 3:
            # Test optimization
            print("\n" + "="*80)
            print("Testing blend optimization")
            print("="*80)

            optimizer = BlendOptimizer()

            # Use first 3 peptones
            test_peptones = sempio[:3]
            print(f"\nOptimizing blend of:")
            for p in test_peptones:
                print(f"  - {p.name}")

            # Create target profile (e.g., high AN, high free AA)
            target = {
                'TN': 0.8,
                'AN': 0.8,
                'essential_aa': 0.7,
                'free_aa': 0.6,
                'bcaa': 0.5,
                'nucleotide': 0.4,
                'vitamin': 0.3,
            }

            result = optimizer.optimize_ratio(
                test_peptones,
                target,
                method='SLSQP'
            )

            print(f"\nOptimization result:")
            print(f"  Method: {result.optimization_method}")
            print(f"  Success: {result.success}")
            print(f"  Iterations: {result.iterations}")
            print(f"  Final score: {result.final_score:.6f}")
            print(f"\nOptimal blend:")
            for pep, ratio in zip(result.peptones, result.optimal_ratios):
                print(f"  {pep.name:15} {ratio*100:6.2f}%")

            # Test complementary peptones
            print("\n" + "="*80)
            print("Finding complementary peptones")
            print("="*80)

            base = sempio[0]
            complementary = optimizer.find_complementary_peptones(
                base,
                sempio[1:],
                top_n=3
            )

            print(f"\nPeptones complementary to {base.name}:")
            for pep, score in complementary:
                print(f"  {pep.name:15} Score: {score:.3f}")

    else:
        print("Test data not found. Skipping tests.")

    print("\n\nBlend optimizer test complete!")
