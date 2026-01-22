"""
Peptone Fit Model - Streamlit Web Application
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Optional

# Set page config
st.set_page_config(
    page_title="Peptone Fit Model",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import modules
from src.strain_manager import StrainDatabase, StrainProfile
from src.peptone_analyzer import PeptoneDatabase, PeptoneProduct
from src.recommendation_engine import PeptoneRecommender
from src.recommendation_engine_v2 import EnhancedPeptoneRecommender
from src.blend_optimizer import BlendOptimizer
from src.visualization import RecommendationVisualizer


# Initialize session state
if 'strain_db' not in st.session_state:
    st.session_state.strain_db = None
if 'peptone_db' not in st.session_state:
    st.session_state.peptone_db = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'selected_strain' not in st.session_state:
    st.session_state.selected_strain = None


def get_file_mtime(filepath):
    """Get file modification time for cache invalidation"""
    return filepath.stat().st_mtime if filepath.exists() else 0

@st.cache_resource
def load_databases(_strain_mtime, _peptone_mtime):
    """Load strain and peptone databases (cached with file modification time check)"""
    try:
        strain_db = StrainDatabase()
        peptone_db = PeptoneDatabase()

        # Try to load from CSV files (for Streamlit Cloud deployment)
        strain_file = Path(__file__).parent.parent / "data" / "strains.csv"
        peptone_file = Path(__file__).parent.parent / "data" / "peptones.csv"

        if strain_file.exists() and peptone_file.exists():
            strain_db.load_from_csv(str(strain_file))
            peptone_db.load_from_csv(str(peptone_file))
            return strain_db, peptone_db, None
        else:
            # Fallback to Excel files (for local development)
            strain_file_excel = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
            peptone_file_excel = Path(r"D:\folder1\composition_template.xlsx")

            if strain_file_excel.exists() and peptone_file_excel.exists():
                strain_db.load_from_excel(str(strain_file_excel))
                peptone_db.load_from_excel(str(peptone_file_excel))
                return strain_db, peptone_db, None
            else:
                return None, None, "Data files not found. Please check file paths."
    except Exception as e:
        return None, None, f"Error loading databases: {str(e)}"


def main():
    """Main application"""

    # Header
    st.title("🧬 Peptone Fit Model")
    st.markdown("### AI-Powered Peptone Recommendation System")
    st.markdown("---")

    # Load databases (with file modification time for cache invalidation)
    strain_file = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
    peptone_file = Path(r"D:\folder1\composition_template.xlsx")

    with st.spinner("Loading databases..."):
        strain_db, peptone_db, error = load_databases(
            get_file_mtime(strain_file),
            get_file_mtime(peptone_file)
        )

    if error:
        st.error(error)
        st.info("Please ensure the data files are in the correct location.")
        return

    if strain_db is None or peptone_db is None:
        st.error("Failed to load databases")
        return

    # Store in session state
    st.session_state.strain_db = strain_db
    st.session_state.peptone_db = peptone_db

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Home", "🔍 Single Recommendation", "⚗️ Blend Optimization",
             "📊 Batch Processing", "📈 Advanced Analysis", "ℹ️ About"]
        )

        st.markdown("---")

        # Database info
        st.subheader("📚 Database Info")
        st.metric("Total Strains", len(strain_db.strains))
        st.metric("Total Peptones", len(peptone_db.peptones))
        st.metric("Sempio Products", len(peptone_db.get_sempio_peptones()))

        # Category breakdown
        with st.expander("Strain Categories"):
            cat_counts = strain_db.get_category_counts()
            for cat, count in cat_counts.items():
                st.text(f"{cat}: {count}")

    # Main content based on page selection
    if page == "🏠 Home":
        show_home_page(strain_db, peptone_db)
    elif page == "🔍 Single Recommendation":
        show_single_recommendation_page(strain_db, peptone_db)
    elif page == "⚗️ Blend Optimization":
        show_blend_optimization_page(strain_db, peptone_db)
    elif page == "📊 Batch Processing":
        show_batch_processing_page(strain_db, peptone_db)
    elif page == "📈 Advanced Analysis":
        show_advanced_analysis_page(strain_db, peptone_db)
    elif page == "ℹ️ About":
        show_about_page()


def show_home_page(strain_db, peptone_db):
    """Home page"""

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Welcome to Peptone Fit Model")
        st.markdown("""
        This application helps you find the optimal peptone products for your microbial strains
        using advanced algorithms and metabolic pathway analysis.

        ### 🎯 Key Features

        - **Smart Recommendations**: AI-powered peptone selection based on strain characteristics
        - **Blend Optimization**: Scipy-based optimization for perfect peptone blends (2-3 components)
        - **KEGG Integration**: Metabolic pathway analysis for precise nutritional requirements
        - **Interactive Visualization**: Beautiful charts and comprehensive reports
        - **Batch Processing**: Process multiple strains at once

        ### 🚀 Quick Start

        1. Navigate to **Single Recommendation** for quick peptone suggestions
        2. Try **Blend Optimization** for optimized multi-component blends
        3. Use **Batch Processing** for multiple strains

        ### 📊 Current Database
        """)

        # Database summary
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.metric("Strains", len(strain_db.strains),
                     delta=f"{len(strain_db.get_public_strains())} public")

        with col_b:
            st.metric("Peptones", len(peptone_db.peptones),
                     delta=f"{len(peptone_db.get_sempio_peptones())} Sempio")

        with col_c:
            st.metric("Categories", len(strain_db.get_category_counts()))

    with col2:
        st.subheader("📦 System Status")
        st.success("✓ Databases Loaded")
        st.success("✓ Recommendation Engine Ready")
        st.success("✓ Optimization Algorithms Ready")
        st.success("✓ Visualization Ready")

        st.markdown("---")

        st.subheader("📈 Strain Distribution")

        # Pie chart of categories
        cat_counts = strain_db.get_category_counts()
        fig = go.Figure(data=[go.Pie(
            labels=list(cat_counts.keys()),
            values=list(cat_counts.values()),
            hole=0.4
        )])
        fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    # Recent activity or example
    st.markdown("---")
    st.subheader("📌 Example: L. plantarum KCCM 12116")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
        **Category**: LAB
        **Type**: Fastidious
        **Requirements**: High amino acids, vitamins
        """)

    with col2:
        st.success("""
        **Top Recommendation**
        Pork peptoneS
        Score: 0.203
        """)

    with col3:
        st.warning("""
        **Best Blend**
        Pork 80% + PEA-BIO 20%
        Score: 0.215
        """)


