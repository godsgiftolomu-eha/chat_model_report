"""
CHAT Model Evaluation - PDF Report Generation
Copied from app/app.py generate_pdf_report() for identical report output.
"""

import os
import re
from datetime import datetime
from fpdf import FPDF
from chart_export import (
    export_domain_average_chart,
    export_domain_detailed_chart,
    export_key_statistics_banner,
    export_domain_radar_chart,
    export_recommendations_roadmap,
    export_facility_heatmap,
)
from prompts import strip_ai_title


def generate_pdf_report(stats, context, content_dict, report_depth, provider_name=""):
    """Generate PDF report matching the WHO template structure with domain tables and charts."""

    def sanitize_for_pdf(text):
        if not text:
            return ""
        replacements = {
            '\u2022': '-', '\u2013': '-', '\u2014': '-', '\u201c': '"', '\u201d': '"',
            '\u2018': "'", '\u2019': "'", '\u2026': '...', '\u00e2': 'a',
            '**': '', '##': '', '###': '', '# ': '', '*': ''
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode('ascii', 'replace').decode('ascii')

    BLUE = (59, 130, 246)
    DARK_BLUE = (30, 58, 95)
    BODY_COLOR = (55, 65, 81)
    FONT_FAMILY = 'Helvetica'

    PAGE_H = 297
    PAGE_MARGIN = 15
    PRINTABLE_H = PAGE_H - PAGE_MARGIN - 10

    def check_space(pdf, needed=40):
        if pdf.get_y() > (PAGE_H - PAGE_MARGIN - needed):
            pdf.add_page()

    def safe_image(pdf, img_path, x, w, h=None):
        if h is None:
            from PIL import Image as PILImage
            try:
                with PILImage.open(img_path) as im:
                    img_w, img_h = im.size
                    h = w * (img_h / img_w)
            except Exception:
                h = 150

        available = PAGE_H - PAGE_MARGIN - pdf.get_y() - 5
        if h > available:
            pdf.add_page()
            available = PRINTABLE_H

        if h > PRINTABLE_H:
            scale = PRINTABLE_H / h
            w = w * scale
            h = PRINTABLE_H

        img_y = pdf.get_y() + 2
        pdf.image(img_path, x=x, y=img_y, w=w, h=h)
        pdf.set_y(img_y + h + 3)

    _last_section_title = [None]

    def add_section_header(pdf, title):
        check_space(pdf, 50)
        pdf.ln(6)
        pdf.set_font(FONT_FAMILY, 'B', 14)
        pdf.set_text_color(*BLUE)
        pdf.cell(0, 10, sanitize_for_pdf(title), border=0, ln=1, align='L')
        pdf.ln(2)
        pdf.set_font(FONT_FAMILY, '', 10)
        pdf.set_text_color(*BODY_COLOR)
        _last_section_title[0] = title

    def add_subsection_header(pdf, title):
        check_space(pdf, 30)
        pdf.ln(3)
        pdf.set_font(FONT_FAMILY, 'B', 11)
        pdf.set_text_color(*DARK_BLUE)
        pdf.cell(0, 7, sanitize_for_pdf(title), ln=1)
        pdf.ln(2)
        pdf.set_font(FONT_FAMILY, '', 10)
        pdf.set_text_color(*BODY_COLOR)

    def add_content(pdf, text):
        if _last_section_title[0]:
            text = strip_ai_title(text, _last_section_title[0])
        clean_text = sanitize_for_pdf(text)
        for line in clean_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.endswith(':') and len(line) < 80 and not line[0].isdigit():
                check_space(pdf, 20)
                pdf.ln(2)
                pdf.set_font(FONT_FAMILY, 'B', 10)
                pdf.set_text_color(*DARK_BLUE)
                pdf.cell(0, 6, line, ln=1)
                pdf.set_font(FONT_FAMILY, '', 10)
                pdf.set_text_color(*BODY_COLOR)
                pdf.ln(1)
            elif line.startswith('- ') or line.startswith('* '):
                bullet_text = line[2:].strip()
                pdf.set_x(pdf.l_margin + 8)
                pdf.cell(5, 5, '-')
                pdf.multi_cell(0, 5, bullet_text, align='L')
                pdf.ln(1)
            else:
                pdf.multi_cell(0, 5, line, align='L')
                pdf.ln(1.5)
        pdf.ln(1)

    def add_domain_table(pdf, domain_key, domain_data):
        facilities = domain_data.get('facilities', [])
        subdivisions = domain_data.get('subdivisions', [])
        display_name = domain_data.get('display_name', domain_key)

        if not facilities:
            return

        check_space(pdf, 60)
        pdf.ln(4)
        pdf.set_font(FONT_FAMILY, 'B', 11)
        pdf.set_text_color(*BLUE)
        pdf.cell(0, 8, sanitize_for_pdf(display_name), ln=1)
        pdf.ln(2)

        col_widths = [8, 60]
        sub_width = (190 - 68 - 22) / len(subdivisions)
        for _ in subdivisions:
            col_widths.append(sub_width)
        col_widths.append(22)

        pdf.set_font(FONT_FAMILY, 'B', 6)
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(255, 255, 255)

        pdf.cell(col_widths[0], 10, '#', border=1, align='C', fill=True)
        pdf.cell(col_widths[1], 10, 'PHCs', border=1, align='C', fill=True)
        for i, sub in enumerate(subdivisions):
            pdf.cell(col_widths[i + 2], 10, sanitize_for_pdf(sub), border=1, align='C', fill=True)
        pdf.cell(col_widths[-1], 10, 'Average', border=1, align='C', fill=True); pdf.ln()

        pdf.set_font(FONT_FAMILY, '', 7)
        pdf.set_text_color(*BODY_COLOR)

        for idx, fac in enumerate(facilities, 1):
            if pdf.get_y() > 260:
                pdf.add_page()
                pdf.set_font(FONT_FAMILY, 'B', 6)
                pdf.set_fill_color(*BLUE)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(col_widths[0], 10, '#', border=1, align='C', fill=True)
                pdf.cell(col_widths[1], 10, 'PHCs', border=1, align='C', fill=True)
                for i, sub in enumerate(subdivisions):
                    pdf.cell(col_widths[i + 2], 10, sanitize_for_pdf(sub), border=1, align='C', fill=True)
                pdf.cell(col_widths[-1], 10, 'Average', border=1, align='C', fill=True); pdf.ln()
                pdf.set_font(FONT_FAMILY, '', 7)
                pdf.set_text_color(*BODY_COLOR)

            if idx % 2 == 0:
                pdf.set_fill_color(240, 240, 245)
                fill = True
            else:
                fill = False

            fac_name = fac['name']
            pdf.cell(col_widths[0], 7, str(idx), border=1, align='C', fill=fill)
            pdf.cell(col_widths[1], 7, sanitize_for_pdf(fac_name), border=1, fill=fill)
            for i, sub in enumerate(subdivisions):
                val = fac.get(sub)
                val_str = f"{val:.2f}" if val is not None else '-'
                pdf.cell(col_widths[i + 2], 7, val_str, border=1, align='C', fill=fill)
            avg = fac.get('Average')
            avg_str = f"{avg:.2f}" if avg is not None else '-'
            pdf.cell(col_widths[-1], 7, avg_str, border=1, align='C', fill=fill); pdf.ln()

    # --- Build the PDF ---
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Register Arial TTF
    fonts_dir = os.path.join(os.path.dirname(__file__), 'assets', 'fonts')
    if os.path.exists(os.path.join(fonts_dir, 'arial.ttf')):
        pdf.add_font('Arial', '', os.path.join(fonts_dir, 'arial.ttf'), uni=True)
        pdf.add_font('Arial', 'B', os.path.join(fonts_dir, 'arialbd.ttf'), uni=True)
        pdf.add_font('Arial', 'I', os.path.join(fonts_dir, 'ariali.ttf'), uni=True)
        FONT_FAMILY = 'Arial'

    location_name = sanitize_for_pdf(context.get('location_name', 'Report'))

    # --- TITLE PAGE ---
    pdf.add_page()
    cover_img = os.path.join(os.path.dirname(__file__), 'assets', 'cover_template_blank.png')
    if os.path.exists(cover_img):
        pdf.image(cover_img, x=0, y=0, w=210, h=297)
        pdf.set_font(FONT_FAMILY, 'B', 11)
        pdf.set_text_color(255, 255, 255)
        pdf.text(28, 137, f'of Primary Health Care Facilities in {location_name},')
        pdf.text(28, 144, 'using the Climate Health Vulnerability')
        pdf.text(28, 151, 'Assessment Tool (CHAT).')
        pdf.set_font(FONT_FAMILY, '', 11)
        pdf.text(28, 261, f'{datetime.now().strftime("%B, %Y")}')
    else:
        pdf.set_fill_color(0, 163, 255)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_fill_color(255, 255, 255)
        pdf.ellipse(80, -15, 50, 50, 'F')
        pdf.set_fill_color(200, 220, 0)
        pdf.ellipse(165, -5, 55, 55, 'F')
        pdf.set_fill_color(100, 195, 255)
        pdf.ellipse(30, 195, 80, 80, 'F')
        pdf.set_fill_color(130, 210, 255)
        pdf.ellipse(100, 210, 90, 90, 'F')
        pdf.set_font(FONT_FAMILY, 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(15, 20)
        pdf.cell(60, 8, 'eHealth', ln=0)
        pdf.set_font(FONT_FAMILY, '', 10)
        pdf.set_xy(15, 28)
        pdf.cell(60, 6, 'A F R I C A', ln=0)
        pdf.set_font(FONT_FAMILY, 'B', 34)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(15, 70)
        pdf.multi_cell(140, 16, 'Climate Health\nVulnerability\nAssessment')
        pdf.set_font(FONT_FAMILY, 'B', 13)
        pdf.set_xy(18, 130)
        pdf.multi_cell(160, 7, f'of Primary Health Care Facilities in {location_name},\nusing the Climate Health Vulnerability\nAssessment Tool (CHAT).')
        pdf.set_font(FONT_FAMILY, '', 12)
        pdf.set_xy(18, 250)
        pdf.cell(80, 8, f'{datetime.now().strftime("%B, %Y")}')

    # --- 1. EXECUTIVE SUMMARY ---
    pdf.add_page()
    add_section_header(pdf, 'Executive Summary')
    add_content(pdf, content_dict.get('executive_summary', 'No summary available.'))

    # Key Statistics Infographic
    key_stats_img = export_key_statistics_banner(stats, location_name)
    if key_stats_img:
        try:
            safe_image(pdf, key_stats_img, x=5, w=200)
            os.unlink(key_stats_img)
        except Exception:
            pass

    # --- 2. INTRODUCTION ---
    add_section_header(pdf, 'Introduction')
    intro_text = content_dict.get('introduction', 'No introduction available.')

    for remove_prefix in ['Introduction\n', 'Introduction:\n', 'Introduction ']:
        if intro_text.startswith(remove_prefix):
            intro_text = intro_text[len(remove_prefix):].strip()
            break

    intro_parts = {'intro': intro_text, 'problem': '', 'purpose': ''}
    for marker in ['Problem Statement', 'Problem statement']:
        if marker in intro_text:
            idx = intro_text.index(marker)
            intro_parts['intro'] = intro_text[:idx].strip()
            remainder = intro_text[idx:]
            for p_marker in ['Purpose and Objectives', 'Purpose and objectives']:
                if p_marker in remainder:
                    p_idx = remainder.index(p_marker)
                    intro_parts['problem'] = remainder[:p_idx].strip()
                    intro_parts['purpose'] = remainder[p_idx:].strip()
                    break
            else:
                intro_parts['problem'] = remainder.strip()
            break

    add_content(pdf, intro_parts['intro'])

    if intro_parts['problem']:
        add_subsection_header(pdf, 'Problem Statement')
        problem_text = intro_parts['problem']
        for remove in ['Problem Statement:', 'Problem Statement', 'Problem statement:', 'Problem statement']:
            problem_text = problem_text.replace(remove, '', 1).strip()
        add_content(pdf, problem_text)

    if intro_parts['purpose']:
        add_subsection_header(pdf, 'Purpose and Objectives')
        purpose_text = intro_parts['purpose']
        for remove in ['Purpose and Objectives:', 'Purpose and Objectives', 'Purpose and objectives:', 'Purpose and objectives']:
            purpose_text = purpose_text.replace(remove, '', 1).strip()
        add_content(pdf, purpose_text)

    # WHO Exposure Areas Table
    check_space(pdf, 60)
    add_subsection_header(pdf, 'Table 1: WHO adapted exposure areas')
    pdf.set_font(FONT_FAMILY, 'B', 8)
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(70, 8, 'Exposures', border=1, align='C', fill=True)
    pdf.cell(120, 8, 'Subdivisions', border=1, align='C', fill=True); pdf.ln()

    pdf.set_font(FONT_FAMILY, '', 8)
    pdf.set_text_color(*BODY_COLOR)
    who_rows = [
        ('Health Workforce', 'Human Resources; Capacity Development; Communication and Awareness Raising'),
        ('Water Sanitation and healthcare Waste', 'Monitoring and Assessment; Risk Management; Health and Safety Regulation'),
        ('Energy', 'Monitoring and Assessment; Risk Management; Health and Safety Regulation'),
        ('Infrastructure, Technologies, Products and Processes', 'Adaptation of current systems and infrastructures; Promotion of new systems and technologies; Sustainability of healthcare facility operations')
    ]
    col1_w = 70
    col2_w = 120
    line_h = 4.5
    for exp, subs in who_rows:
        chars_per_line = 85
        num_lines_col2 = max(1, -(-len(subs) // chars_per_line))
        num_lines_col1 = max(1, -(-len(exp) // 48))
        num_lines = max(num_lines_col1, num_lines_col2)
        row_h = line_h * num_lines + 3

        x_start = pdf.get_x()
        y_start = pdf.get_y()

        pdf.rect(x_start, y_start, col1_w, row_h)
        pdf.rect(x_start + col1_w, y_start, col2_w, row_h)

        pdf.set_xy(x_start + 1, y_start + 1)
        pdf.multi_cell(col1_w - 2, line_h, sanitize_for_pdf(exp), align='L')

        pdf.set_xy(x_start + col1_w + 1, y_start + 1)
        pdf.multi_cell(col2_w - 2, line_h, sanitize_for_pdf(subs), align='L')

        pdf.set_xy(x_start, y_start + row_h)

    # --- 3. METHODOLOGY ---
    add_section_header(pdf, 'Methodology/Approach')
    add_content(pdf, content_dict.get('methodology', 'No methodology available.'))

    # --- 4. FINDINGS / RESULTS ---
    add_section_header(pdf, 'Findings / Results')

    domain_tables = stats.get('domain_tables', {})
    for domain_key in ['Health Workforce', 'WASH', 'Energy', 'Infrastructure']:
        domain_data = domain_tables.get(domain_key, {})
        if not domain_data or not domain_data.get('facilities'):
            continue

        add_domain_table(pdf, domain_key, domain_data)

        chart_w = 93
        chart_h = 60
        if pdf.get_y() + chart_h + 10 > PAGE_H - PAGE_MARGIN:
            pdf.add_page()
        pdf.ln(3)
        chart_y = pdf.get_y()

        avg_img = export_domain_average_chart(domain_data, domain_data['display_name'])
        if avg_img:
            try:
                pdf.image(avg_img, x=5, y=chart_y, w=chart_w, h=chart_h)
                os.unlink(avg_img)
            except Exception:
                pass

        detail_img = export_domain_detailed_chart(domain_data, domain_data['display_name'])
        if detail_img:
            try:
                pdf.image(detail_img, x=103, y=chart_y, w=chart_w, h=chart_h)
                os.unlink(detail_img)
            except Exception:
                pass

        pdf.set_y(chart_y + chart_h + 5)

    # --- DISCUSSION ---
    add_section_header(pdf, 'Discussion')
    discussion_text = content_dict.get('discussion', 'No discussion available.')

    label_map = {
        'HEALTH WORKFORCE': 'Health Workforce',
        'WASH': 'Water, Sanitation, and Healthcare Waste (WASH)',
        'ENERGY SYSTEMS': 'Energy Systems',
        'ENERGY': 'Energy Systems',
        'INFRASTRUCTURE': 'Infrastructure, Technologies, Products, and Processes',
        'OVERALL DISCUSSION': 'Overall Discussion',
        'OVERALL': 'Overall Discussion',
    }

    parts = re.split(r'\[([A-Z][A-Z \-/&]+)\]', discussion_text)
    sections_found = []
    if len(parts) >= 3:
        for i in range(1, len(parts) - 1, 2):
            label = parts[i].strip()
            content = parts[i + 1].strip()
            display = label_map.get(label, label.title())
            if content:
                sections_found.append((display, content))

    if sections_found:
        for header, content in sections_found:
            add_subsection_header(pdf, header)
            add_content(pdf, content)
    else:
        add_content(pdf, discussion_text)

    # --- CHALLENGES AND LESSONS LEARNED ---
    add_section_header(pdf, 'Challenges and Lessons Learned')
    challenges_text = content_dict.get('challenges', 'No challenges listed.')
    for strip_line in ['Challenges and Lessons Learned', 'Challenges and lessons learned']:
        challenges_text = challenges_text.replace(strip_line + '\n', '', 1)
        challenges_text = challenges_text.replace(strip_line + ':', '', 1)
    challenges_text = challenges_text.replace('Implementation Challenges\n', '', 1)
    challenges_text = challenges_text.replace('Implementation Challenges:', 'Implementation Challenges:', 1)
    challenges_text = challenges_text.strip()
    add_content(pdf, challenges_text)

    # Domain Radar Chart
    domain_tables_for_radar = stats.get('domain_tables', {})
    radar_img = export_domain_radar_chart(domain_tables_for_radar)
    if radar_img:
        try:
            safe_image(pdf, radar_img, x=25, w=160)
            os.unlink(radar_img)
        except Exception:
            pass

    # --- RECOMMENDATIONS ---
    add_section_header(pdf, 'Recommendations')
    recommendations_text = content_dict.get('recommendations', 'No recommendations available.')
    add_content(pdf, recommendations_text)

    # Recommendations Roadmap
    roadmap_img = export_recommendations_roadmap(location_name, recommendations_text)
    if roadmap_img:
        try:
            safe_image(pdf, roadmap_img, x=5, w=200)
            os.unlink(roadmap_img)
        except Exception:
            pass

    # --- CONCLUSION ---
    add_section_header(pdf, 'Conclusion')
    add_content(pdf, content_dict.get('conclusion', 'No conclusion available.'))

    # --- REFERENCES ---
    add_section_header(pdf, 'References')
    references = (
        "1. Nigeria Climate Change Policy (2021-2030)\n"
        "2. WHO Operational Framework for Building Climate Resilient Health Systems\n"
        "3. National Health Adaptation Plan (HNAP)\n"
        "4. Facility Assessment Data (CHAT Tool, 2026)\n"
        "5. IPCC Sixth Assessment Report (Warning on Health Impacts)"
    )
    add_content(pdf, references)

    # --- FACILITY LIST ---
    facility_list_table = stats.get('facility_list_table', [])
    if facility_list_table:
        add_section_header(pdf, 'List of Facilities Assessed')

        pdf.set_font(FONT_FAMILY, 'B', 8)
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(10, 8, '#', border=1, align='C', fill=True)
        pdf.cell(100, 8, 'PHCs', border=1, align='C', fill=True)
        pdf.cell(50, 8, 'LGAs', border=1, align='C', fill=True); pdf.ln()

        pdf.set_font(FONT_FAMILY, '', 8)
        pdf.set_text_color(*BODY_COLOR)
        for idx, fac in enumerate(facility_list_table, 1):
            if pdf.get_y() > 270:
                pdf.add_page()
            pdf.cell(10, 7, str(idx), border=1, align='C')
            pdf.cell(100, 7, sanitize_for_pdf(fac.get('name', '')), border=1)
            pdf.cell(50, 7, sanitize_for_pdf(fac.get('lga', '')), border=1); pdf.ln()

    # Facility Vulnerability Heatmap
    heatmap_domain_tables = stats.get('domain_tables', {})
    heatmap_img = export_facility_heatmap(heatmap_domain_tables)
    if heatmap_img:
        try:
            safe_image(pdf, heatmap_img, x=5, w=200)
            os.unlink(heatmap_img)
        except Exception:
            pass

    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        return pdf_output.encode('latin-1')
    return bytes(pdf_output)
