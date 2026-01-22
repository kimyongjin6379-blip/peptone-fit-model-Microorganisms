"""
Utility Functions

Common helper functions used across modules
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from sklearn.preprocessing import MinMaxScaler


def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Normalize a score to a range

    Args:
        score: Input score
        min_val: Minimum value (default 0.0)
        max_val: Maximum value (default 1.0)

    Returns:
        Normalized score
    """
    return max(min_val, min(max_val, score))


def calculate_euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate Euclidean distance between two vectors"""
    return float(np.linalg.norm(vec1 - vec2))


def calculate_deviation(target: Dict[str, float],
                       actual: Dict[str, float],
                       weights: Optional[Dict[str, float]] = None) -> float:
    """
    Calculate weighted deviation between target and actual values

    Args:
        target: Target values
        actual: Actual values
        weights: Optional weights for each component

    Returns:
        Weighted deviation score (0 = perfect match, higher = more deviation)
    """
    if not target:
        return 0.0

    deviations = []
    total_weight = 0.0

    for key, target_val in target.items():
        actual_val = actual.get(key, 0.0)
        weight = weights.get(key, 1.0) if weights else 1.0

        # Calculate relative deviation
        if target_val > 0:
            deviation = abs(actual_val - target_val) / target_val
        else:
            deviation = abs(actual_val - target_val)

        deviations.append(deviation * weight)
        total_weight += weight

    return sum(deviations) / total_weight if total_weight > 0 else 0.0


def is_incomplete_pathway(pathway_data: Dict[str, Any]) -> bool:
    """
    Check if a metabolic pathway is incomplete

    Args:
        pathway_data: Pathway information from KEGG

    Returns:
        True if pathway is incomplete or missing key genes
    """
    # This is a placeholder - actual implementation would analyze KEGG data
    # For now, we assume all pathways are complete
    return False


def create_comparison_table(items: List[Any],
                           attributes: List[str],
                           item_name_attr: str = 'name') -> pd.DataFrame:
    """
    Create a comparison table for items

    Args:
        items: List of items to compare
        attributes: List of attribute names to include
        item_name_attr: Attribute name for item name

    Returns:
        DataFrame with comparison
    """
    data = []
    for item in items:
        row = {item_name_attr: getattr(item, item_name_attr, str(item))}
        for attr in attributes:
            if hasattr(item, attr):
                value = getattr(item, attr)
                if callable(value):
                    value = value()
                row[attr] = value
            else:
                row[attr] = None
        data.append(row)

    return pd.DataFrame(data)


def format_recommendation_report(recommendations: List[Dict[str, Any]],
                                title: str = "Recommendation Report") -> str:
    """
    Format recommendation results as a text report

    Args:
        recommendations: List of recommendation dictionaries
        title: Report title

    Returns:
        Formatted report string
    """
    report = f"\n{'='*80}\n"
    report += f"{title:^80}\n"
    report += f"{'='*80}\n\n"

    for i, rec in enumerate(recommendations, 1):
        report += f"{i}. {rec.get('name', 'Unknown')}\n"
        report += f"   Score: {rec.get('score', 0):.3f}\n"

        if 'composition' in rec:
            report += f"   Composition:\n"
            for comp in rec['composition']:
                report += f"     - {comp['peptone']:15} {comp['ratio']*100:5.1f}%\n"

        if 'rationale' in rec:
            report += f"   Rationale: {rec['rationale']}\n"

        report += "\n"

    return report


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division fails

    Returns:
        Result of division or default
    """
    if denominator == 0 or pd.isna(denominator):
        return default
    return numerator / denominator


def calculate_weighted_average(values: Dict[str, float],
                               weights: Dict[str, float]) -> float:
    """
    Calculate weighted average

    Args:
        values: Dictionary of values
        weights: Dictionary of weights

    Returns:
        Weighted average
    """
    if not values or not weights:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0

    for key, value in values.items():
        weight = weights.get(key, 0.0)
        weighted_sum += value * weight
        total_weight += weight

    return weighted_sum / total_weight if total_weight > 0 else 0.0


def extract_numeric_features(data_dict: Dict[str, Any],
                            prefix: Optional[str] = None) -> np.ndarray:
    """
    Extract numeric features from a dictionary

    Args:
        data_dict: Dictionary with mixed types
        prefix: Optional prefix to filter keys

    Returns:
        NumPy array of numeric values
    """
    values = []

    for key, value in data_dict.items():
        if prefix and not key.startswith(prefix):
            continue

        if isinstance(value, (int, float)) and not pd.isna(value):
            values.append(float(value))

    return np.array(values)


def create_feature_matrix(items: List[Any],
                         feature_extractor_func) -> np.ndarray:
    """
    Create feature matrix from list of items

    Args:
        items: List of items
        feature_extractor_func: Function to extract features from each item

    Returns:
        2D NumPy array (n_items, n_features)
    """
    features = []
    for item in items:
        feature_vec = feature_extractor_func(item)
        features.append(feature_vec)

    return np.array(features)


def normalize_features(features: np.ndarray,
                      method: str = 'minmax') -> np.ndarray:
    """
    Normalize feature matrix

    Args:
        features: Feature matrix
        method: Normalization method ('minmax' or 'standard')

    Returns:
        Normalized features
    """
    if method == 'minmax':
        scaler = MinMaxScaler()
    elif method == 'standard':
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    return scaler.fit_transform(features)


class ProgressTracker:
    """Simple progress tracker for long operations"""

    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description

    def update(self, amount: int = 1):
        """Update progress"""
        self.current += amount
        percentage = (self.current / self.total) * 100
        print(f"\r{self.description}: {self.current}/{self.total} ({percentage:.1f}%)",
              end='', flush=True)

    def finish(self):
        """Finish progress tracking"""
        print()  # New line


if __name__ == "__main__":
    # Test utility functions
    print("Testing utility functions...")

    # Test normalize_score
    assert normalize_score(0.5) == 0.5
    assert normalize_score(1.5) == 1.0
    assert normalize_score(-0.5) == 0.0
    print("[OK] normalize_score")

    # Test safe_divide
    assert safe_divide(10, 2) == 5.0
    assert safe_divide(10, 0) == 0.0
    assert safe_divide(10, 0, default=1.0) == 1.0
    print("[OK] safe_divide")

    # Test calculate_weighted_average
    values = {'a': 10, 'b': 20, 'c': 30}
    weights = {'a': 1, 'b': 2, 'c': 3}
    avg = calculate_weighted_average(values, weights)
    expected = (10*1 + 20*2 + 30*3) / (1+2+3)
    assert abs(avg - expected) < 0.01
    print("[OK] calculate_weighted_average")

    # Test extract_numeric_features
    data = {'a': 1.0, 'b': 2.0, 'c': 'text', 'd': 3.0}
    features = extract_numeric_features(data)
    assert len(features) == 3
    print("[OK] extract_numeric_features")

    print("\nAll tests passed!")