def show_single_recommendation_page(strain_db, peptone_db):
    """Single peptone recommendation page"""

    st.header("🔍 Single Peptone Recommendation")
    st.markdown("Get recommendations for a single strain")
    st.markdown("---")

    # Strain selection
    col1, col2 = st.columns([2, 1])

    with col1:
        # Category filter
        categories = ["All"] + list(strain_db.get_category_counts().keys())
        selected_category = st.selectbox("Filter by Category", categories)

        # Get strains
        if selected_category == "All":
            strains = strain_db.strains
        else:
            strains = strain_db.get_strains_by_category(selected_category)

        # Strain selection
        strain_names = [f"{s.strain_id}: {s.get_full_name()}" for s in strains]
        selected_strain_name = st.selectbox("Select Strain", strain_names)

        # Get selected strain
        strain_id = selected_strain_name.split(":")[0].strip()
        strain = strain_db.get_strain_by_id(strain_id)

    with col2:
        st.subheader("Settings")

        sempio_only = st.checkbox("Sempio Products Only", value=True)
        top_n = st.slider("Number of Recommendations", 3, 10, 5)
        use_kegg = st.checkbox("Use KEGG Pathway Analysis", value=True,
                              help="More accurate recommendations using metabolic pathway data")

        if use_kegg:
            kegg_cache_only = st.checkbox("Use cached data only (faster)", value=True,
                                        help="Only use pre-cached KEGG data, no API calls")

    # Display strain info
    if strain:
        st.markdown("---")
        st.subheader("📋 Strain Information")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Strain ID", strain.strain_id)
        with col2:
            st.metric("Category", strain.category)
        with col3:
            st.metric("Temperature", f"{strain.temperature}°C")
        with col4:
            st.metric("Medium", strain.medium)

        st.text(f"Full Name: {strain.get_full_name()}")
        st.text(f"Nutritional Type: {strain.get_nutritional_type()}")
        st.text(f"Key Requirements: {', '.join(strain.get_key_requirements())}")

    # Recommend button
    st.markdown("---")

    if st.button("🚀 Generate Recommendations", type="primary"):
        with st.spinner("Analyzing strain and generating recommendations..."):

            # Create recommender
            if use_kegg:
                recommender = EnhancedPeptoneRecommender(
                    strain_db, peptone_db,
                    use_kegg=True,
                    kegg_cache_only=kegg_cache_only
                )
                recs = recommender.recommend_with_pathways(
                    strain.strain_id, top_n=top_n, sempio_only=sempio_only
                )
            else:
                recommender = PeptoneRecommender(strain_db, peptone_db)
                recs = recommender.recommend_single(
                    strain.strain_id, top_n=top_n, sempio_only=sempio_only
                )

            st.session_state.recommendations = recs
            st.session_state.selected_strain = strain

    # Display results
    if st.session_state.recommendations:
        recs = st.session_state.recommendations

        st.markdown("---")
        st.subheader("🎯 Recommendations")

        # Create results table
        results_data = []
        for i, rec in enumerate(recs, 1):
            results_data.append({
                'Rank': i,
                'Peptone': rec.peptones[0].name,
                'Manufacturer': rec.peptones[0].manufacturer,
                'Score': f"{rec.overall_score:.3f}",
                'Nutritional': f"{rec.detailed_scores['nutritional_match']:.3f}",
                'Amino Acids': f"{rec.detailed_scores['amino_acid_match']:.3f}",
                'Growth Factors': f"{rec.detailed_scores['growth_factor_match']:.3f}",
                'MW Distribution': f"{rec.detailed_scores['mw_distribution_match']:.3f}",
                'Rationale': rec.rationale
            })

        df = pd.DataFrame(results_data)
        st.dataframe(df, use_container_width=True, height=400)

        # Visualization
        st.markdown("---")
        st.subheader("📊 Visualization")

        tab1, tab2, tab3 = st.tabs(["Score Comparison", "Detailed Breakdown", "Amino Acid Profile"])

        with tab1:
            # Bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[f"#{i+1} {rec.peptones[0].name}" for i, rec in enumerate(recs)],
                y=[rec.overall_score for rec in recs],
                marker_color=px.colors.qualitative.Set2[:len(recs)],
                text=[f"{rec.overall_score:.3f}" for rec in recs],
                textposition='auto'
            ))
            fig.update_layout(
                title="Recommendation Scores",
                xaxis_title="Peptone",
                yaxis_title="Fitness Score",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # Radar chart for top recommendation
            top_rec = recs[0]
            categories = list(top_rec.detailed_scores.keys())
            values = list(top_rec.detailed_scores.values())

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=top_rec.peptones[0].name
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                title=f"Detailed Score: {top_rec.peptones[0].name}",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            # Amino acid heatmap
            visualizer = RecommendationVisualizer()
            peptones = [rec.peptones[0] for rec in recs[:5]]
            fig = visualizer.plot_amino_acid_profile(peptones, profile_type='free')
            st.plotly_chart(fig, use_container_width=True)

        # Export
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            # CSV export
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Results (CSV)",
                data=csv,
                file_name=f"recommendations_{strain.strain_id}.csv",
                mime="text/csv"
            )

        with col2:
            # Generate HTML report
            if st.button("📄 Generate HTML Report"):
                with st.spinner("Generating report..."):
                    output_file = f"report_{strain.strain_id}.html"
                    visualizer.create_recommendation_report(
                        strain, recs, output_file=output_file
                    )
                    st.success(f"Report saved: {output_file}")


