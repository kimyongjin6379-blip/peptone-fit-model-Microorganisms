"""
Strain Manager Module

Manages microbial strain data including:
- Loading strain information from Excel files
- Strain classification and categorization
- NDA strain filtering
- Metadata management
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from pathlib import Path


# Strain classification system
STRAIN_CATEGORIES = {
    'LAB': {  # 유산균 (Lactic Acid Bacteria)
        'genera': [
            'Lactobacillus', 'Lactiplantibacillus', 'Lacticaseibacillus',
            'Limosilactobacillus', 'Ligilactobacillus', 'Bifidobacterium',
            'Enterococcus', 'Streptococcus', 'Lactococcus', 'Leuconostoc',
            'Weissella', 'Pediococcus'
        ],
        'nutritional_type': 'fastidious',
        'key_requirements': ['amino_acids', 'B_vitamins', 'nucleotides'],
        'description': 'Lactic acid bacteria with high nutritional requirements'
    },
    'Bacillus': {
        'genera': ['Bacillus'],
        'nutritional_type': 'minimal',
        'key_requirements': ['nitrogen_source', 'trace_minerals'],
        'description': 'Spore-forming bacteria with minimal nutritional needs'
    },
    'E_coli': {
        'genera': ['Escherichia'],
        'nutritional_type': 'minimal_to_moderate',
        'key_requirements': ['nitrogen_source', 'carbon_source'],
        'description': 'Gram-negative bacteria, commonly used in biotechnology'
    },
    'Yeast': {
        'genera': ['Saccharomyces', 'Candida', 'Pichia'],
        'nutritional_type': 'moderate',
        'key_requirements': ['nitrogen_source', 'vitamins', 'trace_minerals'],
        'description': 'Eukaryotic microorganisms'
    },
    'Actinomycetes': {
        'genera': ['Streptomyces', 'Actinomyces'],
        'nutritional_type': 'complex',
        'key_requirements': ['complex_nitrogen', 'phosphate'],
        'description': 'Filamentous bacteria, antibiotic producers'
    },
    'Other': {
        'genera': [],  # Catch-all for unclassified
        'nutritional_type': 'variable',
        'key_requirements': ['basic_nutrients'],
        'description': 'Other microorganisms'
    }
}


@dataclass
class StrainProfile:
    """Data class representing a microbial strain"""

    strain_number: int
    domain: Optional[str]
    genus: str
    species: str
    strain_id: str
    temperature: float
    medium: str
    category: str = field(default='Other')
    is_nda: bool = field(default=False)
    ncbi_taxonomy_id: Optional[str] = field(default=None)
    test_results: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Automatically determine category based on genus"""
        if not self.category or self.category == 'Other':
            self.category = self._determine_category()

        # Check if NDA strain (marked with *)
        if isinstance(self.strain_id, str) and '*' in self.strain_id:
            self.is_nda = True

    def _determine_category(self) -> str:
        """Determine strain category based on genus"""
        if pd.isna(self.genus):
            return 'Other'

        genus_str = str(self.genus).strip()

        for category, info in STRAIN_CATEGORIES.items():
            if genus_str in info['genera']:
                return category

        return 'Other'

    def get_full_name(self) -> str:
        """Get full taxonomic name"""
        parts = []
        if self.genus and not pd.isna(self.genus):
            parts.append(str(self.genus))
        if self.species and not pd.isna(self.species):
            parts.append(str(self.species))
        if self.strain_id and not pd.isna(self.strain_id):
            parts.append(str(self.strain_id))
        return ' '.join(parts)

    def get_nutritional_type(self) -> str:
        """Get nutritional type based on category"""
        return STRAIN_CATEGORIES.get(self.category, {}).get('nutritional_type', 'variable')

    def get_key_requirements(self) -> List[str]:
        """Get key nutritional requirements"""
        return STRAIN_CATEGORIES.get(self.category, {}).get('key_requirements', [])


