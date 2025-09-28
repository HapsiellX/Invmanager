"""
Analytics views for comprehensive inventory reporting
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any

from core.security import require_auth, require_role
from core.database import get_db
from .services import get_analytics_service


@require_auth
@require_role("netzwerker")
def show_analytics_page():
    """
    Comprehensive analytics dashboard (requires netzwerker role or higher)
    """
    st.header("📈 Analytics & Berichte")

    # Get database session and analytics service
    db = next(get_db())
    analytics_service = get_analytics_service(db)

    # Create tabs for different analytics views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Übersicht", "📦 Inventar", "⚠️ Bestände", "📈 Trends", "🏢 Standorte", "📋 Aktivitäten"
    ])

    with tab1:
        show_overview_dashboard(analytics_service)

    with tab2:
        show_inventory_analytics(analytics_service)

    with tab3:
        show_stock_alerts(analytics_service)

    with tab4:
        show_trends_analysis(analytics_service)

    with tab5:
        show_location_analytics(analytics_service)

    with tab6:
        show_activity_timeline(analytics_service)

    db.close()


def show_overview_dashboard(analytics_service):
    """Show main overview dashboard"""
    st.subheader("📊 Inventar Übersicht")

    # Get overview data
    overview = analytics_service.get_inventory_overview()

    # Display key metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🔧 Hardware Artikel",
            value=f"{overview['hardware']['total_items']:,}",
            delta=None
        )
        st.metric(
            label="💰 Hardware Wert",
            value=f"€{overview['hardware']['total_value']:,.2f}",
            delta=None
        )

    with col2:
        st.metric(
            label="🔌 Kabel Typen",
            value=f"{overview['cables']['total_types']:,}",
            delta=None
        )
        st.metric(
            label="💰 Kabel Wert",
            value=f"€{overview['cables']['total_value']:,.2f}",
            delta=None
        )

    with col3:
        st.metric(
            label="📦 Kabel Anzahl",
            value=f"{overview['cables']['total_quantity']:,}",
            delta=None
        )
        st.metric(
            label="⚠️ Niedrige Bestände",
            value=overview['cables']['low_stock_count'],
            delta=None
        )

    with col4:
        st.metric(
            label="🏢 Standorte",
            value=f"{overview['locations']['total_locations']:,}",
            delta=None
        )
        total_value = overview['hardware']['total_value'] + overview['cables']['total_value']
        st.metric(
            label="💎 Gesamtwert",
            value=f"€{total_value:,.2f}",
            delta=None
        )

    # Top suppliers chart
    st.subheader("🏭 Top Lieferanten")
    suppliers = analytics_service.get_top_suppliers()

    if suppliers:
        df_suppliers = pd.DataFrame(suppliers[:10])  # Top 10

        fig = px.bar(
            df_suppliers,
            x='name',
            y='total_value',
            title='Top 10 Lieferanten nach Gesamtwert',
            labels={'name': 'Lieferant', 'total_value': 'Gesamtwert (€)'}
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Suppliers table
        st.dataframe(
            df_suppliers[['name', 'hardware_items', 'cable_items', 'total_items', 'total_value']],
            column_config={
                'name': 'Lieferant',
                'hardware_items': 'Hardware',
                'cable_items': 'Kabel',
                'total_items': 'Gesamt Artikel',
                'total_value': st.column_config.NumberColumn('Gesamtwert (€)', format="€%.2f")
            },
            hide_index=True
        )


def show_inventory_analytics(analytics_service):
    """Show detailed inventory analytics"""
    st.subheader("📦 Inventar Analyse")

    # Hardware by category
    hardware_categories = analytics_service.get_hardware_by_category()
    cable_types = analytics_service.get_cable_by_type()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔧 Hardware nach Kategorie")
        if hardware_categories:
            df_hw = pd.DataFrame(hardware_categories)

            # Pie chart for hardware categories
            fig_pie = px.pie(
                df_hw,
                values='count',
                names='category',
                title='Hardware Verteilung nach Kategorie'
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            # Table
            st.dataframe(
                df_hw,
                column_config={
                    'category': 'Kategorie',
                    'count': 'Anzahl',
                    'total_value': st.column_config.NumberColumn('Gesamtwert (€)', format="€%.2f")
                },
                hide_index=True
            )
        else:
            st.info("Keine Hardware Daten vorhanden")

    with col2:
        st.subheader("🔌 Kabel nach Typ")
        if cable_types:
            df_cables = pd.DataFrame(cable_types)

            # Treemap for cable types
            fig_tree = px.treemap(
                df_cables,
                path=['type', 'standard'],
                values='total_quantity',
                title='Kabel Verteilung nach Typ und Standard'
            )
            st.plotly_chart(fig_tree, use_container_width=True)

            # Table
            st.dataframe(
                df_cables,
                column_config={
                    'type': 'Typ',
                    'standard': 'Standard',
                    'types_count': 'Artikel Typen',
                    'total_quantity': 'Gesamtmenge',
                    'total_value': st.column_config.NumberColumn('Gesamtwert (€)', format="€%.2f")
                },
                hide_index=True
            )
        else:
            st.info("Keine Kabel Daten vorhanden")

    # Hardware by status
    st.subheader("📊 Hardware Status")
    hardware_status = analytics_service.get_hardware_by_status()

    if hardware_status:
        df_status = pd.DataFrame(hardware_status)

        fig_bar = px.bar(
            df_status,
            x='status',
            y='count',
            title='Hardware nach Status',
            labels={'status': 'Status', 'count': 'Anzahl'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)


def show_stock_alerts(analytics_service):
    """Show stock level alerts"""
    st.subheader("⚠️ Bestandswarnungen")

    stock_alerts = analytics_service.get_stock_alerts()

    # Display alert counts
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🔴 Niedriger Bestand",
            value=len(stock_alerts['low_stock']),
            delta=None
        )

    with col2:
        st.metric(
            label="🟡 Ausverkauft",
            value=len(stock_alerts['out_of_stock']),
            delta=None
        )

    with col3:
        st.metric(
            label="🟠 Überbestand",
            value=len(stock_alerts['high_stock']),
            delta=None
        )

    # Tabs for different alert types
    alert_tab1, alert_tab2, alert_tab3 = st.tabs(["🔴 Niedriger Bestand", "🟡 Ausverkauft", "🟠 Überbestand"])

    with alert_tab1:
        if stock_alerts['low_stock']:
            df_low = pd.DataFrame(stock_alerts['low_stock'])
            st.dataframe(
                df_low,
                column_config={
                    'type': 'Typ',
                    'standard': 'Standard',
                    'length': 'Länge (m)',
                    'current_stock': 'Aktueller Bestand',
                    'min_stock': 'Mindestbestand',
                    'location': 'Standort'
                },
                hide_index=True
            )
        else:
            st.success("Keine Artikel mit niedrigem Bestand")

    with alert_tab2:
        if stock_alerts['out_of_stock']:
            df_out = pd.DataFrame(stock_alerts['out_of_stock'])
            st.dataframe(
                df_out,
                column_config={
                    'type': 'Typ',
                    'standard': 'Standard',
                    'length': 'Länge (m)',
                    'min_stock': 'Mindestbestand',
                    'location': 'Standort'
                },
                hide_index=True
            )
        else:
            st.success("Keine ausverkauften Artikel")

    with alert_tab3:
        if stock_alerts['high_stock']:
            df_high = pd.DataFrame(stock_alerts['high_stock'])
            st.dataframe(
                df_high,
                column_config={
                    'type': 'Typ',
                    'standard': 'Standard',
                    'length': 'Länge (m)',
                    'current_stock': 'Aktueller Bestand',
                    'max_stock': 'Höchstbestand',
                    'location': 'Standort'
                },
                hide_index=True
            )
        else:
            st.success("Keine Artikel mit Überbestand")


def show_trends_analysis(analytics_service):
    """Show trends and historical analysis"""
    st.subheader("📈 Trend Analyse")

    # Time period selector
    period = st.selectbox(
        "Zeitraum auswählen:",
        ["30 Tage", "90 Tage", "6 Monate", "12 Monate"],
        index=1
    )

    days_map = {"30 Tage": 30, "90 Tage": 90, "6 Monate": 180, "12 Monate": 365}
    days = days_map[period]

    # Get trends data
    trends = analytics_service.get_value_trends(months=int(days/30))

    if trends['daily_transactions']:
        df_trends = pd.DataFrame(trends['daily_transactions'])
        df_trends['date'] = pd.to_datetime(df_trends['date'])

        # Create subplot with multiple y-axes
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Transaktions Trends', 'Netto Bewegungen'),
            vertical_spacing=0.1
        )

        # Transaction trends
        fig.add_trace(
            go.Scatter(x=df_trends['date'], y=df_trends['inbound'],
                      name='Eingänge', line=dict(color='green')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df_trends['date'], y=df_trends['outbound'],
                      name='Ausgänge', line=dict(color='red')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df_trends['date'], y=df_trends['transfer'],
                      name='Transfers', line=dict(color='blue')),
            row=1, col=1
        )

        # Net movements
        df_trends['net'] = df_trends['inbound'] - df_trends['outbound']
        fig.add_trace(
            go.Scatter(x=df_trends['date'], y=df_trends['net'],
                      name='Netto Bewegung', line=dict(color='purple')),
            row=2, col=1
        )

        fig.update_layout(height=600, title_text=f"Transaktions Trends - {period}")
        st.plotly_chart(fig, use_container_width=True)

        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Gesamt Eingänge", f"{df_trends['inbound'].sum():,}")
        with col2:
            st.metric("Gesamt Ausgänge", f"{df_trends['outbound'].sum():,}")
        with col3:
            st.metric("Netto Veränderung", f"{df_trends['net'].sum():,}")
    else:
        st.info(f"Keine Transaktionsdaten für den Zeitraum {period} verfügbar")


def show_location_analytics(analytics_service):
    """Show location-based analytics"""
    st.subheader("🏢 Standort Analyse")

    # Location distribution
    location_dist = analytics_service.get_location_inventory_distribution()
    space_util = analytics_service.get_space_utilization()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Inventar nach Standort")
        if location_dist:
            df_loc = pd.DataFrame(location_dist)

            # Stacked bar chart
            fig = go.Figure(data=[
                go.Bar(name='Hardware', x=df_loc['location_name'], y=df_loc['hardware_count']),
                go.Bar(name='Kabel', x=df_loc['location_name'], y=df_loc['cable_count'])
            ])

            fig.update_layout(
                barmode='stack',
                title='Inventar Verteilung nach Standort',
                xaxis_title='Standort',
                yaxis_title='Anzahl Artikel'
            )
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Table
            df_loc['total_items'] = df_loc['hardware_count'] + df_loc['cable_count']
            st.dataframe(
                df_loc,
                column_config={
                    'location_name': 'Standort',
                    'location_type': 'Typ',
                    'hardware_count': 'Hardware',
                    'cable_count': 'Kabel',
                    'total_items': 'Gesamt'
                },
                hide_index=True
            )
        else:
            st.info("Keine Standort Daten vorhanden")

    with col2:
        st.subheader("📦 Raum Auslastung")
        if space_util:
            df_space = pd.DataFrame(space_util[:15])  # Top 15 most utilized

            # Horizontal bar chart
            fig = px.bar(
                df_space,
                x='total_items',
                y='location_name',
                orientation='h',
                title='Top 15 Räume nach Auslastung',
                labels={'total_items': 'Anzahl Artikel', 'location_name': 'Raum'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Table
            st.dataframe(
                df_space,
                column_config={
                    'location_name': 'Raum',
                    'location_type': 'Typ',
                    'hardware_items': 'Hardware',
                    'cable_types': 'Kabel Typen',
                    'total_items': 'Gesamt Artikel',
                    'path': 'Vollständiger Pfad'
                },
                hide_index=True
            )
        else:
            st.info("Keine Raum Auslastungsdaten vorhanden")


def show_activity_timeline(analytics_service):
    """Show recent activity timeline"""
    st.subheader("📋 Aktivitäts Timeline")

    # Time period selector
    days = st.selectbox(
        "Zeitraum auswählen:",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda x: f"{x} Tage"
    )

    activities = analytics_service.get_activity_timeline(days=days)

    if activities:
        df_activities = pd.DataFrame(activities)

        # Activity type distribution
        activity_counts = df_activities['action'].value_counts()

        col1, col2 = st.columns(2)

        with col1:
            fig_pie = px.pie(
                values=activity_counts.values,
                names=activity_counts.index,
                title=f'Aktivitäts Verteilung - Letzte {days} Tage'
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            # Resource type distribution
            resource_counts = df_activities['resource_type'].value_counts()
            fig_bar = px.bar(
                x=resource_counts.index,
                y=resource_counts.values,
                title='Aktivitäten nach Ressource Typ',
                labels={'x': 'Ressource Typ', 'y': 'Anzahl Aktivitäten'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Activity timeline
        st.subheader("⏰ Zeitlicher Verlauf")
        df_activities['date'] = pd.to_datetime(df_activities['timestamp']).dt.date
        daily_activities = df_activities.groupby('date').size().reset_index(name='count')

        fig_timeline = px.line(
            daily_activities,
            x='date',
            y='count',
            title='Tägliche Aktivitäten',
            labels={'date': 'Datum', 'count': 'Anzahl Aktivitäten'}
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # Recent activities table
        st.subheader("🔄 Neueste Aktivitäten")

        # Format timestamp for display
        df_display = df_activities.copy()
        df_display['timestamp'] = pd.to_datetime(df_display['timestamp']).dt.strftime('%d.%m.%Y %H:%M')

        st.dataframe(
            df_display[['timestamp', 'action', 'resource_type', 'description']].head(50),
            column_config={
                'timestamp': 'Zeitstempel',
                'action': 'Aktion',
                'resource_type': 'Ressource Typ',
                'description': 'Beschreibung'
            },
            hide_index=True
        )
    else:
        st.info(f"Keine Aktivitäten in den letzten {days} Tagen")