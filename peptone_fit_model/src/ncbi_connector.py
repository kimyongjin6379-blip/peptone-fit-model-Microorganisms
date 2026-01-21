"""
NCBI API Connector

Connects to NCBI Entrez API to retrieve taxonomy and genome information
"""

from typing import Optional, Dict, List
from dataclasses import dataclass
import time

try:
    from Bio import Entrez
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    print("Warning: Biopython not available. Install with: pip install biopython")


# Set email for NCBI (required)
Entrez.email = "your_email@example.com"  # Should be configured by user


@dataclass
class TaxonomyInfo:
    """Taxonomy information from NCBI"""

    tax_id: str
    scientific_name: str
    rank: str
    lineage: List[str]
    genus: str = ""
    species: str = ""
    strain: str = ""

    def get_full_name(self) -> str:
        """Get full taxonomic name"""
        parts = [self.genus, self.species]
        if self.strain:
            parts.append(self.strain)
        return ' '.join(p for p in parts if p)


class NCBIConnector:
    """NCBI Entrez API client"""

    def __init__(self, email: str = "your_email@example.com"):
        """
        Initialize NCBI connector

        Args:
            email: Email address for NCBI API (required by NCBI)
        """
        if not BIOPYTHON_AVAILABLE:
            raise ImportError("Biopython is required. Install with: pip install biopython")

        Entrez.email = email
        self.rate_limit_delay = 0.34  # ~3 requests per second

    def search_taxonomy(self, query: str) -> Optional[str]:
        """
        Search NCBI Taxonomy database

        Args:
            query: Search query (e.g., "Escherichia coli")

        Returns:
            Taxonomy ID or None
        """
        try:
            handle = Entrez.esearch(db="taxonomy", term=query, retmax=1)
            record = Entrez.read(handle)
            handle.close()

            if record['IdList']:
                return record['IdList'][0]

            return None

        except Exception as e:
            print(f"Error searching taxonomy: {e}")
            return None

    def get_taxonomy_info(self, tax_id: str) -> Optional[TaxonomyInfo]:
        """
        Get detailed taxonomy information

        Args:
            tax_id: NCBI Taxonomy ID

        Returns:
            TaxonomyInfo object or None
        """
        try:
            time.sleep(self.rate_limit_delay)

            handle = Entrez.efetch(db="taxonomy", id=tax_id, retmode="xml")
            records = Entrez.read(handle)
            handle.close()

            if not records:
                return None

            record = records[0]

            # Parse lineage
            lineage = []
            if 'LineageEx' in record:
                lineage = [item['ScientificName'] for item in record['LineageEx']]

            # Parse scientific name components
            scientific_name = record.get('ScientificName', '')
            rank = record.get('Rank', '')

            # Parse genus, species, strain
            genus = ""
            species = ""
            strain = ""

            name_parts = scientific_name.split()
            if len(name_parts) >= 1:
                genus = name_parts[0]
            if len(name_parts) >= 2:
                species = name_parts[1]
            if len(name_parts) >= 3:
                strain = ' '.join(name_parts[2:])

            return TaxonomyInfo(
                tax_id=tax_id,
                scientific_name=scientific_name,
                rank=rank,
                lineage=lineage,
                genus=genus,
                species=species,
                strain=strain
            )

        except Exception as e:
            print(f"Error fetching taxonomy info: {e}")
            return None

    def get_taxonomy_by_name(self, genus: str, species: str,
                            strain: Optional[str] = None) -> Optional[TaxonomyInfo]:
        """
        Get taxonomy information by organism name

        Args:
            genus: Genus name
            species: Species name
            strain: Optional strain designation

        Returns:
            TaxonomyInfo object or None
        """
        # Build query
        query_parts = [genus, species]
        if strain:
            query_parts.append(strain)
        query = ' '.join(query_parts)

        # Search for taxonomy ID
        tax_id = self.search_taxonomy(query)
        if not tax_id:
            # Try without strain
            if strain:
                query = f"{genus} {species}"
                tax_id = self.search_taxonomy(query)

        if not tax_id:
            return None

        # Get taxonomy info
        return self.get_taxonomy_info(tax_id)


if __name__ == "__main__":
    if not BIOPYTHON_AVAILABLE:
        print("Biopython not available. Skipping tests.")
    else:
        print("Testing NCBI connector...")
        print("Note: This requires internet connection and may take time due to rate limiting")

        connector = NCBIConnector()

        # Test organisms
        test_cases = [
            ('Escherichia', 'coli', 'K-12'),
            ('Lactobacillus', 'plantarum', None),
            ('Bacillus', 'subtilis', None),
        ]

        print("\n" + "="*80)
        print("Testing taxonomy lookup")
        print("="*80)

        for genus, species, strain in test_cases:
            print(f"\nLooking up: {genus} {species}" + (f" {strain}" if strain else ""))

            try:
                tax_info = connector.get_taxonomy_by_name(genus, species, strain)

                if tax_info:
                    print(f"  Tax ID: {tax_info.tax_id}")
                    print(f"  Name: {tax_info.scientific_name}")
                    print(f"  Rank: {tax_info.rank}")
                    print(f"  Lineage: {' > '.join(tax_info.lineage[-3:])}")
                else:
                    print("  Not found")

            except Exception as e:
                print(f"  Error: {e}")

        print("\n\nNCBI connector test complete!")
