"""
Peptone Analyzer Module

Manages peptone composition data including:
- Loading peptone composition from Excel/CSV
- Data preprocessing and missing value handling
- Nutritional profile generation
- Similarity calculations
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler


# Nutritional component categories
COMPONENT_CATEGORIES = {
    'general': [
        'general_TN', 'general_AN', 'general_total_sugar',
        'general_reducing_sugar', 'general_ash', 'general_moisture',
        'general_crude_fat', 'general_salinity'
    ],
    'sugars': [
        'sugar_Fructose', 'sugar_Glucose', 'sugar_Sucrose',
        'sugar_Lactose', 'sugar_Maltose'
    ],
    'minerals': [
        'mineral_Na', 'mineral_K', 'mineral_Mg', 'mineral_Ca'
    ],
    'nucleotides': [
        'nucleotide_AMP', 'nucleotide_GMP', 'nucleotide_UMP',
        'nucleotide_IMP', 'nucleotide_CMP', 'nucleotide_Hypoxanthine'
    ],
    'organic_acids': [
        'orgacid_Citric', 'orgacid_Malic', 'orgacid_Succinic',
        'orgacid_Lactic', 'orgacid_Acetic'
    ],
    'vitamins': [
        'vitB_B1', 'vitB_B2', 'vitB_B3', 'vitB_B6', 'vitB_B9'
    ],
    'molecular_weight': [
        'mw_avg_Da', 'mw_pct_lt250Da', 'mw_pct_250_500Da',
        'mw_pct_500_750Da', 'mw_pct_750_1000Da', 'mw_pct_gt1000Da'
    ],
    'total_amino_acids': [
        'taa_Aspartic acid', 'taa_Hydroxyproline', 'taa_Threonine',
        'taa_Serine', 'taa_Asparagine', 'taa_Glutamic acid',
        'taa_Glutamine', 'taa_Cysteine', 'taa_Proline', 'taa_Glycine',
        'taa_Alanine', 'taa_Citruline', 'taa_Valine', 'taa_Cystine',
        'taa_Methionine', 'taa_Isoleucine', 'taa_Leucine', 'taa_Tyrosine',
        'taa_Phenylalanine', 'taa_GABA', 'taa_Histidine', 'taa_Tryptophan',
        'taa_Ornithine', 'taa_Lysine', 'taa_Arginine'
    ],
    'free_amino_acids': [
        'faa_Aspartic acid', 'faa_Hydroxyproline', 'faa_Threonine',
        'faa_Serine', 'faa_Asparagine', 'faa_Glutamic acid',
        'faa_Glutamine', 'faa_Cysteine', 'faa_Proline', 'faa_Glycine',
        'faa_Alanine', 'faa_Citruline', 'faa_Valine', 'faa_Cystine',
        'faa_Methionine', 'faa_Isoleucine', 'faa_Leucine', 'faa_Tyrosine',
        'faa_Phenylalanine', 'faa_GABA', 'faa_Histidine', 'faa_Tryptophan',
        'faa_Ornithine', 'faa_Lysine', 'faa_Arginine'
    ]
}

# Essential amino acids
ESSENTIAL_AMINO_ACIDS = [
    'Threonine', 'Valine', 'Methionine', 'Isoleucine',
    'Leucine', 'Phenylalanine', 'Tryptophan', 'Lysine', 'Histidine'
]

# Branched-chain amino acids
BCAA = ['Valine', 'Leucine', 'Isoleucine']


@dataclass
class NutritionalProfile:
    """Nutritional profile of a peptone"""

    general: Dict[str, float] = field(default_factory=dict)
    sugars: Dict[str, float] = field(default_factory=dict)
    minerals: Dict[str, float] = field(default_factory=dict)
    nucleotides: Dict[str, float] = field(default_factory=dict)
    organic_acids: Dict[str, float] = field(default_factory=dict)
    vitamins: Dict[str, float] = field(default_factory=dict)
    molecular_weight: Dict[str, float] = field(default_factory=dict)
    total_amino_acids: Dict[str, float] = field(default_factory=dict)
    free_amino_acids: Dict[str, float] = field(default_factory=dict)

    def get_essential_aa_ratio(self) -> float:
        """Calculate ratio of essential amino acids to total amino acids"""
        total = sum(self.total_amino_acids.values()) or 1.0
        essential = sum(
            self.total_amino_acids.get(f'taa_{aa}', 0)
            for aa in ESSENTIAL_AMINO_ACIDS
        )
        return essential / total

    def get_bcaa_ratio(self) -> float:
        """Calculate ratio of BCAA to total amino acids"""
        total = sum(self.total_amino_acids.values()) or 1.0
        bcaa = sum(
            self.total_amino_acids.get(f'taa_{aa}', 0)
            for aa in BCAA
        )
        return bcaa / total

    def get_free_aa_ratio(self) -> float:
        """Calculate ratio of free amino acids to total amino acids"""
        total = sum(self.total_amino_acids.values()) or 1.0
        free = sum(self.free_amino_acids.values()) or 0.0
        return free / total

    def to_vector(self) -> np.ndarray:
        """Convert profile to numerical vector for similarity calculations"""
        values = []

        # Add all categories in order
        for category in ['general', 'sugars', 'minerals', 'nucleotides',
                        'organic_acids', 'vitamins', 'molecular_weight',
                        'total_amino_acids', 'free_amino_acids']:
            cat_dict = getattr(self, category)
            values.extend(cat_dict.values())

        return np.array(values)


@dataclass
class PeptoneProduct:
    """Represents a peptone product"""

    sample_id: str
    name: str
    raw_material: str
    manufacturer: str
    profile: NutritionalProfile
    is_sempio: bool = field(default=False)

    def __post_init__(self):
        """Automatically detect Sempio products"""
        if not self.is_sempio:
            self.is_sempio = self.manufacturer.lower() == 'sempio'

    def get_quality_score(self) -> float:
        """Calculate overall quality score based on key indicators"""
        score = 0

        # Protein quality (30%)
        tn = self.profile.general.get('general_TN', 0)
        an = self.profile.general.get('general_AN', 0)
        an_ratio = (an / tn * 100) if tn > 0 else 0
        protein_score = min(1.0, an_ratio / 80)  # Normalize to 80% as excellent
        score += protein_score * 0.3

        # Amino acid profile (40%)
        aa_score = (
            self.profile.get_essential_aa_ratio() * 0.5 +
            self.profile.get_free_aa_ratio() * 0.5
        )
        score += aa_score * 0.4

        # Growth factors (20%)
        nucleotide_sum = sum(self.profile.nucleotides.values())
        vitamin_sum = sum(self.profile.vitamins.values())
        growth_score = min(1.0, (nucleotide_sum + vitamin_sum) / 50)
        score += growth_score * 0.2

        # Molecular weight distribution (10%)
        low_mw = self.profile.molecular_weight.get('mw_pct_lt250Da', 0)
        mid_mw = self.profile.molecular_weight.get('mw_pct_250_500Da', 0)
        mw_score = (low_mw + mid_mw) / 100  # Prefer low to mid molecular weight
        score += mw_score * 0.1

        return score


class PeptoneDatabase:
    """Manages peptone composition data"""

    def __init__(self):
        self.peptones: List[PeptoneProduct] = []
        self._peptone_dict: Dict[str, PeptoneProduct] = {}
        self._manufacturer_index: Dict[str, List[PeptoneProduct]] = {}
        self._raw_data: Optional[pd.DataFrame] = None

    def load_from_excel(self, filepath: str, sheet_name: str = 'data') -> None:
        """
        Load peptone composition data from Excel file

        Args:
            filepath: Path to Excel file
            sheet_name: Sheet name (default 'data')
        """
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        self._load_from_dataframe(df)

    def load_from_csv(self, filepath: str) -> None:
        """Load peptone composition data from CSV file"""
        df = pd.read_csv(filepath)
        self._load_from_dataframe(df)

    def _load_from_dataframe(self, df: pd.DataFrame) -> None:
        """Internal method to load data from DataFrame"""
        # Store raw data
        self._raw_data = df.copy()

        # Preprocess
        df = self.preprocess(df)

        # Parse each row
        for idx, row in df.iterrows():
            # Create nutritional profile
            profile = self._create_profile(row)

            # Create peptone product
            peptone = PeptoneProduct(
                sample_id=str(row['sample_id']),
                name=str(row['Sample_name']),
                raw_material=str(row['raw_material']),
                manufacturer=str(row['manufacturer']),
                profile=profile
            )

            self.peptones.append(peptone)

        # Build indices
        self._build_indices()

        print(f"Loaded {len(self.peptones)} peptone products from data")
        print(f"  - Sempio products: {sum(1 for p in self.peptones if p.is_sempio)}")
        print(f"  - Manufacturers: {len(self._manufacturer_index)}")

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess peptone data:
        - Handle missing values
        - Convert detection limit values
        """
        df = df.copy()

        # List of numeric columns
        numeric_cols = [col for col in df.columns if col not in
                       ['sample_id', 'material_type', 'Sample_name',
                        'raw_material', 'manufacturer']]

        for col in numeric_cols:
            if col in df.columns:
                # Convert to string first to handle mixed types
                df[col] = df[col].astype(str)

                # Replace detection limit indicators
                df[col] = df[col].replace({
                    'N.D': '0',
                    'N.D.': '0',
                    'n.d': '0',
                    'n.d.': '0',
                    '<LOQ': '0',
                    '< LOQ': '0',
                    '<loq': '0',
                    '미량': '0.001',
                    'trace': '0.001',
                    'nan': np.nan,
                    'NaN': np.nan,
                    '': np.nan
                })

                # Convert to numeric
                df[col] = pd.to_numeric(df[col], errors='coerce')

                # Fill remaining NaN with column mean
                if df[col].isna().any():
                    col_mean = df[col].mean()
                    if pd.notna(col_mean):
                        df[col] = df[col].fillna(col_mean)
                    else:
                        df[col] = df[col].fillna(0)

        return df

    def _create_profile(self, row: pd.Series) -> NutritionalProfile:
        """Create nutritional profile from row data"""
        profile = NutritionalProfile()

        # Extract each category
        for category, columns in COMPONENT_CATEGORIES.items():
            cat_dict = {}
            for col in columns:
                if col in row:
                    value = row[col]
                    if pd.notna(value):
                        # Convert MW percentages to ratios (divide by 100)
                        if category == 'molecular_weight' and col.startswith('mw_pct_'):
                            cat_dict[col] = float(value) / 100.0
                        else:
                            cat_dict[col] = float(value)
                    else:
                        cat_dict[col] = 0.0

            setattr(profile, category, cat_dict)

        return profile

    def _build_indices(self) -> None:
        """Build internal indices for fast lookup"""
        self._peptone_dict = {}
        self._manufacturer_index = {}

        for peptone in self.peptones:
            # Name index
            self._peptone_dict[peptone.name] = peptone

            # Manufacturer index
            if peptone.manufacturer not in self._manufacturer_index:
                self._manufacturer_index[peptone.manufacturer] = []
            self._manufacturer_index[peptone.manufacturer].append(peptone)

    def get_peptone_by_name(self, name: str) -> Optional[PeptoneProduct]:
        """Get peptone by product name"""
        return self._peptone_dict.get(name)

    def get_peptones_by_manufacturer(self, manufacturer: str) -> List[PeptoneProduct]:
        """Get all peptones from a manufacturer"""
        return self._manufacturer_index.get(manufacturer, [])

    def get_sempio_peptones(self) -> List[PeptoneProduct]:
        """Get all Sempio peptones"""
        return [p for p in self.peptones if p.is_sempio]

    def filter_by_manufacturer(self, manufacturer: str = 'Sempio') -> List[PeptoneProduct]:
        """Filter peptones by manufacturer"""
        return self.get_peptones_by_manufacturer(manufacturer)

    def calculate_similarity(self,
                           peptone1: PeptoneProduct,
                           peptone2: PeptoneProduct,
                           method: str = 'cosine') -> float:
        """
        Calculate similarity between two peptones

        Args:
            peptone1: First peptone
            peptone2: Second peptone
            method: Similarity method ('cosine' or 'euclidean')

        Returns:
            Similarity score (higher = more similar)
        """
        v1 = peptone1.profile.to_vector().reshape(1, -1)
        v2 = peptone2.profile.to_vector().reshape(1, -1)

        if method == 'cosine':
            return float(cosine_similarity(v1, v2)[0, 0])
        elif method == 'euclidean':
            # Convert to similarity (inverse of distance)
            dist = np.linalg.norm(v1 - v2)
            return 1.0 / (1.0 + dist)
        else:
            raise ValueError(f"Unknown method: {method}")

    def find_similar_peptones(self,
                             peptone: PeptoneProduct,
                             top_n: int = 5,
                             sempio_only: bool = False) -> List[Tuple[PeptoneProduct, float]]:
        """
        Find peptones similar to the given peptone

        Args:
            peptone: Reference peptone
            top_n: Number of results to return
            sempio_only: Only search Sempio products

        Returns:
            List of (peptone, similarity_score) tuples
        """
        candidates = self.get_sempio_peptones() if sempio_only else self.peptones

        # Exclude the reference peptone itself
        candidates = [p for p in candidates if p.name != peptone.name]

        # Calculate similarities
        similarities = []
        for candidate in candidates:
            sim = self.calculate_similarity(peptone, candidate)
            similarities.append((candidate, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_n]

    def get_manufacturer_list(self) -> List[str]:
        """Get list of all manufacturers"""
        return sorted(self._manufacturer_index.keys())

    def to_dataframe(self) -> pd.DataFrame:
        """Convert peptone database to pandas DataFrame"""
        data = []
        for peptone in self.peptones:
            row = {
                'sample_id': peptone.sample_id,
                'name': peptone.name,
                'raw_material': peptone.raw_material,
                'manufacturer': peptone.manufacturer,
                'is_sempio': peptone.is_sempio,
                'quality_score': peptone.get_quality_score(),
                'essential_aa_ratio': peptone.profile.get_essential_aa_ratio(),
                'free_aa_ratio': peptone.profile.get_free_aa_ratio(),
                'bcaa_ratio': peptone.profile.get_bcaa_ratio()
            }

            # Add key nutritional values
            row['TN'] = peptone.profile.general.get('general_TN', 0)
            row['AN'] = peptone.profile.general.get('general_AN', 0)
            row['nucleotide_total'] = sum(peptone.profile.nucleotides.values())
            row['vitamin_total'] = sum(peptone.profile.vitamins.values())

            data.append(row)

        return pd.DataFrame(data)

    def save_to_csv(self, filepath: str) -> None:
        """Save peptone database to CSV"""
        df = self.to_dataframe()
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"Saved {len(df)} peptones to {filepath}")

    def get_summary(self) -> str:
        """Get summary statistics"""
        total = len(self.peptones)
        sempio = sum(1 for p in self.peptones if p.is_sempio)

        summary = f"""
Peptone Database Summary
{'='*50}
Total products: {total}
Sempio products: {sempio}
Other products: {total - sempio}

Manufacturers: {len(self._manufacturer_index)}
"""

        # Top manufacturers
        man_counts = {man: len(peps) for man, peps in self._manufacturer_index.items()}
        top_mans = sorted(man_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        summary += "\nTop manufacturers:\n"
        for man, count in top_mans:
            summary += f"  {man:20} {count:3} products\n"

        return summary


if __name__ == "__main__":
    # Test loading
    db = PeptoneDatabase()

    # Load from Excel
    if Path(r"D:\folder1\composition_template.xlsx").exists():
        db.load_from_excel(r"D:\folder1\composition_template.xlsx")

        print("\n" + db.get_summary())

        # Save to CSV
        db.save_to_csv(r"D:\folder1\peptone_fit_model\data\peptones.csv")

        # Test queries
        print("\n" + "="*50)
        print("Sample queries:")
        print("="*50)

        # Get Sempio peptones
        sempio_peptones = db.get_sempio_peptones()
        print(f"\nSempio peptones: {len(sempio_peptones)}")
        for pep in sempio_peptones[:5]:
            print(f"  - {pep.name:15} Quality: {pep.get_quality_score():.3f}")

        # Find similar peptones
        if sempio_peptones:
            ref = sempio_peptones[0]
            print(f"\nPeptones similar to {ref.name}:")
            similar = db.find_similar_peptones(ref, top_n=3, sempio_only=True)
            for pep, sim in similar:
                print(f"  - {pep.name:15} Similarity: {sim:.3f}")