def show_blend_optimization_page(strain_db, peptone_db):
    """Blend optimization page"""

    st.header("⚗️ Blend Optimization")
    st.markdown("Optimize peptone blend ratios using scipy algorithms")
    st.markdown("---")

    # Strain selection
    col1, col2 = st.columns([2, 1])

    with col1:
        strains = strain_db.strains
        strain_names = [f"{s.strain_id}: {s.get_full_name()}" for s in strains]
        selected_strain_name = st.selectbox("Select Strain", strain_names, key="blend_strain")

        strain_id = selected_strain_name.split(":")[0].strip()
        strain = strain_db.get_strain_by_id(strain_id)

    with col2:
        st.subheader("Optimization Settings")
        max_components = st.slider("Max Components", 2, 3, 3)
        top_n = st.slider("Results to Show", 3, 10, 5)
        sempio_only = st.checkbox("Sempio Only", value=True, key="blend_sempio")
        use_optimizer = st.checkbox("Use Scipy Optimizer", value=True,
                                   help="More accurate but slower")
        use_kegg_blend = st.checkbox("Use KEGG Analysis", value=True, key="blend_kegg",
                                    help="Include metabolic pathway data")
        if use_kegg_blend:
            kegg_cache_only_blend = st.checkbox("Cached data only", value=True, key="blend_kegg_cache",
                                              help="Faster, uses pre-cached data")

    # Generate button
    if st.button("🔬 Optimize Blend", type="primary"):
        with st.spinner("Running optimization algorithm..."):

            # Create enhanced recommender
            recommender = EnhancedPeptoneRecommender(
                strain_db, peptone_db,
                use_kegg=use_kegg_blend,
                kegg_cache_only=kegg_cache_only_blend if use_kegg_blend else False
            )

            # Get optimized blends
            recs = recommender.recommend_optimized_blend(
                strain.strain_id,
                max_components=max_components,
                top_n=top_n,
                sempio_only=sempio_only,
                use_optimizer=use_optimizer
            )

            st.session_state.recommendations = recs
            st.session_state.selected_strain = strain

    # Display results
    if st.session_state.recommendations:
        recs = st.session_state.recommendations

        st.markdown("---")
        st.subheader("🎯 Optimized Blends")

        # Display each blend
        for i, rec in enumerate(recs, 1):
            with st.expander(f"#{i} - {rec.get_description()} (Score: {rec.overall_score:.3f})",
                           expanded=(i==1)):

                col1, col2 = st.columns([1, 1])

                with col1:
                    st.markdown("**Composition:**")
                    for pep, ratio in zip(rec.peptones, rec.ratios):
                        st.progress(ratio, text=f"{pep.name}: {ratio*100:.1f}%")

                    st.markdown(f"**Rationale:** {rec.rationale}")

                with col2:
                    # Pie chart
                    fig = go.Figure(data=[go.Pie(
                        labels=[p.name for p in rec.peptones],
                        values=rec.ratios,
                        textinfo='label+percent'
                    )])
                    fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)

                # Detailed scores
                st.markdown("**Detailed Scores:**")
                score_cols = st.columns(4)
                for idx, (key, value) in enumerate(rec.detailed_scores.items()):
                    with score_cols[idx % 4]:
                        st.metric(key.replace('_', ' ').title(), f"{value:.3f}")

        # Comparison chart
        st.markdown("---")
        st.subheader("📊 Blend Comparison")

        fig = go.Figure()
        for i, rec in enumerate(recs):
            fig.add_trace(go.Bar(
                name=f"Blend #{i+1}",
                x=list(rec.detailed_scores.keys()),
                y=list(rec.detailed_scores.values())
            ))

        fig.update_layout(
            barmode='group',
            title="Score Components Comparison",
            xaxis_title="Component",
            yaxis_title="Score",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)


