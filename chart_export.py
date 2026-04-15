"""
Chart export using matplotlib for PDF/PPTX generation.
Copied from app/chart_export.py for self-contained operation.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import re
import tempfile
import os


COLORS = {
    'high': '#ef4444',
    'medium': '#f59e0b',
    'low': '#22c55e',
    'primary': '#4472C4',
    'secondary': '#ED7D31',
    'tertiary': '#A5A5A5',
    'header_bg': '#1E3A5F',
}


def _get_vuln_color(val):
    if val <= 1.5:
        return COLORS['high']
    elif val < 2.5:
        return COLORS['medium']
    return COLORS['low']


def _shorten_name(name, maxlen=None):
    """Return full facility name for chart labels (no truncation)."""
    return name


def export_domain_average_chart(domain_data, domain_name):
    """Bar chart: domain average per PHC. Returns temp file path or None."""
    facilities = domain_data.get('facilities', [])
    if not facilities:
        return None

    names = [_shorten_name(f['name']) for f in facilities]
    averages = [f.get('Average', 0) or 0 for f in facilities]
    colors = [_get_vuln_color(v) for v in averages]

    fig, ax = plt.subplots(figsize=(6.5, 4))
    bars = ax.bar(range(len(names)), averages, color=colors, width=0.65, edgecolor='white', linewidth=0.5)

    for bar, val in zip(bars, averages):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.04,
                f'{val:.2f}', ha='center', va='bottom', fontsize=6.5, fontweight='bold')

    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=40, ha='right', fontsize=5.5)
    ax.set_ylabel('Average', fontsize=8)
    ax.set_ylim(0, 3.2)
    ax.set_title(f'{domain_name} Average per PHC', fontsize=10, fontweight='bold', color='#3B82F6', pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    plt.subplots_adjust(bottom=0.28, top=0.90, left=0.10, right=0.97)

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        fig.savefig(tmp.name, dpi=150, facecolor='white')
        plt.close(fig)
        return tmp.name
    except Exception:
        plt.close(fig)
        return None


def export_domain_detailed_chart(domain_data, domain_name):
    """Grouped bar chart: 3 subdivisions per PHC. Returns temp file path or None."""
    facilities = domain_data.get('facilities', [])
    subdivisions = domain_data.get('subdivisions', [])
    if not facilities or not subdivisions:
        return None

    names = [_shorten_name(f['name']) for f in facilities]
    sub_colors = [COLORS['primary'], COLORS['secondary'], COLORS['tertiary']]

    x = np.arange(len(names))
    width = 0.25
    fig, ax = plt.subplots(figsize=(6.5, 4))

    for i, sub in enumerate(subdivisions):
        values = [f.get(sub, 0) or 0 for f in facilities]
        short_label = sub
        offset = (i - 1) * width
        ax.bar(x + offset, values, width, label=short_label, color=sub_colors[i % 3], edgecolor='white', linewidth=0.3)

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=40, ha='right', fontsize=5.5)
    ax.set_ylim(0, 3.2)
    ax.set_title('Detailed Comparison Per PHC', fontsize=10, fontweight='bold', color='#3B82F6', pad=10)
    ax.legend(fontsize=5.5, loc='upper right', framealpha=0.9, edgecolor='#ccc')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    plt.subplots_adjust(bottom=0.28, top=0.90, left=0.10, right=0.97)

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        fig.savefig(tmp.name, dpi=150, facecolor='white')
        plt.close(fig)
        return tmp.name
    except Exception:
        plt.close(fig)
        return None


def export_key_statistics_banner(stats, location_name):
    """Key Statistics infographic banner."""
    fig, ax = plt.subplots(figsize=(10, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.8)
    ax.axis('off')

    border = plt.Rectangle((0.05, 0.05), 9.9, 2.7, facecolor='#1E3A5F', edgecolor='none')
    ax.add_patch(border)

    title_rect = plt.Rectangle((0.1, 2.1), 9.8, 0.55, facecolor='#0EA5E9', edgecolor='none')
    ax.add_patch(title_rect)
    ax.text(5, 2.37, f'Climate Health Vulnerability Assessment \u2014 {location_name}  |  Key Statistics',
            ha='center', va='center', fontsize=11, fontweight='bold', color='white')

    cards = [
        {'value': f"{stats.get('avg_vuln', 0)} / 3.0", 'label': 'Overall\nVulnerability Index', 'color': '#DC2626'},
        {'value': f"{stats.get('high_pct', 0)}%", 'label': 'Facilities Classified\nHighly Vulnerable', 'color': '#F59E0B'},
        {'value': str(stats.get('facilities', 0)), 'label': 'PHC Facilities\nAssessed', 'color': '#3B82F6'},
        {'value': f"{stats.get('total', 0):,}", 'label': 'Total Assessments\nConducted', 'color': '#22C55E'},
    ]

    card_w = 2.3
    gap = 0.2
    start_x = (10 - (4 * card_w + 3 * gap)) / 2
    for i, card in enumerate(cards):
        x = start_x + i * (card_w + gap)
        bg = plt.Rectangle((x, 0.25), card_w, 1.7, facecolor='#EFF6FF',
                           edgecolor=card['color'], linewidth=2.5)
        ax.add_patch(bg)
        cbar = plt.Rectangle((x, 1.6), card_w, 0.35, facecolor=card['color'], edgecolor='none')
        ax.add_patch(cbar)
        ax.text(x + card_w / 2, 1.1, card['value'],
                ha='center', va='center', fontsize=18, fontweight='bold', color='#1E3A5F')
        ax.text(x + card_w / 2, 0.55, card['label'],
                ha='center', va='center', fontsize=7, color='#64748B')

    ax.text(5, 0.1, f'Source: CHAT Tool Assessment  |  eHealth Africa',
            ha='center', va='center', fontsize=5.5, color='#94A3B8', style='italic')

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        fig.savefig(tmp.name, dpi=180, bbox_inches='tight', facecolor='white', pad_inches=0.05)
        plt.close(fig)
        return tmp.name
    except Exception:
        plt.close(fig)
        return None


def export_domain_radar_chart(domain_tables):
    """Radar chart: domain vulnerability scores comparison."""
    domains = []
    averages = []

    domain_labels = {
        'Health Workforce': 'Health\nWorkforce',
        'WASH': 'WASH &\nWaste',
        'Energy': 'Energy\nSystems',
        'Infrastructure': 'Infrastructure\n& Technology',
    }

    for key in ['Health Workforce', 'WASH', 'Energy', 'Infrastructure']:
        data = domain_tables.get(key, {})
        if data and data.get('domain_avg') is not None:
            domains.append(domain_labels.get(key, key))
            try:
                averages.append(float(data['domain_avg']))
            except (ValueError, TypeError):
                averages.append(0)

    if len(domains) < 3:
        return None

    N = len(domains)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    values = averages + averages[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    theta_fill = np.linspace(0, 2 * np.pi, 100)
    ax.fill_between(theta_fill, 2.5, 3.0, alpha=0.12, color='#22c55e', zorder=0)
    ax.fill_between(theta_fill, 1.5, 2.5, alpha=0.12, color='#f59e0b', zorder=0)
    ax.fill_between(theta_fill, 0, 1.5, alpha=0.12, color='#ef4444', zorder=0)

    ax.plot(angles, values, 'o-', linewidth=2.5, color='#2563EB', markersize=8,
            markerfacecolor='#BEF264', markeredgecolor='#2563EB', markeredgewidth=1.5, zorder=5)
    ax.fill(angles, values, alpha=0.15, color='#2563EB', zorder=4)

    for angle, val in zip(angles[:-1], averages):
        x_offset = 0.22 * np.cos(angle - np.pi / 12)
        y_offset = 0.22 * np.sin(angle - np.pi / 12)
        ax.annotate(f'{val:.2f}', xy=(angle, val), fontsize=12, fontweight='bold',
                    color='#1E3A5F', ha='center', va='center',
                    xytext=(angle + x_offset * 0.3, val + 0.2),
                    zorder=6)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(domains, fontsize=11, fontweight='bold', color='#1E3A5F')
    ax.set_ylim(0, 3.0)
    ax.set_yticks([1.0, 2.0, 3.0])
    ax.set_yticklabels(['1.0\n(High)', '2.0\n(Med)', '3.0\n(Low)'], fontsize=7, color='#64748B')
    ax.set_rlabel_position(30)
    ax.grid(True, alpha=0.3)
    ax.spines['polar'].set_alpha(0.3)

    ax.set_title('Domain Vulnerability Scores Comparison\n(Average score out of 3.0 across PHC Facilities)',
                 fontsize=13, fontweight='bold', color='#1E3A5F', pad=25)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#ef4444', alpha=0.3, label='High Vulnerability (1.0 \u2013 1.5)'),
        Patch(facecolor='#f59e0b', alpha=0.3, label='Medium Vulnerability (1.5 \u2013 2.5)'),
        Patch(facecolor='#22c55e', alpha=0.3, label='Low Vulnerability (2.5 \u2013 3.0)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.35, 1.12),
              fontsize=9, framealpha=0.9, edgecolor='#ccc')

    plt.tight_layout()

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return tmp.name
    except Exception:
        plt.close(fig)
        return None


def _wrap_text(text, max_chars=42):
    """Word-wrap text to fit within a column width."""
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = f'{current} {word}'.strip()
        if len(test) <= max_chars:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return '\n'.join(lines)


def export_recommendations_roadmap(location_name, recommendations_text):
    """Recommendations Roadmap timeline infographic with full text wrapping.

    Parses the AI-generated recommendations text into three time-bucketed lists.
    The parser accepts any common bullet marker (-, *, •, ·, —) and numbered
    items (1., 1), 1:), and also falls back to plain prose sentences that appear
    under a category header — so that variations in LLM output still populate
    the roadmap instead of leaving the boxes empty.
    """
    short_items = []
    medium_items = []
    long_items = []
    current_list = None

    # Matches a line that starts with a bullet marker OR a number prefix.
    # Captures the remaining text after the marker.
    BULLET_RE = re.compile(r'^\s*(?:[-*•·—]+|\d+[.):])\s+(.+)$')

    # Category header detection: the line is primarily a category label, not a
    # recommendation itself. We check this BEFORE the bullet regex because some
    # LLMs output headers like "- Short-Term (0-12 months):" with a dash.
    def _category_of(lower_line):
        if 'short-term' in lower_line or 'short term' in lower_line or '0-12' in lower_line or '0 - 12' in lower_line:
            return 'short'
        if 'medium-term' in lower_line or 'medium term' in lower_line or '1-3' in lower_line or '1 - 3' in lower_line:
            return 'medium'
        if 'long-term' in lower_line or 'long term' in lower_line or '3-5' in lower_line or '3 - 5' in lower_line:
            return 'long'
        return None

    for raw_line in recommendations_text.split('\n'):
        stripped = raw_line.strip()
        if not stripped:
            continue
        # Drop markdown emphasis that some models emit even when told not to.
        stripped = stripped.replace('**', '').replace('__', '').strip()
        lower = stripped.lower()

        # 1. Is this a category header? Treat short lines that name a category
        #    as headers regardless of bullet prefix, so "- Short-Term:" is a
        #    header, not a bullet.
        cat = _category_of(lower)
        if cat and len(stripped) < 60:
            current_list = {'short': short_items, 'medium': medium_items, 'long': long_items}[cat]
            continue

        if current_list is None:
            continue

        # 2. Bullet-marker path: extract text after the marker.
        m = BULLET_RE.match(stripped)
        if m:
            text = m.group(1).strip().rstrip(':').strip()
            if text:
                current_list.append(text)
            continue

        # 3. Fallback: plain sentence under a category header — still an item.
        #    Guard: must be a substantive sentence (>= 15 chars) and not another
        #    stray header we missed.
        if len(stripped) >= 15 and not stripped.endswith(':'):
            current_list.append(stripped.rstrip('.'))

    short_items = short_items[:4]
    medium_items = medium_items[:4]
    long_items = long_items[:4]

    line_h = 0.38
    item_gap = 0.25
    wrap_chars = 32

    def _calc_column_h(items):
        total = 0
        for item in items:
            wrapped = _wrap_text(item, max_chars=wrap_chars)
            n_lines = len(wrapped.split('\n'))
            total += n_lines * line_h + item_gap
        return total

    col_heights = [_calc_column_h(short_items), _calc_column_h(medium_items), _calc_column_h(long_items)]
    max_content_h = max(col_heights) if col_heights else 3.0

    header_h = 1.6
    card_content_h = header_h + max_content_h + 0.4
    title_area_h = 2.5
    total_h = title_area_h + card_content_h + 0.8

    fig, ax = plt.subplots(figsize=(16, total_h))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, total_h)
    ax.axis('off')

    bar_y = total_h - 0.25
    bar = plt.Rectangle((0, bar_y), 16, 0.25, facecolor='#BEF264', edgecolor='none')
    ax.add_patch(bar)

    title_y = bar_y - 0.5
    ax.text(8, title_y, f'Recommendations Roadmap \u2014 {location_name} CHAT Assessment',
            ha='center', va='center', fontsize=24, fontweight='bold', color='#1E3A5F')

    arrow_y = title_y - 0.55
    ax.annotate('', xy=(15.5, arrow_y), xytext=(0.5, arrow_y),
                arrowprops=dict(arrowstyle='->', color='#22C55E', lw=4))
    for x_pos in [2.7, 8, 13.3]:
        circle = plt.Circle((x_pos, arrow_y), 0.2, facecolor='#BEF264', edgecolor='#22C55E', linewidth=2.5, zorder=5)
        ax.add_patch(circle)

    card_top = arrow_y - 0.45
    card_bottom = card_top - card_content_h
    col_w = 5.0
    columns = [
        {'title': 'Short-Term', 'subtitle': '0 \u2013 12 Months', 'items': short_items, 'x': 0.15, 'color': '#DC2626'},
        {'title': 'Medium-Term', 'subtitle': '1 \u2013 3 Years', 'items': medium_items, 'x': 5.5, 'color': '#F59E0B'},
        {'title': 'Long-Term', 'subtitle': '3 \u2013 5 Years', 'items': long_items, 'x': 10.85, 'color': '#22C55E'},
    ]

    for col in columns:
        x = col['x']
        card = plt.Rectangle((x, card_bottom), col_w, card_content_h, facecolor=col['color'],
                             edgecolor='none', alpha=0.88)
        ax.add_patch(card)

        ax.text(x + col_w / 2, card_top - 0.35, col['title'],
                ha='center', va='center', fontsize=20, fontweight='bold', color='white')
        badge_w = 2.0
        badge = plt.Rectangle((x + col_w / 2 - badge_w / 2, card_top - 0.82), badge_w, 0.35,
                              facecolor='#BEF264', edgecolor='none')
        ax.add_patch(badge)
        ax.text(x + col_w / 2, card_top - 0.65, col['subtitle'],
                ha='center', va='center', fontsize=13, fontweight='bold', color='#1E3A5F')

        y_cursor = card_top - header_h
        for i, item in enumerate(col['items']):
            wrapped = _wrap_text(item, max_chars=wrap_chars)
            n_lines = len(wrapped.split('\n'))
            bullet = plt.Circle((x + 0.3, y_cursor - 0.05), 0.12, facecolor='#BEF264', edgecolor='none')
            ax.add_patch(bullet)
            ax.text(x + 0.6, y_cursor, wrapped, fontsize=14, color='white',
                    va='top', ha='left', linespacing=1.3)
            y_cursor -= (n_lines * line_h + item_gap)

    ax.text(8, card_bottom - 0.5, f'Source: CHAT Tool Assessment  |  eHealth Africa',
            ha='center', va='center', fontsize=12, color='#94A3B8', style='italic')

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        fig.savefig(tmp.name, dpi=200, bbox_inches='tight', facecolor='white', pad_inches=0.05)
        plt.close(fig)
        return tmp.name
    except Exception:
        plt.close(fig)
        return None


def export_facility_heatmap(domain_tables):
    """Facility vulnerability heatmap."""
    facilities_data = {}
    domain_order = ['Health Workforce', 'WASH', 'Energy', 'Infrastructure']
    domain_display = {
        'Health Workforce': 'Health\nWorkforce',
        'WASH': 'WASH &\nWaste',
        'Energy': 'Energy\nSystems',
        'Infrastructure': 'Infrastructure\n& Tech',
    }

    for domain_key in domain_order:
        data = domain_tables.get(domain_key, {})
        for fac in data.get('facilities', []):
            name = fac.get('name', 'Unknown')
            short = name
            if short not in facilities_data:
                facilities_data[short] = {}
            avg = fac.get('Average', None)
            if avg is not None:
                facilities_data[short][domain_key] = float(avg)

    if not facilities_data:
        return None

    fac_names = list(facilities_data.keys())
    n_facs = len(fac_names)
    n_domains = len(domain_order)

    row_h = 0.5
    header_h = 0.55
    gap = 0.04
    legend_h = 0.6
    title_h = 0.9
    total_h = title_h + header_h + n_facs * (row_h + gap) + legend_h + 0.3

    fig, ax = plt.subplots(figsize=(10, max(3.5, total_h)))
    ax.axis('off')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, total_h)

    top_y = total_h - 0.15
    ax.text(5, top_y, 'Facility Vulnerability Heatmap \u2014 All Domains (Score out of 3.0)',
            ha='center', va='top', fontsize=12, fontweight='bold', color='#1E3A5F')
    bar_y = top_y - 0.55
    ax.add_patch(plt.Rectangle((0.3, bar_y), 9.4, 0.1, facecolor='#BEF264', edgecolor='none'))

    name_col_x = 0.2
    max_name_len = max(len(n) for n in fac_names) if fac_names else 20
    name_col_w = min(3.8, max(2.5, max_name_len * 0.085))
    data_col_w = min(1.3, (10 - name_col_w - 0.5) / (n_domains + 1) - 0.06)
    col_gap = 0.06
    data_start_x = name_col_x + name_col_w + 0.08
    overall_x = data_start_x + n_domains * (data_col_w + col_gap)

    header_top = bar_y - 0.15
    for i, dk in enumerate(domain_order):
        x = data_start_x + i * (data_col_w + col_gap)
        rect = plt.Rectangle((x, header_top - header_h), data_col_w, header_h,
                             facecolor='#1E3A5F', edgecolor='white', linewidth=1)
        ax.add_patch(rect)
        ax.text(x + data_col_w / 2, header_top - header_h / 2, domain_display[dk],
                ha='center', va='center', fontsize=7, fontweight='bold', color='white')

    rect = plt.Rectangle((overall_x, header_top - header_h), data_col_w, header_h,
                         facecolor='#1E3A5F', edgecolor='white', linewidth=1)
    ax.add_patch(rect)
    ax.text(overall_x + data_col_w / 2, header_top - header_h / 2, 'Overall\nAverage',
            ha='center', va='center', fontsize=7, fontweight='bold', color='white')

    def get_cell_color(val):
        if val <= 1.5:
            return '#ef4444'
        elif val <= 2.0:
            return '#f59e0b'
        else:
            return '#22c55e'

    rows_start_y = header_top - header_h - gap
    for row_idx, fac_name in enumerate(fac_names):
        y = rows_start_y - row_idx * (row_h + gap) - row_h
        fac_vals = facilities_data[fac_name]

        name_rect = plt.Rectangle((name_col_x, y), name_col_w, row_h,
                                  facecolor='#1E3A5F', edgecolor='white', linewidth=0.5, alpha=0.88)
        ax.add_patch(name_rect)
        name_fs = 6.5 if len(fac_name) <= 30 else 5.5 if len(fac_name) <= 40 else 4.8
        ax.text(name_col_x + name_col_w - 0.08, y + row_h / 2, fac_name,
                ha='right', va='center', fontsize=name_fs, color='white', fontweight='bold')

        all_vals = []
        for i, dk in enumerate(domain_order):
            x = data_start_x + i * (data_col_w + col_gap)
            val = fac_vals.get(dk, None)
            if val is not None:
                all_vals.append(val)
                color = get_cell_color(val)
                cell = plt.Rectangle((x, y), data_col_w, row_h, facecolor=color,
                                    edgecolor='white', linewidth=1, alpha=0.85)
                ax.add_patch(cell)
                ax.text(x + data_col_w / 2, y + row_h / 2, f'{val:.2f}',
                        ha='center', va='center', fontsize=8.5, fontweight='bold', color='white')
            else:
                cell = plt.Rectangle((x, y), data_col_w, row_h, facecolor='#E5E7EB',
                                    edgecolor='white', linewidth=1)
                ax.add_patch(cell)
                ax.text(x + data_col_w / 2, y + row_h / 2, '-',
                        ha='center', va='center', fontsize=8.5, color='#9CA3AF')

        if all_vals:
            overall = sum(all_vals) / len(all_vals)
            color = get_cell_color(overall)
            cell = plt.Rectangle((overall_x, y), data_col_w, row_h, facecolor=color,
                                edgecolor='white', linewidth=1.5, alpha=0.92)
            ax.add_patch(cell)
            ax.text(overall_x + data_col_w / 2, y + row_h / 2, f'{overall:.2f}',
                    ha='center', va='center', fontsize=9, fontweight='bold', color='white')

    legend_y_pos = rows_start_y - n_facs * (row_h + gap) - row_h - 0.3
    legend_items = [
        ('#ef4444', 'High Vulnerability (\u2264 1.5)'),
        ('#f59e0b', 'Medium (1.5 \u2013 2.0)'),
        ('#22c55e', 'Low Vulnerability (> 2.0)'),
    ]
    legend_x = 1.5
    for color, label in legend_items:
        swatch = plt.Rectangle((legend_x, legend_y_pos), 0.3, 0.25,
                              facecolor=color, edgecolor='none', alpha=0.85)
        ax.add_patch(swatch)
        ax.text(legend_x + 0.4, legend_y_pos + 0.12, label,
                ha='left', va='center', fontsize=7.5, color='#374151')
        legend_x += 2.8

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight', facecolor='white', pad_inches=0.1)
        plt.close(fig)
        return tmp.name
    except Exception:
        plt.close(fig)
        return None


def export_vuln_pie_chart(stats):
    """Pie chart: vulnerability distribution."""
    high = stats.get('high', 0)
    medium = stats.get('medium', 0)
    low = stats.get('low', 0)

    if high + medium + low == 0:
        return None

    labels = []
    sizes = []
    colors = []
    for label, val, color in [('High', high, COLORS['high']), ('Medium', medium, COLORS['medium']), ('Low', low, COLORS['low'])]:
        if val > 0:
            labels.append(label)
            sizes.append(val)
            colors.append(color)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        startangle=90, pctdistance=0.75,
        wedgeprops=dict(width=0.5)
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight('bold')
    ax.set_title('Vulnerability Distribution', fontsize=11, fontweight='bold', color='#1E3A5F')
    plt.tight_layout()

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return tmp.name
    except Exception:
        plt.close(fig)
        return None
