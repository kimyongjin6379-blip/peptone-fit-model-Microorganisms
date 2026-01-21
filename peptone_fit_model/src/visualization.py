"""
Visualization Module

Creates charts and visualizations for recommendation results
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .recommendation_engine import RecommendationResult
from .peptone_analyzer import PeptoneProduct
from .strain_manager import StrainProfile


class RecommendationVisualizer:
    """Creates visualizations for peptone recommendations"""

    def __init__(self, style: str = 'plotly'):
        """
        Initialize visualizer

        Args:
            style: Visualization style ('plotly', 'simple')
        """
        self.style = style
        self.color_scheme = px.colors.qualitative.Set2

    def plot_score_comparison(self,
                             recommendations: List[RecommendationResult],
                             title: str = "Peptone Recommendations") -> go.Figure:
        """
        Create bar chart comparing recommendation scores

        Args:
            recommendations: List of recommendations
            title: Chart title

        Returns:
            Plotly Figure object
        """
        # Extract data
        names = [rec.get_description() for rec in recommendations]
        scores = [rec.overall_score for rec in recommendations]

        # Create bar chart
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=names,
            y=scores,
            marker_color=self.color_scheme[:len(names)],
            text=[f"{s:.3f}" for s in scores],
            textposition='auto',
        ))

        fig.update_layout(
            title=title,
            xaxis_title="Peptone/Blend",
            yaxis_title="Fitness Score",
            yaxis_range=[0, 1.0],
            height=500,
            showlegend=False
        )

        return fig

    def plot_detailed_scores(self,
                            recommendation: RecommendationResult,
                            title: Optional[str] = None) -> go.Figure:
        """
        Create radar chart showing detailed score breakdown

        Args:
            recommendation: Recommendation to visualize
            title: Optional chart title

        Returns:
            Plotly Figure object
        """
        if title is None:
            title = f"Score Breakdown: {recommendation.get_description()}"

        # Extract detailed scores
        categories = list(recommendation.detailed_scores.keys())
        values = list(recommendation.detailed_scores.values())

        # Create radar chart
        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Score'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            title=title,
            height=500
        )

        return fig

    def plot_amino_acid_profile(self,
                               peptones: List[PeptoneProduct],
                               profile_type: str = 'free') -> go.Figure:
        """
        Create heatmap of amino acid profiles

        Args:
            peptones: List of peptones to compare
            profile_type: 'free' or 'total'

        Returns:
            Plotly Figure object
        """
        # Amino acids to display
        amino_acids = [
            'Threonine', 'Valine', 'Methionine', 'Isoleucine',
            'Leucine', 'Phenylalanine', 'Tryptophan', 'Lysine',
            'Histidine', 'Arginine'
        ]

        # Extract data
        data = []
        peptone_names = []

        prefix = 'faa_' if profile_type == 'free' else 'taa_'

        for peptone in peptones:
            aa_dict = (peptone.profile.free_amino_acids if profile_type == 'free'
                      else peptone.profile.total_amino_acids)

            row = [aa_dict.get(f'{prefix}{aa}', 0) for aa in amino_acids]
            data.append(row)
            peptone_names.append(peptone.name)

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=amino_acids,
            y=peptone_names,
            colorscale='YlOrRd',
            text=np.round(data, 2),
            texttemplate='%{text}',
            textfont={"size": 10},
        ))

        profile_name = "Free" if profile_type == 'free' else "Total"
        fig.update_layout(
            title=f"{profile_name} Amino Acid Profile Comparison",
            xaxis_title="Amino Acid",
            yaxis_title="Peptone",
            height=400 + len(peptones) * 30
        )

        return fig

    def plot_blend_composition(self,
                              recommendation: RecommendationResult) -> go.Figure:
        """
        Create pie chart showing blend composition

        Args:
            recommendation: Blend recommendation

        Returns:
            Plotly Figure object
        """
        if len(recommendation.peptones) == 1:
            raise ValueError("Single peptone - no blend to visualize")

        labels = [p.name for p in recommendation.peptones]
        values = recommendation.ratios

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            textinfo='label+percent',
            textposition='inside',
            marker=dict(colors=self.color_scheme[:len(labels)])
        )])

        fig.update_layout(
            title=f"Blend Composition: {recommendation.get_description()}",
            height=500
        )

        return fig

    def plot_nutritional_comparison(self,
                                   peptones: List[PeptoneProduct],
                                   components: Optional[List[str]] = None) -> go.Figure:
        """
        Create grouped bar chart comparing nutritional components

        Args:
            peptones: Peptones to compare
            components: Optional list of components to display

        Returns:
            Plotly Figure object
        """
        if components is None:
            components = ['TN', 'AN', 'Nucleotides', 'Vitamins', 'Free AA Ratio']

        # Extract data
        data_dict = {comp: [] for comp in components}
        peptone_names = []

        for peptone in peptones:
            peptone_names.append(peptone.name)

            # TN
            if 'TN' in components:
                data_dict['TN'].append(peptone.profile.general.get('general_TN', 0))

            # AN
            if 'AN' in components:
                data_dict['AN'].append(peptone.profile.general.get('general_AN', 0))

            # Nucleotides
            if 'Nucleotides' in components:
                data_dict['Nucleotides'].append(sum(peptone.profile.nucleotides.values()))

            # Vitamins
            if 'Vitamins' in components:
                data_dict['Vitamins'].append(sum(peptone.profile.vitamins.values()))

            # Free AA Ratio
            if 'Free AA Ratio' in components:
                data_dict['Free AA Ratio'].append(peptone.profile.get_free_aa_ratio() * 100)

        # Create grouped bar chart
        fig = go.Figure()

        for i, component in enumerate(components):
            fig.add_trace(go.Bar(
                name=component,
                x=peptone_names,
                y=data_dict[component],
                marker_color=self.color_scheme[i % len(self.color_scheme)]
            ))

        fig.update_layout(
            title="Nutritional Component Comparison",
            xaxis_title="Peptone",
            yaxis_title="Value",
            barmode='group',
            height=500,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig

    def create_recommendation_report(self,
                                    strain: StrainProfile,
                                    recommendations: List[RecommendationResult],
                                    output_file: Optional[str] = None) -> str:
        """
        Create comprehensive HTML report

        Args:
            strain: Target strain
            recommendations: List of recommendations
            output_file: Optional output HTML file path

        Returns:
            HTML string
        """
        html_parts = []

        # Header
        html_parts.append("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Peptone Recommendation Report</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #2c3e50; }
                h2 { color: #34495e; margin-top: 30px; }
                .strain-info { background-color: #ecf0f1; padding: 15px; border-radius: 5px; }
                .chart { margin: 20px 0; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #3498db; color: white; }
            </style>
        </head>
        <body>
        """)

        # Title
        html_parts.append("<h1>Peptone Recommendation Report</h1>")

        # Strain information
        html_parts.append("<h2>Target Strain</h2>")
        html_parts.append('<div class="strain-info">')
        html_parts.append(f"<p><strong>ID:</strong> {strain.strain_id}</p>")
        html_parts.append(f"<p><strong>Name:</strong> {strain.get_full_name()}</p>")
        html_parts.append(f"<p><strong>Category:</strong> {strain.category}</p>")
        html_parts.append(f"<p><strong>Nutritional Type:</strong> {strain.get_nutritional_type()}</p>")
        html_parts.append(f"<p><strong>Key Requirements:</strong> {', '.join(strain.get_key_requirements())}</p>")
        html_parts.append("</div>")

        # Score comparison chart
        html_parts.append("<h2>Recommendation Scores</h2>")
        fig1 = self.plot_score_comparison(recommendations)
        html_parts.append('<div class="chart">')
        html_parts.append(fig1.to_html(full_html=False, include_plotlyjs=False))
        html_parts.append('</div>')

        # Detailed recommendations table
        html_parts.append("<h2>Detailed Recommendations</h2>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Rank</th><th>Peptone/Blend</th><th>Score</th><th>Rationale</th></tr>")

        for i, rec in enumerate(recommendations, 1):
            html_parts.append(f"<tr>")
            html_parts.append(f"<td>{i}</td>")
            html_parts.append(f"<td>{rec.get_description()}</td>")
            html_parts.append(f"<td>{rec.overall_score:.3f}</td>")
            html_parts.append(f"<td>{rec.rationale}</td>")
            html_parts.append(f"</tr>")

        html_parts.append("</table>")

        # Detailed score breakdown for top recommendation
        if recommendations:
            html_parts.append("<h2>Top Recommendation Details</h2>")
            fig2 = self.plot_detailed_scores(recommendations[0])
            html_parts.append('<div class="chart">')
            html_parts.append(fig2.to_html(full_html=False, include_plotlyjs=False))
            html_parts.append('</div>')

        # Footer
        html_parts.append("""
        </body>
        </html>
        """)

        html_content = "\n".join(html_parts)

        # Save to file if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Report saved to: {output_file}")

        return html_content