def show_batch_processing_page(strain_db, peptone_db):
    """Batch processing page"""

    st.header("📊 Batch Processing")
    st.markdown("Process multiple strains at once")
    st.markdown("---")

    # Strain selection
    st.subheader("1️⃣ Select Strains")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Category filter
        categories = list(strain_db.get_category_counts().keys())
        selected_categories = st.multiselect(
            "Filter by Categories",
            categories,
            default=["LAB"]
        )

        # Get strains from selected categories
        if selected_categories:
            selected_strains = []
            for cat in selected_categories:
                selected_strains.extend(strain_db.get_strains_by_category(cat))
        else:
            selected_strains = strain_db.strains

        # Strain selection
        strain_options = [f"{s.strain_id}: {s.get_full_name()}" for s in selected_strains]
        selected_strain_names = st.multiselect(
            "Select Strains to Process",
            strain_options,
            max_selections=10
        )

    with col2:
        st.subheader("Settings")
        top_n = st.number_input("Recommendations per Strain", 1, 10, 3)
        sempio_only = st.checkbox("Sempio Only", value=True, key="batch_sempio")
        mode = st.radio("Mode", ["Single", "Blend"], key="batch_mode")

    st.markdown("---")

    # Process button
    if st.button("🚀 Process Batch", type="primary", disabled=len(selected_strain_names)==0):

        progress_bar = st.progress(0)
        status_text = st.empty()

        results_list = []
        recommender = PeptoneRecommender(strain_db, peptone_db)

        for idx, strain_name in enumerate(selected_strain_names):
            strain_id = strain_name.split(":")[0].strip()
            status_text.text(f"Processing {strain_id}... ({idx+1}/{len(selected_strain_names)})")

            strain = strain_db.get_strain_by_id(strain_id)

            if mode == "Single":
                recs = recommender.recommend_single(strain_id, top_n=top_n, sempio_only=sempio_only)
            else:
                recs = recommender.recommend_blend(strain_id, max_components=3, top_n=top_n, sempio_only=sempio_only)

            # Store results
            for rank, rec in enumerate(recs, 1):
                results_list.append({
                    'Strain ID': strain_id,
                    'Strain Name': strain.get_full_name(),
                    'Category': strain.category,
                    'Rank': rank,
                    'Recommendation': rec.get_description(),
                    'Score': rec.overall_score,
                    'Rationale': rec.rationale
                })

            progress_bar.progress((idx + 1) / len(selected_strain_names))

        status_text.text("✓ Batch processing complete!")

        # Display results
        st.markdown("---")
        st.subheader("📋 Results")

        df = pd.DataFrame(results_list)
        st.dataframe(df, use_container_width=True, height=400)

        # Summary statistics
        st.markdown("---")
        st.subheader("📈 Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Strains Processed", len(selected_strain_names))
        with col2:
            st.metric("Total Recommendations", len(results_list))
        with col3:
            avg_score = df['Score'].mean()
            st.metric("Average Score", f"{avg_score:.3f}")

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Batch Results",
            data=csv,
            file_name="batch_results.csv",
            mime="text/csv"
        )


