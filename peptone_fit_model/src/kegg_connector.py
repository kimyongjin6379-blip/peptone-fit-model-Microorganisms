"""
KEGG API Connector

Connects to KEGG REST API to retrieve metabolic pathway information
for microbial strains
"""

import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta


# KEGG REST API base URL
KEGG_API_BASE = "https://rest.kegg.jp"

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "kegg_cache"
CACHE_EXPIRY_DAYS = 30

# Relevant KEGG pathways for peptone requirements
PATHWAY_CATEGORIES = {
    'amino_acid_biosynthesis': {
        'map00250': 'Alanine, aspartate and glutamate metabolism',
        'map00260': 'Glycine, serine and threonine metabolism',
        'map00270': 'Cysteine and methionine metabolism',
        'map00280': 'Valine, leucine and isoleucine degradation',
        'map00290': 'Valine, leucine and isoleucine biosynthesis',
        'map00300': 'Lysine biosynthesis',
        'map00310': 'Lysine degradation',
        'map00330': 'Arginine and proline metabolism',
        'map00340': 'Histidine metabolism',
        'map00350': 'Tyrosine metabolism',
        'map00360': 'Phenylalanine metabolism',
        'map00380': 'Tryptophan metabolism',
        'map00400': 'Phenylalanine, tyrosine and tryptophan biosynthesis',
    },
    'nucleotide_metabolism': {
        'map00230': 'Purine metabolism',
        'map00240': 'Pyrimidine metabolism',
    },
    'vitamin_biosynthesis': {
        'map00730': 'Thiamine (B1) metabolism',
        'map00740': 'Riboflavin (B2) metabolism',
        'map00750': 'Vitamin B6 metabolism',
        'map00760': 'Nicotinate and nicotinamide (B3) metabolism',
        'map00770': 'Pantothenate and CoA (B5) biosynthesis',
        'map00780': 'Biotin (B7) metabolism',
        'map00785': 'Lipoic acid metabolism',
        'map00790': 'Folate (B9) biosynthesis',
    },
    'cofactor_biosynthesis': {
        'map00860': 'Porphyrin and chlorophyll metabolism',
    }
}

# Amino acid to pathway mapping
AMINO_ACID_PATHWAYS = {
    'Alanine': 'map00250',
    'Aspartate': 'map00250',
    'Glutamate': 'map00250',
    'Glycine': 'map00260',
    'Serine': 'map00260',
    'Threonine': 'map00260',
    'Cysteine': 'map00270',
    'Methionine': 'map00270',
    'Valine': 'map00290',
    'Leucine': 'map00290',
    'Isoleucine': 'map00290',
    'Lysine': 'map00300',
    'Arginine': 'map00330',
    'Proline': 'map00330',
    'Histidine': 'map00340',
    'Tyrosine': 'map00350',
    'Phenylalanine': 'map00400',
    'Tryptophan': 'map00400',
}


@dataclass
class PathwayInfo:
    """Information about a KEGG pathway"""

    pathway_id: str
    name: str
    genes: List[str] = field(default_factory=list)
    enzymes: List[str] = field(default_factory=list)
    compounds: List[str] = field(default_factory=list)
    completeness: float = 0.0  # 0-1 scale

    def is_complete(self, threshold: float = 0.7) -> bool:
        """Check if pathway is considered complete"""
        return self.completeness >= threshold


@dataclass
class OrganismPathways:
    """Pathway information for an organism"""

    organism_code: str
    organism_name: str
    pathways: Dict[str, PathwayInfo] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=datetime.now)

    def has_pathway(self, pathway_id: str) -> bool:
        """Check if organism has a specific pathway"""
        return pathway_id in self.pathways

    def get_incomplete_pathways(self, threshold: float = 0.7) -> List[str]:
        """Get list of incomplete pathway IDs"""
        return [
            pid for pid, pinfo in self.pathways.items()
            if not pinfo.is_complete(threshold)
        ]

    def get_missing_pathways(self, required_pathways: List[str]) -> List[str]:
        """Get list of required but missing pathways"""
        return [pid for pid in required_pathways if pid not in self.pathways]


