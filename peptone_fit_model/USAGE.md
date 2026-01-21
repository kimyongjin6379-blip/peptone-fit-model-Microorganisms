# Peptone Fit Model - Usage Guide

## Quick Start

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure data files are in place:
- `D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx`
- `D:\folder1\composition_template.xlsx`

### Basic Usage

#### List Available Strains
```bash
python peptone_fit.py list strains
```

#### List Strains by Category
```bash
python peptone_fit.py list strains --category LAB
```

#### List Available Peptones
```bash
python peptone_fit.py list peptones
```

#### Get Peptone Recommendations for a Strain
```bash
python peptone_fit.py recommend "KCCM 12116"
```

This will show:
- Strain information
- Top 5 single peptone recommendations
- Top 5 blend recommendations (2-3 components)

#### Get Only Single Peptone Recommendations
```bash
python peptone_fit.py recommend "KCCM 12116" --mode single
```

#### Get Only Blend Recommendations
```bash
python peptone_fit.py recommend "KCCM 12116" --mode blend
```

#### Save Results to CSV
```bash
python peptone_fit.py recommend "KCCM 12116" --output results.csv
```

#### Include All Manufacturers (not just Sempio)
```bash
python peptone_fit.py recommend "KCCM 12116" --all-products
```

#### Customize Number of Recommendations
```bash
python peptone_fit.py recommend "KCCM 12116" --top-n 10
```

## Python API Usage

### Basic Example

```python
from src.strain_manager import StrainDatabase
from src.peptone_analyzer import PeptoneDatabase
from src.recommendation_engine import PeptoneRecommender

# Load databases
strain_db = StrainDatabase()
strain_db.load_from_excel(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")

peptone_db = PeptoneDatabase()
peptone_db.load_from_excel(r"D:\folder1\composition_template.xlsx")

# Create recommender
recommender = PeptoneRecommender(strain_db, peptone_db)

# Get recommendations
recommendations = recommender.recommend_single("KCCM 12116", top_n=5)

# Print results
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec.get_description()}")
    print(f"   Score: {rec.overall_score:.3f}")
```

### Get Blend Recommendations

```python
blend_recs = recommender.recommend_blend(
    strain_id="KCCM 12116",
    max_components=3,
    top_n=5,
    sempio_only=True
)

for rec in blend_recs:
    print(f"Blend: {rec.get_description()}")
    print(f"Score: {rec.overall_score:.3f}")
    for peptone, ratio in zip(rec.peptones, rec.ratios):
        print(f"  - {peptone.name}: {ratio*100:.1f}%")
```

### Access Strain Information

```python
# Get specific strain
strain = strain_db.get_strain_by_id("KCCM 12116")
print(f"Full name: {strain.get_full_name()}")
print(f"Category: {strain.category}")
print(f"Nutritional type: {strain.get_nutritional_type()}")
print(f"Requirements: {strain.get_key_requirements()}")

# Search strains
lab_strains = strain_db.get_strains_by_category('LAB')
print(f"Found {len(lab_strains)} LAB strains")
```

### Access Peptone Information

```python
# Get specific peptone
peptone = peptone_db.get_peptone_by_name("SOY-N+")
print(f"Quality score: {peptone.get_quality_score():.3f}")
print(f"Manufacturer: {peptone.manufacturer}")

# Get Sempio peptones
sempio = peptone_db.get_sempio_peptones()
print(f"Sempio products: {len(sempio)}")

# Find similar peptones
similar = peptone_db.find_similar_peptones(peptone, top_n=3)
for sim_pep, similarity in similar:
    print(f"  {sim_pep.name}: {similarity:.3f}")
```

### Custom Scoring Weights

You can modify the scoring weights in `src/recommendation_engine.py`:

```python
SCORING_WEIGHTS = {
    'nutritional_match': 0.40,      # 40%
    'amino_acid_match': 0.25,       # 25%
    'growth_factor_match': 0.20,    # 20%
    'mw_distribution_match': 0.15   # 15%
}
```

## Understanding the Results

### Fitness Scores

The recommendation engine calculates fitness scores based on four components:

1. **Nutritional Match (40%)**: How well the peptone meets the strain's basic nutritional needs (TN, AN)
2. **Amino Acid Match (25%)**: Quality of amino acid profile, including essential AA and free AA
3. **Growth Factor Match (20%)**: Presence of nucleotides and vitamins
4. **MW Distribution Match (15%)**: Suitability of peptide molecular weight distribution

### Score Interpretation

- **0.0 - 0.3**: Poor match (not recommended)
- **0.3 - 0.5**: Fair match (may work but not optimal)
- **0.5 - 0.7**: Good match (recommended)
- **0.7 - 1.0**: Excellent match (highly recommended)

### Strain Categories

Different strain categories have different nutritional requirements:

- **LAB (Lactic Acid Bacteria)**: Fastidious, high requirements for amino acids, vitamins, nucleotides
- **Bacillus**: Minimal requirements, can grow on simple media
- **E. coli**: Moderate requirements, efficient metabolism
- **Yeast**: Moderate requirements, need vitamins and trace minerals
- **Actinomycetes**: Complex requirements, prefer complex nitrogen sources

## Advanced Features

### Export Results to Excel

```python
import pandas as pd

# Get recommendations
recs = recommender.recommend_single("KCCM 12116", top_n=10)

# Convert to DataFrame
data = [rec.to_dict() for rec in recs]
df = pd.DataFrame(data)

# Save to Excel
df.to_excel("recommendations.xlsx", index=False)
```

### Batch Processing

```python
# Process multiple strains
strain_ids = ["KCCM 12116", "KCTC 3108", "KCTC 3510"]

results = {}
for strain_id in strain_ids:
    recs = recommender.recommend_single(strain_id, top_n=3)
    results[strain_id] = recs

# Export all results
for strain_id, recs in results.items():
    print(f"\nRecommendations for {strain_id}:")
    for i, rec in enumerate(recs, 1):
        print(f"  {i}. {rec.get_description()} - Score: {rec.overall_score:.3f}")
```

## Troubleshooting

### Import Errors

If you get import errors, ensure you're running from the project root:
```bash
cd D:\folder1\peptone_fit_model
python peptone_fit.py ...
```

### Data File Not Found

Make sure the data files exist at the specified paths, or provide custom paths:
```bash
python peptone_fit.py recommend "KCCM 12116" \
    --strain-file "path/to/strains.xlsx" \
    --peptone-file "path/to/peptones.xlsx"
```

### Encoding Issues

If you see encoding errors with Korean characters, ensure your terminal supports UTF-8:
```bash
# On Windows
chcp 65001
```

## Next Steps

Phase 1 is complete! The following features are planned for future phases:

- **Phase 2**: KEGG/NCBI database integration for metabolic pathway analysis
- **Phase 3**: Machine learning model for improved predictions
- **Phase 4**: Streamlit web UI for easier access

## Support

For issues or questions, contact the Sempio R&D Team.