class StrainDatabase:
    """Manages strain data loading and querying"""

    def __init__(self):
        self.strains: List[StrainProfile] = []
        self._strain_dict: Dict[str, StrainProfile] = {}
        self._genus_index: Dict[str, List[StrainProfile]] = {}
        self._category_index: Dict[str, List[StrainProfile]] = {}

    def load_from_excel(self, filepath: str, skiprows: int = 8) -> None:
        """
        Load strain data from Excel file

        Args:
            filepath: Path to Excel file
            skiprows: Number of rows to skip (default 8 for header)
        """
        df = pd.read_excel(filepath, sheet_name=0, header=None, skiprows=skiprows)

        # Remove completely empty rows
        df = df.dropna(how='all')

        # Assign column names
        columns = [
            'no', 'domain', 'genus', 'species', 'strain_id',
            'temperature', 'medium', 'test_col_1', 'test_col_2', 'test_col_3',
            'test_col_4', 'test_col_5', 'test_col_6', 'test_col_7',
            'test_col_8', 'test_col_9', 'notes_1', 'notes_2'
        ]

        df.columns = columns[:len(df.columns)]

        # Forward fill domain and genus (due to merged cells)
        df['domain'] = df['domain'].ffill()
        df['genus'] = df['genus'].ffill()

        # Parse each row into StrainProfile
        for idx, row in df.iterrows():
            # Skip rows without strain_id
            if pd.isna(row['strain_id']):
                continue

            # Collect test results
            test_results = {}
            for col in ['test_col_1', 'test_col_2', 'test_col_3', 'test_col_4',
                       'test_col_5', 'test_col_6', 'test_col_7', 'test_col_8', 'test_col_9']:
                if col in row and not pd.isna(row[col]):
                    test_results[col] = row[col]

            # Collect notes
            notes = []
            for col in ['notes_1', 'notes_2']:
                if col in row and not pd.isna(row[col]):
                    notes.append(str(row[col]))

            # Parse temperature (handle mixed formats like "30 or 37")
            temp_value = 37.0  # Default
            if not pd.isna(row['temperature']):
                temp_str = str(row['temperature']).strip()
                try:
                    temp_value = float(temp_str)
                except ValueError:
                    # Handle cases like "30 or 37" - take first value
                    import re
                    match = re.search(r'(\d+)', temp_str)
                    if match:
                        temp_value = float(match.group(1))

            # Create StrainProfile
            strain = StrainProfile(
                strain_number=int(row['no']) if not pd.isna(row['no']) else idx + 1,
                domain=row['domain'] if not pd.isna(row['domain']) else None,
                genus=row['genus'] if not pd.isna(row['genus']) else 'Unknown',
                species=row['species'] if not pd.isna(row['species']) else 'sp.',
                strain_id=str(row['strain_id']).strip(),
                temperature=temp_value,
                medium=str(row['medium']) if not pd.isna(row['medium']) else 'Unknown',
                test_results=test_results,
                notes=notes
            )

            self.strains.append(strain)

        # Build indices
        self._build_indices()

        print(f"Loaded {len(self.strains)} strains from {filepath}")
        print(f"  - NDA strains: {sum(1 for s in self.strains if s.is_nda)}")
        print(f"  - Categories: {self.get_category_counts()}")

    def _build_indices(self) -> None:
        """Build internal indices for fast lookup"""
        self._strain_dict = {}
        self._genus_index = {}
        self._category_index = {}

        for strain in self.strains:
            # Strain ID index
            self._strain_dict[strain.strain_id] = strain

            # Genus index
            if strain.genus not in self._genus_index:
                self._genus_index[strain.genus] = []
            self._genus_index[strain.genus].append(strain)

            # Category index
            if strain.category not in self._category_index:
                self._category_index[strain.category] = []
            self._category_index[strain.category].append(strain)

    def get_strain_by_id(self, strain_id: str) -> Optional[StrainProfile]:
        """Get strain by strain ID"""
        return self._strain_dict.get(strain_id)

    def get_strains_by_genus(self, genus: str) -> List[StrainProfile]:
        """Get all strains of a specific genus"""
        return self._genus_index.get(genus, [])

    def get_strains_by_category(self, category: str) -> List[StrainProfile]:
        """Get all strains in a category"""
        return self._category_index.get(category, [])

    def get_nda_strains(self) -> List[StrainProfile]:
        """Get all NDA strains"""
        return [s for s in self.strains if s.is_nda]

    def get_public_strains(self) -> List[StrainProfile]:
        """Get all public (non-NDA) strains"""
        return [s for s in self.strains if not s.is_nda]

    def is_nda_strain(self, strain_id: str) -> bool:
        """Check if strain is NDA"""
        strain = self.get_strain_by_id(strain_id)
        return strain.is_nda if strain else False

    def get_category_counts(self) -> Dict[str, int]:
        """Get count of strains per category"""
        return {cat: len(strains) for cat, strains in self._category_index.items()}

    def get_genus_list(self) -> List[str]:
        """Get list of all genera"""
        return sorted(self._genus_index.keys())

    def search_strains(self,
                      genus: Optional[str] = None,
                      category: Optional[str] = None,
                      include_nda: bool = True) -> List[StrainProfile]:
        """
        Search strains with filters

        Args:
            genus: Filter by genus
            category: Filter by category
            include_nda: Include NDA strains in results

        Returns:
            List of matching strains
        """
        results = self.strains.copy()

        if genus:
            results = [s for s in results if s.genus == genus]

        if category:
            results = [s for s in results if s.category == category]

        if not include_nda:
            results = [s for s in results if not s.is_nda]

        return results

    def to_dataframe(self) -> pd.DataFrame:
        """Convert strain database to pandas DataFrame"""
        data = []
        for strain in self.strains:
            data.append({
                'strain_number': strain.strain_number,
                'domain': strain.domain,
                'genus': strain.genus,
                'species': strain.species,
                'strain_id': strain.strain_id,
                'full_name': strain.get_full_name(),
                'temperature': strain.temperature,
                'medium': strain.medium,
                'category': strain.category,
                'nutritional_type': strain.get_nutritional_type(),
                'is_nda': strain.is_nda,
                'ncbi_taxonomy_id': strain.ncbi_taxonomy_id
            })

        return pd.DataFrame(data)

    def save_to_csv(self, filepath: str) -> None:
        """Save strain database to CSV"""
        df = self.to_dataframe()
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"Saved {len(df)} strains to {filepath}")

    def get_summary(self) -> str:
        """Get summary statistics"""
        total = len(self.strains)
        nda_count = sum(1 for s in self.strains if s.is_nda)

        summary = f"""
Strain Database Summary
{'='*50}
Total strains: {total}
NDA strains: {nda_count}
Public strains: {total - nda_count}

Category breakdown:
"""
        for category, count in sorted(self.get_category_counts().items()):
            percentage = count / total * 100
            summary += f"  {category:15} {count:3} ({percentage:5.1f}%)\n"

        summary += f"\nUnique genera: {len(self._genus_index)}\n"

        return summary


if __name__ == "__main__":
    # Test loading
    db = StrainDatabase()

    # Try loading from parent directory
    import os
    if os.path.exists(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx"):
        db.load_from_excel(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")

        print("\n" + db.get_summary())

        # Save to CSV
        db.save_to_csv(r"D:\folder1\peptone_fit_model\data\strains.csv")

        # Test queries
        print("\n" + "="*50)
        print("Sample queries:")
        print("="*50)

        # Get LAB strains
        lab_strains = db.get_strains_by_category('LAB')
        print(f"\nLAB strains: {len(lab_strains)}")
        for strain in lab_strains[:3]:
            print(f"  - {strain.get_full_name()}")

        # Get specific strain
        strain = db.get_strain_by_id('KCCM 12116')
        if strain:
            print(f"\nStrain KCCM 12116:")
            print(f"  Full name: {strain.get_full_name()}")
            print(f"  Category: {strain.category}")
            print(f"  Nutritional type: {strain.get_nutritional_type()}")
            print(f"  Key requirements: {strain.get_key_requirements()}")
