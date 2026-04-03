"""
CHAT Model Evaluation - Data Loading and Processing
Copied from app/data_loader.py and app/app.py for self-contained operation.
"""

import pandas as pd
import numpy as np
from functools import lru_cache
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "CHAT Main Data.xlsx")


@lru_cache(maxsize=1)
def load_data():
    """Load and cache the CHAT data from Excel file."""
    df = pd.read_excel(DATA_FILE)
    df.columns = df.columns.str.strip()
    df['answer'] = pd.to_numeric(df['answer'], errors='coerce').fillna(0).astype(int)
    vulnerability_map = {1: 'High', 2: 'Medium', 3: 'Low'}
    df['vulnerability_level'] = df['answer'].map(vulnerability_map).fillna('Unknown')
    df['state'] = df['state'].str.strip().str.title() if df['state'].notna().any() else df['state']
    df['lga'] = df['lga'].str.strip().str.title() if df['lga'].notna().any() else df['lga']
    df['ward'] = df['ward'].str.strip().str.title() if df['ward'].notna().any() else df['ward']
    return df


def get_unique_values(column):
    """Get unique values for a column."""
    df = load_data()
    return sorted(df[column].dropna().unique().tolist())


def filter_data(df, state=None, lga=None, ward=None, facility=None, hazard_area=None):
    """Filter data based on geographic and hazard parameters."""
    filtered = df.copy()
    if state and state != "All":
        filtered = filtered[filtered['state'].str.contains(state, case=False, na=False)]
    if lga and lga != "All":
        filtered = filtered[filtered['lga'].str.contains(lga, case=False, na=False)]
    if ward and ward != "All":
        filtered = filtered[filtered['ward'].str.contains(ward, case=False, na=False)]
    if facility and facility != "All":
        filtered = filtered[filtered['name'].str.contains(facility, case=False, na=False)]
    if hazard_area and hazard_area != "All":
        filtered = filtered[filtered['hazard_area'].str.contains(hazard_area, case=False, na=False)]
    return filtered


def compute_domain_tables(df):
    """Compute per-domain, per-facility breakdown with subdivision scores."""
    DOMAIN_CONFIG = {
        'Health Workforce': {
            'section_label': 'Health Workforce',
            'subdivisions': ['Human Resources', 'Capacity Development', 'Communication and Awareness Raising'],
            'display_name': 'Health Workforce'
        },
        'WASH': {
            'section_label': 'Water, Sanitation and health care waste',
            'subdivisions': ['Monitoring and Assessment', 'Risk management', 'Health and safety regulation'],
            'display_name': 'WASH and Waste Services Management'
        },
        'Energy': {
            'section_label': 'Energy',
            'subdivisions': ['Monitoring and Assessment', 'Risk management', 'Health and safety regulation'],
            'display_name': 'Energy'
        },
        'Infrastructure': {
            'section_label': 'Infrastructure, Technologies, Products and Processes',
            'subdivisions': [
                'Adaptation of current systems and infrastructures',
                'Promotion of new systems and technologies',
                'Sustainability of health care facility operations'
            ],
            'display_name': 'Infrastructure, Technologies, Products and Processes'
        }
    }

    result = {}
    for domain_key, config in DOMAIN_CONFIG.items():
        domain_df = df[df['section_label'] == config['section_label']]
        if domain_df.empty:
            result[domain_key] = {
                'subdivisions': config['subdivisions'],
                'facilities': [],
                'display_name': config['display_name'],
                'section_label': config['section_label'],
                'domain_avg': 0
            }
            continue

        facilities_data = []
        for facility_name in sorted(domain_df['name'].unique()):
            fac_df = domain_df[domain_df['name'] == facility_name]
            row = {'name': facility_name}
            scores = []
            for sub in config['subdivisions']:
                sub_df = fac_df[fac_df['subsection_label'] == sub]
                if not sub_df.empty:
                    score = round(sub_df['answer'].mean(), 2)
                else:
                    score = None
                row[sub] = score
                if score is not None:
                    scores.append(score)
            row['Average'] = round(sum(scores) / len(scores), 2) if scores else None
            row['lga'] = fac_df['lga'].iloc[0] if not fac_df.empty else ''
            row['state'] = fac_df['state'].iloc[0] if not fac_df.empty else ''
            facilities_data.append(row)

        facilities_data.sort(key=lambda x: x['name'])
        all_avgs = [f['Average'] for f in facilities_data if f['Average'] is not None]
        domain_avg = round(sum(all_avgs) / len(all_avgs), 2) if all_avgs else 0

        result[domain_key] = {
            'subdivisions': config['subdivisions'],
            'facilities': facilities_data,
            'display_name': config['display_name'],
            'section_label': config['section_label'],
            'domain_avg': domain_avg
        }

    return result


def get_facility_list(df):
    """Get a clean list of facilities with their LGAs for the report appendix."""
    facility_list = df.groupby('name').agg({
        'lga': 'first',
        'state': 'first',
        'ward': 'first'
    }).reset_index().sort_values('name')
    return facility_list.to_dict('records')