class KEGGConnector:
    """KEGG REST API client"""

    def __init__(self, cache_dir: Optional[Path] = None, use_cache: bool = True):
        """
        Initialize KEGG connector

        Args:
            cache_dir: Directory for caching results
            use_cache: Whether to use cached results
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.use_cache = use_cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key"""
        safe_key = key.replace(':', '_').replace('/', '_')
        return self.cache_dir / f"{safe_key}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid"""
        if not cache_path.exists():
            return False

        modified_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = modified_time + timedelta(days=CACHE_EXPIRY_DAYS)

        return datetime.now() < expiry_time

    def _load_cache(self, key: str) -> Optional[Dict]:
        """Load data from cache"""
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(key)
        if not self._is_cache_valid(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cache for {key}: {e}")
            return None

    def _save_cache(self, key: str, data: Dict) -> None:
        """Save data to cache"""
        if not self.use_cache:
            return

        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save cache for {key}: {e}")

    def _kegg_request(self, endpoint: str, max_retries: int = 3) -> Optional[str]:
        """
        Make a request to KEGG REST API

        Args:
            endpoint: API endpoint (e.g., 'list/organism')
            max_retries: Maximum number of retries

        Returns:
            Response text or None if failed
        """
        url = f"{KEGG_API_BASE}/{endpoint}"

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 404:
                    return None
                else:
                    print(f"KEGG API returned status {response.status_code}")
            except requests.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        return None

    def find_organism(self, genus: str, species: str) -> Optional[str]:
        """
        Find KEGG organism code for a species

        Args:
            genus: Genus name
            species: Species name

        Returns:
            KEGG organism code (e.g., 'eco' for E. coli) or None
        """
        cache_key = f"organism_{genus}_{species}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached.get('organism_code')

        # Get organism list
        result = self._kegg_request('list/organism')
        if not result:
            return None

        # Parse organism list
        search_name = f"{genus} {species}".lower()
        for line in result.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 4:
                org_code = parts[1]
                org_name = parts[2].lower()

                if genus.lower() in org_name and species.lower() in org_name:
                    # Cache result
                    self._save_cache(cache_key, {'organism_code': org_code})
                    return org_code

        return None

    def get_organism_pathways(self, organism_code: str) -> Optional[OrganismPathways]:
        """
        Get all pathways for an organism

        Args:
            organism_code: KEGG organism code

        Returns:
            OrganismPathways object or None
        """
        cache_key = f"pathways_{organism_code}"
        cached = self._load_cache(cache_key)

        if cached:
            # Reconstruct from cache
            org_pathways = OrganismPathways(
                organism_code=cached['organism_code'],
                organism_name=cached['organism_name'],
                retrieved_at=datetime.fromisoformat(cached['retrieved_at'])
            )
            for pid, pdata in cached['pathways'].items():
                org_pathways.pathways[pid] = PathwayInfo(**pdata)
            return org_pathways

        # Get pathway list
        result = self._kegg_request(f'list/pathway/{organism_code}')
        if not result:
            return None

        # Parse pathways
        org_pathways = OrganismPathways(
            organism_code=organism_code,
            organism_name=organism_code
        )

        for line in result.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                pathway_id = parts[0].replace(f'path:{organism_code}', 'map')
                pathway_name = parts[1]

                # Get pathway details
                pathway_info = self.get_pathway_info(organism_code, pathway_id)
                if pathway_info:
                    org_pathways.pathways[pathway_id] = pathway_info

        # Cache result
        cache_data = {
            'organism_code': org_pathways.organism_code,
            'organism_name': org_pathways.organism_name,
            'retrieved_at': org_pathways.retrieved_at.isoformat(),
            'pathways': {
                pid: {
                    'pathway_id': p.pathway_id,
                    'name': p.name,
                    'genes': p.genes,
                    'enzymes': p.enzymes,
                    'compounds': p.compounds,
                    'completeness': p.completeness
                }
                for pid, p in org_pathways.pathways.items()
            }
        }
        self._save_cache(cache_key, cache_data)

        return org_pathways

    def get_pathway_info(self, organism_code: str, pathway_id: str) -> Optional[PathwayInfo]:
        """
        Get detailed information about a pathway

        Args:
            organism_code: KEGG organism code
            pathway_id: Pathway ID (e.g., 'map00260')

        Returns:
            PathwayInfo object or None
        """
        # Get pathway for organism
        org_pathway_id = pathway_id.replace('map', organism_code)
        result = self._kegg_request(f'get/{org_pathway_id}')

        if not result:
            return None

        # Parse pathway information
        genes = []
        enzymes = []
        compounds = []
        name = pathway_id

        in_gene_section = False
        in_enzyme_section = False
        in_compound_section = False

        for line in result.split('\n'):
            if line.startswith('NAME'):
                name = line.split(maxsplit=1)[1].strip()
            elif line.startswith('GENE'):
                in_gene_section = True
                in_enzyme_section = False
                in_compound_section = False
                gene_part = line.split(maxsplit=1)[1] if len(line.split(maxsplit=1)) > 1 else ''
                if gene_part:
                    genes.append(gene_part.split()[0])
            elif line.startswith('ENZYME'):
                in_gene_section = False
                in_enzyme_section = True
                in_compound_section = False
                enzyme_part = line.split(maxsplit=1)[1] if len(line.split(maxsplit=1)) > 1 else ''
                if enzyme_part:
                    enzymes.extend(enzyme_part.split())
            elif line.startswith('COMPOUND'):
                in_gene_section = False
                in_enzyme_section = False
                in_compound_section = True
            elif line.startswith(' ') and in_gene_section:
                gene_line = line.strip()
                if gene_line:
                    genes.append(gene_line.split()[0])
            elif line.startswith(' ') and in_enzyme_section:
                enzyme_line = line.strip()
                if enzyme_line:
                    enzymes.extend(enzyme_line.split())
            elif not line.startswith(' '):
                in_gene_section = False
                in_enzyme_section = False
                in_compound_section = False

        # Estimate completeness (simplified - count genes/enzymes present)
        # More sophisticated analysis would check specific key enzymes
        completeness = 1.0 if len(genes) > 0 else 0.0

        return PathwayInfo(
            pathway_id=pathway_id,
            name=name,
            genes=genes,
            enzymes=enzymes,
            compounds=compounds,
            completeness=completeness
        )

    def infer_nutritional_requirements(self,
                                      organism_pathways: OrganismPathways) -> Dict[str, str]:
        """
        Infer nutritional requirements based on pathway presence

        Args:
            organism_pathways: Organism pathway information

        Returns:
            Dictionary of nutrient -> requirement level (high/medium/low)
        """
        requirements = {}

        # Check amino acid biosynthesis pathways
        for aa, pathway_id in AMINO_ACID_PATHWAYS.items():
            if not organism_pathways.has_pathway(pathway_id):
                requirements[f'{aa}_requirement'] = 'high'
            else:
                pathway = organism_pathways.pathways.get(pathway_id)
                if pathway and not pathway.is_complete(threshold=0.7):
                    requirements[f'{aa}_requirement'] = 'medium'
                else:
                    requirements[f'{aa}_requirement'] = 'low'

        # Check vitamin biosynthesis
        vitamin_pathways = PATHWAY_CATEGORIES['vitamin_biosynthesis']
        vitamin_missing = 0
        vitamin_total = len(vitamin_pathways)

        for pathway_id in vitamin_pathways.keys():
            if not organism_pathways.has_pathway(pathway_id):
                vitamin_missing += 1

        if vitamin_missing > vitamin_total * 0.7:
            requirements['vitamin_requirement'] = 'high'
        elif vitamin_missing > vitamin_total * 0.3:
            requirements['vitamin_requirement'] = 'medium'
        else:
            requirements['vitamin_requirement'] = 'low'

        # Check nucleotide metabolism
        purine_present = organism_pathways.has_pathway('map00230')
        pyrimidine_present = organism_pathways.has_pathway('map00240')

        if not purine_present or not pyrimidine_present:
            requirements['nucleotide_requirement'] = 'high'
        else:
            requirements['nucleotide_requirement'] = 'low'

        return requirements


if __name__ == "__main__":
    # Test KEGG connector
    print("Testing KEGG connector...")

    connector = KEGGConnector()

    # Test 1: Find organism code
    print("\n" + "="*80)
    print("Test 1: Finding organism codes")
    print("="*80)

    test_organisms = [
        ('Escherichia', 'coli'),
        ('Lactobacillus', 'plantarum'),
        ('Bacillus', 'subtilis'),
    ]

    for genus, species in test_organisms:
        org_code = connector.find_organism(genus, species)
        print(f"{genus} {species}: {org_code if org_code else 'Not found'}")

    # Test 2: Get pathways for E. coli
    print("\n" + "="*80)
    print("Test 2: Getting pathways for E. coli")
    print("="*80)

    eco_pathways = connector.get_organism_pathways('eco')
    if eco_pathways:
        print(f"Found {len(eco_pathways.pathways)} pathways")

        # Check amino acid pathways
        aa_pathways = [pid for pid in AMINO_ACID_PATHWAYS.values()]
        present = sum(1 for pid in aa_pathways if eco_pathways.has_pathway(pid))
        print(f"Amino acid biosynthesis pathways: {present}/{len(aa_pathways)}")

        # Infer requirements
        requirements = connector.infer_nutritional_requirements(eco_pathways)
        print(f"\nInferred requirements:")
        for nutrient, level in list(requirements.items())[:5]:
            print(f"  {nutrient}: {level}")

    print("\n\nKEGG connector test complete!")