def show_advanced_analysis_page(strain_db, peptone_db):
    """Advanced analysis page"""

    st.header("📈 Advanced Analysis")
    st.markdown("Explore data and perform custom analysis")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Database Explorer", "Sensitivity Analysis", "Custom Optimization"])

    with tab1:
        st.subheader("🔍 Database Explorer")

        analysis_type = st.radio("Select Analysis", ["Strains", "Peptones"])

        if analysis_type == "Strains":
            # Strain analysis
            st.markdown("### Strain Distribution")

            cat_counts = strain_db.get_category_counts()

            col1, col2 = st.columns(2)

            with col1:
                # Pie chart
                fig = go.Figure(data=[go.Pie(
                    labels=list(cat_counts.keys()),
                    values=list(cat_counts.values())
                )])
                fig.update_layout(title="Strain Categories", height=400)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Bar chart
                fig = go.Figure(data=[go.Bar(
                    x=list(cat_counts.keys()),
                    y=list(cat_counts.values())
                )])
                fig.update_layout(title="Category Counts", height=400)
                st.plotly_chart(fig, use_container_width=True)

            # Strain table
            st.markdown("### All Strains")
            df = strain_db.to_dataframe()
            st.dataframe(df, use_container_width=True, height=400)

        else:
            # Peptone analysis
            st.markdown("### Peptone Analysis")

            df = peptone_db.to_dataframe()

            col1, col2 = st.columns(2)

            with col1:
                # Quality score distribution
                fig = go.Figure(data=[go.Histogram(
                    x=df['quality_score'],
                    nbinsx=20
                )])
                fig.update_layout(title="Quality Score Distribution", height=400)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Manufacturer distribution
                manufacturer_counts = df['manufacturer'].value_counts()
                fig = go.Figure(data=[go.Bar(
                    x=manufacturer_counts.index,
                    y=manufacturer_counts.values
                )])
                fig.update_layout(title="Peptones by Manufacturer", height=400)
                st.plotly_chart(fig, use_container_width=True)

            # Peptone table
            st.markdown("### All Peptones")
            st.dataframe(df, use_container_width=True, height=400)

    with tab2:
        st.subheader("🔬 Sensitivity Analysis")
        st.info("Analyze how blend ratios affect fitness scores")

        # Select peptones
        sempio = peptone_db.get_sempio_peptones()
        peptone_names = [p.name for p in sempio]

        col1, col2 = st.columns(2)

        with col1:
            peptone1_name = st.selectbox("Peptone 1", peptone_names, index=0)
        with col2:
            peptone2_name = st.selectbox("Peptone 2", peptone_names, index=1)

        if peptone1_name != peptone2_name:
            if st.button("Run Sensitivity Analysis"):
                with st.spinner("Calculating..."):
                    peptone1 = peptone_db.get_peptone_by_name(peptone1_name)
                    peptone2 = peptone_db.get_peptone_by_name(peptone2_name)

                    # Get a test strain
                    strain = strain_db.strains[0]
                    recommender = PeptoneRecommender(strain_db, peptone_db)

                    # Test different ratios
                    ratios = np.linspace(0, 1, 21)
                    scores = []

                    for r1 in ratios:
                        r2 = 1 - r1
                        if r1 >= 0.1 and r2 >= 0.1:  # Respect constraints
                            score, _ = recommender._evaluate_blend(
                                strain, [peptone1, peptone2], [r1, r2]
                            )
                            scores.append(score)
                        else:
                            scores.append(None)

                    # Plot
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=ratios * 100,
                        y=scores,
                        mode='lines+markers',
                        name='Fitness Score'
                    ))
                    fig.update_layout(
                        title=f"Sensitivity: {peptone1_name} vs {peptone2_name}",
                        xaxis_title=f"{peptone1_name} Ratio (%)",
                        yaxis_title="Fitness Score",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("🎛️ Custom Optimization")
        st.info("Define custom target profile and optimize")

        # Select peptones
        sempio = peptone_db.get_sempio_peptones()
        peptone_names = [p.name for p in sempio]

        selected_peptones_names = st.multiselect(
            "Select Peptones (2-3)",
            peptone_names,
            max_selections=3
        )

        if len(selected_peptones_names) >= 2:
            st.markdown("### Target Profile")

            col1, col2 = st.columns(2)

            with col1:
                target_tn = st.slider("Total Nitrogen", 0.0, 1.0, 0.8)
                target_an = st.slider("Amino Nitrogen", 0.0, 1.0, 0.7)
                target_aa = st.slider("Essential AA", 0.0, 1.0, 0.65)

            with col2:
                target_free = st.slider("Free AA", 0.0, 1.0, 0.55)
                target_nucl = st.slider("Nucleotides", 0.0, 1.0, 0.4)
                target_vit = st.slider("Vitamins", 0.0, 1.0, 0.3)

            if st.button("🔧 Optimize Custom Blend"):
                with st.spinner("Optimizing..."):
                    from src.blend_optimizer import BlendOptimizer

                    optimizer = BlendOptimizer()
                    peptones = [peptone_db.get_peptone_by_name(name)
                               for name in selected_peptones_names]

                    target = {
                        'TN': target_tn,
                        'AN': target_an,
                        'essential_aa': target_aa,
                        'free_aa': target_free,
                        'nucleotide': target_nucl,
                        'vitamin': target_vit
                    }

                    result = optimizer.optimize_ratio(peptones, target, method='SLSQP')

                    if result.success:
                        st.success("✓ Optimization Successful!")

                        st.markdown("### Optimal Blend")
                        for pep, ratio in zip(result.peptones, result.optimal_ratios):
                            st.progress(ratio, text=f"{pep.name}: {ratio*100:.1f}%")

                        st.metric("Final Score", f"{result.final_score:.6f}")
                        st.text(f"Iterations: {result.iterations}")
                    else:
                        st.error("Optimization failed")
                        st.text(result.message)


def show_about_page():
    """About page"""

    st.header("ℹ️ About Peptone Fit Model")

    st.markdown("""
    ### 🧬 Peptone Fit Model v2.0

    An AI-powered system for recommending optimal peptone products based on microbial strain characteristics.

    ### 🎯 Features

    #### Phase 1: Basic Recommendation
    - 56 strain database with automatic categorization
    - 49 peptone products with 94 nutritional components
    - Multi-factor fitness scoring algorithm
    - Single and blend recommendations

    #### Phase 2: External DB Integration
    - KEGG REST API integration (24 metabolic pathways)
    - NCBI Taxonomy lookup
    - Pathway-based nutritional requirement inference
    - Local caching system (30-day expiry)

    #### Phase 3: Advanced Optimization
    - Scipy-based optimization (SLSQP, Differential Evolution)
    - Complementarity-based peptone selection
    - Pathway data-integrated scoring
    - Interactive visualizations (6 chart types)
    - Automated HTML report generation

    #### Phase 4: Web Interface (Current)
    - Streamlit-based web application
    - Interactive parameter adjustment
    - Real-time visualization
    - Batch processing interface
    - Export functionality

    ### 📊 Algorithm

    **Fitness Score Calculation:**
    ```
    Total Score = Σ(Component Score × Weight) × (1 + Pathway Bonus × 0.15)

    Components:
    - Nutritional Match (40%)
    - Amino Acid Profile (25%)
    - Growth Factors (20%)
    - MW Distribution (15%)
    ```

    **Blend Optimization:**
    ```python
    minimize: Σ((blended - target) × weights)²
    subject to:
      - Σ(ratios) = 1.0
      - 0.1 ≤ ratio_i ≤ 0.8
      - len(ratios) ≤ 5
    ```

    ### 📈 Performance

    - Single Recommendation: <0.1s
    - Blend Optimization: <5s
    - KEGG API (cached): <0.01s
    - Memory Usage: ~50MB

    ### 👥 Credits

    **Development:** Sempio R&D Team
    **Version:** 2.0
    **Date:** 2025-01-21

    ### 📚 Documentation

    - `README.md`: Project overview
    - `USAGE_V2.md`: Detailed usage guide
    - `PHASE1_COMPLETE.md`: Phase 1 report
    - `PHASE2_3_COMPLETE.md`: Phase 2&3 report
    - `FINAL_SUMMARY.md`: Complete summary

    ### 🔗 Resources

    - KEGG Database: https://www.kegg.jp/
    - NCBI Taxonomy: https://www.ncbi.nlm.nih.gov/taxonomy
    - Scipy Optimization: https://docs.scipy.org/doc/scipy/reference/optimize.html

    ### 📄 License

    Internal use only - Sempio
    """)


if __name__ == "__main__":
    main()