def calculate_stats(df, context):
    """Calculate stats with location context and domain-level breakdowns."""
    stats = {}
    stats['context'] = context

    stats['lga_list'] = df['lga'].dropna().unique().tolist()
    stats['ward_list'] = df['ward'].dropna().unique().tolist()
    stats['facility_list'] = df['name'].dropna().unique().tolist()

    stats['states'] = df['state'].nunique()
    stats['lgas'] = df['lga'].nunique()
    stats['wards'] = df['ward'].nunique()
    stats['facilities'] = df['name'].nunique()
    stats['total'] = len(df)
    stats['avg_vuln'] = round(df['answer'].mean(), 2) if len(df) > 0 else 0

    total = len(df)
    stats['high'] = len(df[df['answer'] == 1])
    stats['medium'] = len(df[df['answer'] == 2])
    stats['low'] = len(df[df['answer'] == 3])
    stats['high_pct'] = round(stats['high'] / total * 100, 1) if total > 0 else 0
    stats['medium_pct'] = round(stats['medium'] / total * 100, 1) if total > 0 else 0
    stats['low_pct'] = round(stats['low'] / total * 100, 1) if total > 0 else 0

    # By hazard
    if len(df) > 0:
        hazard_stats = df.groupby('hazard_area').agg({'answer': ['mean', 'count']}).reset_index()
        hazard_stats.columns = ['hazard', 'avg', 'count']
        hazard_stats['vuln_idx'] = round(hazard_stats['avg'], 2)
        stats['hazards'] = hazard_stats.to_dict('records')
    else:
        stats['hazards'] = []

    # By section
    if len(df) > 0:
        section_stats = df.groupby('section_label').agg({'answer': ['mean', 'count']}).reset_index()
        section_stats.columns = ['section', 'avg', 'count']
        section_stats['vuln_idx'] = round(section_stats['avg'], 2)
        stats['sections'] = section_stats.to_dict('records')
    else:
        stats['sections'] = []

    # By subsection
    if len(df) > 0:
        subsection_stats = df.groupby('subsection_label').agg({'answer': ['mean', 'count']}).reset_index()
        subsection_stats.columns = ['subsection', 'avg', 'count']
        subsection_stats['vuln_idx'] = round(subsection_stats['avg'], 2)
        stats['subsections'] = subsection_stats.to_dict('records')
    else:
        stats['subsections'] = []

    # Top vulnerable facilities
    if len(df) > 0:
        fac_stats = df.groupby('name').agg({'answer': 'mean', 'state': 'first', 'lga': 'first', 'ward': 'first'}).reset_index()
        fac_stats['vuln_idx'] = round(fac_stats['answer'], 2)
        fac_stats = fac_stats.nsmallest(10, 'vuln_idx')
        stats['top_facilities'] = fac_stats[['name', 'state', 'lga', 'ward', 'vuln_idx']].to_dict('records')
    else:
        stats['top_facilities'] = []

    # Sector-Specific Vulnerable Facilities
    stats['sector_vulnerability'] = {}
    target_sectors = {
        'Health Workforce': 'Health Workforce',
        'WASH': 'Water, Sanitation and health care waste',
        'Energy': 'Energy',
        'Infrastructure': 'Infrastructure, Technologies, Products and Processes'
    }
    if len(df) > 0:
        for key, sector_name in target_sectors.items():
            sector_df = df[df['section_label'] == sector_name]
            if not sector_df.empty:
                sector_facs = sector_df.groupby('name').agg({'answer': 'mean', 'state': 'first', 'lga': 'first'}).reset_index()
                sector_facs['vuln_idx'] = round(sector_facs['answer'], 2)
                top_sector_facs = sector_facs.nsmallest(5, 'vuln_idx')
                stats['sector_vulnerability'][key] = top_sector_facs[['name', 'state', 'lga', 'vuln_idx']].to_dict('records')
            else:
                stats['sector_vulnerability'][key] = []
    else:
        for key in target_sectors:
            stats['sector_vulnerability'][key] = []

    # All facilities
    if len(df) > 0:
        all_fac = df.groupby('name').agg({
            'answer': 'mean', 'state': 'first', 'lga': 'first', 'ward': 'first',
            'latitude': 'first', 'longitude': 'first'
        }).reset_index()
        all_fac['vuln_idx'] = round(all_fac['answer'], 2)
        all_fac = all_fac.sort_values('vuln_idx', ascending=True)
        stats['all_facilities'] = all_fac.to_dict('records')
    else:
        stats['all_facilities'] = []

    # LGA breakdown
    if len(df) > 0:
        lga_stats = df.groupby('lga').agg({'answer': 'mean', 'name': 'nunique'}).reset_index()
        lga_stats.columns = ['lga', 'avg', 'facilities']
        lga_stats['vuln_idx'] = round(lga_stats['avg'], 2)
        lga_stats = lga_stats.sort_values('vuln_idx', ascending=True)
        stats['lgas_data'] = lga_stats.to_dict('records')
    else:
        stats['lgas_data'] = []

    # Domain tables
    if len(df) > 0:
        stats['domain_tables'] = compute_domain_tables(df)
    else:
        stats['domain_tables'] = {}

    # Facility list for appendix
    if len(df) > 0:
        stats['facility_list_table'] = get_facility_list(df)
    else:
        stats['facility_list_table'] = []

    return stats