if __name__ == "__main__":
    print("Testing visualization module...")

    from pathlib import Path

    strain_file = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
    peptone_file = Path(r"D:\folder1\composition_template.xlsx")

    if strain_file.exists() and peptone_file.exists():
        from .strain_manager import StrainDatabase
        from .peptone_analyzer import PeptoneDatabase
        from .recommendation_engine import PeptoneRecommender

        # Load databases
        strain_db = StrainDatabase()
        peptone_db = PeptoneDatabase()

        strain_db.load_from_excel(str(strain_file))
        peptone_db.load_from_excel(str(peptone_file))

        # Create recommender
        recommender = PeptoneRecommender(strain_db, peptone_db)

        # Get recommendations
        recs = recommender.recommend_single("KCCM 12116", top_n=5)

        # Create visualizations
        visualizer = RecommendationVisualizer()

        print("\n1. Creating score comparison chart...")
        fig1 = visualizer.plot_score_comparison(recs)
        fig1.write_html("score_comparison.html")
        print("   Saved to: score_comparison.html")

        print("\n2. Creating detailed score breakdown...")
        fig2 = visualizer.plot_detailed_scores(recs[0])
        fig2.write_html("score_details.html")
        print("   Saved to: score_details.html")

        print("\n3. Creating amino acid profile heatmap...")
        top_peptones = [rec.peptones[0] for rec in recs[:5]]
        fig3 = visualizer.plot_amino_acid_profile(top_peptones, profile_type='free')
        fig3.write_html("aa_profile.html")
        print("   Saved to: aa_profile.html")

        print("\n4. Creating comprehensive HTML report...")
        strain = strain_db.get_strain_by_id("KCCM 12116")
        visualizer.create_recommendation_report(
            strain, recs,
            output_file="recommendation_report.html"
        )

    else:
        print("Data files not found. Skipping tests.")

    print("\n\nVisualization test complete!")
