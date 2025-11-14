"""
Chart Generation Module
=======================
Plotly chart generators for Bidco retail analytics dashboard.
"""

import sys
from pathlib import Path

# Add src to path for imports
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root / "src"))

import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any


def create_quality_gauge(score: float, title: str = "Data Quality Score") -> go.Figure:
    """
    Create a gauge chart for quality score.
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score * 100,
        title={'text': title},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 60], 'color': "#ffcccc"},
                {'range': [60, 75], 'color': "#ffffcc"},
                {'range': [75, 90], 'color': "#ccffcc"},
                {'range': [90, 100], 'color': "#ccffff"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 75
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig


def create_market_share_pie(bidco_sales: float, total_sales: float) -> go.Figure:
    """
    Create pie chart showing market share.
    """
    other_sales = total_sales - bidco_sales
    
    fig = go.Figure(data=[go.Pie(
        labels=['Bidco', 'Other Suppliers'],
        values=[bidco_sales, other_sales],
        hole=0.4,
        marker_colors=['#FF6B6B', '#E8E8E8'],
        textinfo='label+percent',
        textfont_size=14
    )])
    
    fig.update_layout(
        title_text="Market Share",
        height=350,
        showlegend=True
    )
    
    return fig


def create_category_bar(categories: List[Dict]) -> go.Figure:
    """
    Create bar chart for category breakdown.
    """
    categories_sorted = sorted(categories, key=lambda x: x['sales'], reverse=True)
    
    fig = go.Figure(data=[
        go.Bar(
            x=[cat['category'] for cat in categories_sorted],
            y=[cat['sales'] for cat in categories_sorted],
            text=[f"{cat['sales_share_pct']:.1f}%" for cat in categories_sorted],
            textposition='outside',
            marker_color='#4ECDC4'
        )
    ])
    
    fig.update_layout(
        title_text="Sales by Category",
        xaxis_title="Category",
        yaxis_title="Sales (KES)",
        height=400
    )
    
    return fig


def create_top_products_bar(products: List[Dict], top_n: int = 10) -> go.Figure:
    """
    Create bar chart for top products.
    """
    products_sorted = sorted(products, key=lambda x: x['sales'], reverse=True)[:top_n]
    
    # Truncate long product names
    labels = [p['description'][:40] + '...' if len(p['description']) > 40 
              else p['description'] for p in products_sorted]
    
    fig = go.Figure(data=[
        go.Bar(
            y=labels,
            x=[p['sales'] for p in products_sorted],
            orientation='h',
            marker_color='#95E1D3',
            text=[f"KES {p['sales']:,.0f}" for p in products_sorted],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title_text=f"Top {top_n} Products by Sales",
        xaxis_title="Sales (KES)",
        yaxis_title="",
        height=500,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    return fig


def create_price_index_bar(category_indices: Dict[str, float]) -> go.Figure:
    """
    Create bar chart for price indices by category.
    """
    categories = list(category_indices.keys())
    indices = list(category_indices.values())
    
    # Color based on positioning
    colors = ['#FF6B6B' if idx > 1.1 else '#4ECDC4' if idx < 0.9 else '#FFE66D' 
              for idx in indices]
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=indices,
            marker_color=colors,
            text=[f"{idx:.2f}" for idx in indices],
            textposition='outside'
        )
    ])
    
    # Add reference lines
    fig.add_hline(y=1.1, line_dash="dash", line_color="red", 
                  annotation_text="Premium (>1.1)")
    fig.add_hline(y=0.9, line_dash="dash", line_color="blue", 
                  annotation_text="Discount (<0.9)")
    fig.add_hline(y=1.0, line_dash="solid", line_color="gray", 
                  annotation_text="At Market (1.0)")
    
    fig.update_layout(
        title_text="Price Index by Category",
        xaxis_title="Category",
        yaxis_title="Price Index (Bidco/Competitor Avg)",
        height=450,
        xaxis={'tickangle': -45}
    )
    
    return fig


def create_store_rankings_bar(stores: List[Dict], top_n: int = 10) -> go.Figure:
    """
    Create bar chart for top stores by sales.
    """
    stores_sorted = sorted(stores, key=lambda x: x['sales'], reverse=True)[:top_n]
    
    fig = go.Figure(data=[
        go.Bar(
            x=[s['store'] for s in stores_sorted],
            y=[s['sales'] for s in stores_sorted],
            marker_color='#F38181',
            text=[f"KES {s['sales']:,.0f}" for s in stores_sorted],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title_text=f"Top {top_n} Stores by Sales",
        xaxis_title="Store",
        yaxis_title="Sales (KES)",
        height=400,
        xaxis={'tickangle': -45}
    )
    
    return fig


def create_metrics_cards_html(metrics: Dict[str, str]) -> str:
    """
    Create HTML for metric cards.
    """
    cards_html = '<div style="display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0;">'
    
    for metric, value in metrics.items():
        cards_html += f'''
        <div style="
            flex: 1;
            min-width: 200px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: white;
        ">
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 10px;">
                {metric.replace('_', ' ').title()}
            </div>
            <div style="font-size: 24px; font-weight: bold;">
                {value}
            </div>
        </div>
        '''
    
    cards_html += '</div>'
    return cards_html


def create_insights_html(insights: List[str]) -> str:
    """
    Create HTML for insights section.
    """
    if not insights:
        return ""
    
    insights_html = '''
    <div style="
        margin: 30px 0;
        padding: 20px;
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        border-radius: 5px;
    ">
        <h3 style="margin-top: 0; color: #667eea;">💡 Key Insights</h3>
        <ul style="line-height: 1.8;">
    '''
    
    for insight in insights:
        insights_html += f'<li>{insight}</li>'
    
    insights_html += '</ul></div>'
    return insights_html

####----UNCOMMENT TO TEST ---###


# if __name__ == "__main__":
#     """Test chart generation"""
    
#     print("=" * 80)
#     print("CHART GENERATION TEST")
#     print("=" * 80)
#     print()
    
#     # Test quality gauge
#     fig = create_quality_gauge(0.79, "Bidco Quality Score")
#     print(" Quality gauge created")
    
#     # Test market share pie
#     fig = create_market_share_pie(1100000, 14000000)
#     print("Market share pie created")
    
#     # Test category bar
#     categories = [
#         {"category": "FOODS", "sales": 800000, "sales_share_pct": 74.2},
#         {"category": "HOMECARE", "sales": 280000, "sales_share_pct": 25.7}
#     ]
#     fig = create_category_bar(categories)
#     print(" Category bar chart created")
    
#     # Test metrics cards
#     metrics = {
#         "market_share": "7.84%",
#         "total_sales": "KES 1.1M",
#         "quality_grade": "C"
#     }
#     html = create_metrics_cards_html(metrics)
#     print(" Metrics cards HTML created")
    
#     print()
#     print("=" * 80)
#     print(" All chart generators working!")
#     print("=" * 80)