"""
Main CLI Interface for Peptone Fit Model
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .strain_manager import StrainDatabase
from .peptone_analyzer import PeptoneDatabase
from .recommendation_engine import PeptoneRecommender


def load_databases(strain_file: Optional[str] = None,
                  peptone_file: Optional[str] = None):
    """Load strain and peptone databases"""

    # Default file paths
    if strain_file is None:
        strain_file = r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx"

    if peptone_file is None:
        peptone_file = r"D:\folder1\composition_template.xlsx"

    # Load databases
    strain_db = StrainDatabase()
    peptone_db = PeptoneDatabase()

    print(f"Loading strain database from: {strain_file}")
    strain_db.load_from_excel(strain_file)

    print(f"Loading peptone database from: {peptone_file}")
    peptone_db.load_from_excel(peptone_file)

    return strain_db, peptone_db


def recommend_command(args):
    """Handle recommend command"""

    # Load databases
    strain_db, peptone_db = load_databases(args.strain_file, args.peptone_file)

    # Create recommender
    recommender = PeptoneRecommender(strain_db, peptone_db)

    # Get strain
    strain = strain_db.get_strain_by_id(args.strain_id)
    if not strain:
        print(f"Error: Strain '{args.strain_id}' not found")
        print(f"\nAvailable strains:")
        for s in strain_db.strains[:10]:
            print(f"  - {s.strain_id}: {s.get_full_name()}")
        print(f"  ... and {len(strain_db.strains) - 10} more")
        return

    # Display strain information
    print("\n" + "="*80)
    print("STRAIN INFORMATION")
    print("="*80)
    print(f"ID: {strain.strain_id}")
    print(f"Name: {strain.get_full_name()}")
    print(f"Category: {strain.category}")
    print(f"Nutritional type: {strain.get_nutritional_type()}")
    print(f"Temperature: {strain.temperature}°C")
    print(f"Medium: {strain.medium}")
    print(f"Key requirements: {', '.join(strain.get_key_requirements())}")

    # Single peptone recommendations
    if args.mode in ['single', 'all']:
        print("\n" + "="*80)
        print("SINGLE PEPTONE RECOMMENDATIONS")
        print("="*80)

        recs = recommender.recommend_single(
            args.strain_id,
            top_n=args.top_n,
            sempio_only=args.sempio_only
        )

        for i, rec in enumerate(recs, 1):
            print(f"\n{i}. {rec.get_description()}")
            print(f"   Overall Score: {rec.overall_score:.3f}")
            print(f"   - Nutritional match: {rec.detailed_scores['nutritional_match']:.3f}")
            print(f"   - Amino acid match: {rec.detailed_scores['amino_acid_match']:.3f}")
            print(f"   - Growth factors: {rec.detailed_scores['growth_factor_match']:.3f}")
            print(f"   - MW distribution: {rec.detailed_scores['mw_distribution_match']:.3f}")
            if rec.rationale:
                print(f"   Rationale: {rec.rationale}")

    # Blend recommendations
    if args.mode in ['blend', 'all']:
        print("\n" + "="*80)
        print(f"BLEND RECOMMENDATIONS (up to {args.max_components} components)")
        print("="*80)

        blend_recs = recommender.recommend_blend(
            args.strain_id,
            max_components=args.max_components,
            top_n=args.top_n,
            sempio_only=args.sempio_only
        )

        for i, rec in enumerate(blend_recs, 1):
            print(f"\n{i}. {rec.get_description()}")
            print(f"   Overall Score: {rec.overall_score:.3f}")
            print(f"   Composition:")
            for pep, ratio in zip(rec.peptones, rec.ratios):
                print(f"     - {pep.name:15} {ratio*100:5.1f}%")
            if rec.rationale:
                print(f"   Rationale: {rec.rationale}")

    # Save results if requested
    if args.output:
        import pandas as pd

        results = []
        if args.mode in ['single', 'all']:
            for rec in recs:
                results.append(rec.to_dict())

        if args.mode in ['blend', 'all']:
            for rec in blend_recs:
                results.append(rec.to_dict())

        df = pd.DataFrame(results)
        df.to_csv(args.output, index=False, encoding='utf-8-sig')
        print(f"\n\nResults saved to: {args.output}")


def list_command(args):
    """Handle list command"""

    # Load databases
    strain_db, peptone_db = load_databases(args.strain_file, args.peptone_file)

    if args.type == 'strains':
        print("\n" + strain_db.get_summary())

        if args.category:
            strains = strain_db.get_strains_by_category(args.category)
            print(f"\n{args.category} strains ({len(strains)}):")
            for s in strains:
                print(f"  - {s.strain_id:20} {s.get_full_name()}")

    elif args.type == 'peptones':
        print("\n" + peptone_db.get_summary())

        if args.manufacturer:
            peptones = peptone_db.get_peptones_by_manufacturer(args.manufacturer)
            print(f"\n{args.manufacturer} peptones ({len(peptones)}):")
            for p in peptones:
                quality = p.get_quality_score()
                print(f"  - {p.name:20} Quality: {quality:.3f}")


def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Peptone Fit Model - Strain-based peptone recommendation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Recommend command
    rec_parser = subparsers.add_parser('recommend', help='Recommend peptones for a strain')
    rec_parser.add_argument('strain_id', help='Strain identifier (e.g., KCCM 12116)')
    rec_parser.add_argument('--mode', choices=['single', 'blend', 'all'], default='all',
                           help='Recommendation mode')
    rec_parser.add_argument('--top-n', type=int, default=5,
                           help='Number of recommendations (default: 5)')
    rec_parser.add_argument('--max-components', type=int, default=3, choices=[2, 3],
                           help='Maximum components in blend (default: 3)')
    rec_parser.add_argument('--sempio-only', action='store_true', default=True,
                           help='Only recommend Sempio products')
    rec_parser.add_argument('--all-products', action='store_true',
                           help='Include all manufacturers (not just Sempio)')
    rec_parser.add_argument('--strain-file', help='Path to strain Excel file')
    rec_parser.add_argument('--peptone-file', help='Path to peptone Excel file')
    rec_parser.add_argument('--output', '-o', help='Save results to CSV file')
    rec_parser.set_defaults(func=recommend_command)

    # List command
    list_parser = subparsers.add_parser('list', help='List strains or peptones')
    list_parser.add_argument('type', choices=['strains', 'peptones'],
                            help='What to list')
    list_parser.add_argument('--category', help='Filter strains by category')
    list_parser.add_argument('--manufacturer', help='Filter peptones by manufacturer')
    list_parser.add_argument('--strain-file', help='Path to strain Excel file')
    list_parser.add_argument('--peptone-file', help='Path to peptone Excel file')
    list_parser.set_defaults(func=list_command)

    # Parse arguments
    args = parser.parse_args()

    # Handle --all-products flag
    if hasattr(args, 'all_products') and args.all_products:
        args.sempio_only = False

    # Execute command
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
