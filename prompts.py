"""
CHAT Model Evaluation - Prompt Functions
All 8 prompt functions copied from app/app.py, wired to providers.call_llm().
"""

import json
from collections import Counter
from providers import (
    call_llm,
    get_model_for_depth,
    get_length_instruction,
    get_sections_for_depth,
)


def clean_ai_output(text):
    """Detect and truncate LLM repetition loops."""
    if not text or len(text) < 300:
        return text

    sentences = [s.strip() for s in text.replace('\n', '. ').split('. ') if len(s.strip()) > 10]
    if len(sentences) < 5:
        return text

    seen = {}
    cut_index = None
    for i, sent in enumerate(sentences):
        key = ' '.join(sent.lower().split())[:80]
        if key in seen:
            seen[key]['count'] += 1
            if seen[key]['count'] >= 3:
                cut_index = seen[key].get('second_pos', i)
                break
            else:
                seen[key]['second_pos'] = i
        else:
            seen[key] = {'count': 1}

    if cut_index is not None and cut_index > 2:
        good_text = '. '.join(sentences[:cut_index]) + '.'
        return good_text

    words = text.split()
    if len(words) > 150:
        tail_start = len(words) * 2 // 3
        tail = words[tail_start:]
        freq = Counter(w.lower().strip('.,;:-') for w in tail if len(w) > 3)
        if freq:
            top_word, top_count = freq.most_common(1)[0]
            if top_count > len(tail) * 0.2:
                rejoined = ' '.join(words[:tail_start])
                last_period = rejoined.rfind('.')
                if last_period > len(rejoined) // 3:
                    return rejoined[:last_period + 1]

    return text


def strip_ai_title(text, title):
    """Strip LLM-echoed section titles from the start of AI-generated text."""
    cleaned = text.strip()
    for sep in ['\n', ':\n', ':']:
        if cleaned.startswith(title + sep):
            return cleaned[len(title + sep):].strip()
    if cleaned.lower().startswith(title.lower() + '\n'):
        return cleaned[len(title) + 1:].strip()
    if cleaned.lower().startswith(title.lower() + ':'):
        return cleaned[len(title) + 1:].strip()
    first_line = cleaned.split('\n')[0].strip()
    title_words = title.lower().split()
    if title_words and all(w in first_line.lower() for w in title_words) and len(first_line) < 120:
        return '\n'.join(cleaned.split('\n')[1:]).strip()
    return cleaned


def _call_and_clean(provider, messages, report_depth, max_tokens, temperature):
    """Call LLM and clean the output. Returns (cleaned_text, model_used, latency)."""
    raw, model_used, latency = call_llm(provider, messages, report_depth, max_tokens, temperature)
    cleaned = clean_ai_output(raw)
    return cleaned, model_used, latency


def get_ai_executive_summary(stats, context, report_depth, provider):
    """Generate executive summary matching WHO template format."""
    domain_summary = ""
    if 'domain_tables' in stats:
        for domain_key, domain_data in stats['domain_tables'].items():
            domain_summary += f"- {domain_data['display_name']}: Average {domain_data.get('domain_avg', 'N/A')}/3.0\n"

    prompt = f"""
    You are an expert Climate Health Consultant writing an Executive Summary for the CHAT deployment report for {context['location_name']}.

    IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
    - CHAT = Climate Health Vulnerability Assessment Tool (CHAT). Do NOT call it "Climate Health Adaptation and Tracking" or "Climate Hazards and Health Tool" or any other variation.
    - WASH = Water, Sanitation and Healthcare Waste (WASH)
    - PHC = Primary Health Care (PHC)
    - WHO = World Health Organization (WHO)
    - eHA = eHealth Africa (eHA)

    KEY STATISTICS:
    - Location: {context['location_name']} ({context['location_type']})
    - Facilities Assessed: {stats['facilities']}
    - Total Assessments: {stats['total']:,}
    - Average Vulnerability Index: {stats['avg_vuln']}/3.0 (1=High Vulnerability, 3=Low Vulnerability)
    - High Vulnerability: {stats['high_pct']}%
    - Medium Vulnerability: {stats['medium_pct']}%
    - Low Vulnerability: {stats['low_pct']}%

    DOMAIN AVERAGES:
    {domain_summary}

    TEMPLATE FORMAT TO FOLLOW:
    Write the Executive Summary as a professional narrative (NOT bullet points). Structure it as:
    1. Opening paragraph: Present findings from the CHAT deployment. State the vulnerability index ({stats['avg_vuln']}/3.0) and what it means — if below 1.5, state facilities are critically vulnerable; if 1.5-2.0, moderately vulnerable; if above 2.0, showing some resilience but with gaps.
    2. Second paragraph: Describe the digitized WHO checklist and digital dashboard for real-time analysis.
    3. Third paragraph: Compare the four domain scores. Identify which domain is MOST vulnerable (lowest score) and which is LEAST vulnerable (highest score). Explain what these specific scores mean for healthcare delivery in {context['location_name']}.
    4. Closing paragraph: Emphasize CHAT's value and how findings inform targeted interventions.

    CRITICAL: Your analysis must INTERPRET the scores, not just list them. For example:
    - A domain score of 1.15 means "critically vulnerable, requiring immediate intervention"
    - A domain score of 1.8 means "moderately vulnerable with some resilience"
    - A domain score of 2.5 means "relatively resilient but with room for improvement"
    - {stats['high_pct']}% high vulnerability means the tone should reflect the actual urgency level

    IMPORTANT: Base your analysis STRICTLY on the data provided above. Do NOT hallucinate or fabricate data.

    WRITING STYLE: Vary your sentence structure and word choice. Do NOT use the same opening phrases across reports.
    Avoid formulaic language. Each report should read uniquely while maintaining professional tone.
    Keep evidence-based. Do NOT use markdown formatting.

    {get_length_instruction(report_depth, "executive_summary")}
    """
    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 1024, temperature=0.8)


def get_ai_introduction(stats, context, report_depth, provider):
    """Generate Introduction with Problem Statement and Purpose/Objectives."""
    domain_intro = ""
    if 'domain_tables' in stats:
        for domain_key, domain_data in stats['domain_tables'].items():
            domain_intro += f"- {domain_data['display_name']}: Average {domain_data.get('domain_avg', 'N/A')}/3.0\n"

    prompt = f"""Write the Introduction for a Climate Health Vulnerability Assessment Report for {context['location_name']}.

IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
- CHAT = Climate Health Vulnerability Assessment Tool (CHAT). Do NOT call it "Climate Health Adaptation and Tracking" or "Climate Hazards and Health Tool" or any other variation.
- WASH = Water, Sanitation and Healthcare Waste (WASH)
- PHC = Primary Health Care (PHC)
- WHO = World Health Organization (WHO)
- eHA = eHealth Africa (eHA)

ASSESSMENT CONTEXT:
- Location: {context['location_name']} ({context['location_type']})
- Facilities Assessed: {stats['facilities']}
- Total Assessments: {stats['total']:,}
- LGAs Covered: {stats['lgas']}
- Overall Vulnerability Index: {stats['avg_vuln']}/3.0 (1=High Vulnerability, 3=Low Vulnerability)
- High Vulnerability: {stats['high_pct']}% | Medium: {stats['medium_pct']}% | Low: {stats['low_pct']}%
Domain Scores:
{domain_intro}

Write the introduction covering these points:
1. Opening: Climate-related hazards (flooding, drought, heat stress) threaten healthcare systems in {context['location_name']}. PHC facilities are critical but vulnerable. Reference the assessment scale (vulnerability index {stats['avg_vuln']}/3.0 with {stats['high_pct']}% high vulnerability).
2. Describe CHAT as eHA's digital tool built on the WHO checklist, assessing 4 domains. Mention {stats['facilities']} facilities were assessed across {stats['lgas']} LGAs.
3. Problem Statement: PHC facilities face increasing climate risks, paper-based tools are inadequate, CHAT addresses the gap.
4. Purpose and Objectives: Assess vulnerabilities, generate credible data. List objectives:
   - Identify climate-related vulnerabilities across selected PHCs
   - Provide evidence to guide targeted resilience-building interventions
   - Support data-driven planning and policy development
   - Strengthen preparedness and response capacity within health facilities

CRITICAL: Your introduction must reflect the ACTUAL severity level of {context['location_name']}. If {stats['high_pct']}% of facilities are highly vulnerable, the tone should convey urgency. If vulnerability is moderate, reflect that. The writing must match the data.

WRITING STYLE: Use varied sentence structures. Each report should read distinctly. Do not use any markdown formatting. Use plain text only.

{get_length_instruction(report_depth, "introduction")}"""
    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 1500, temperature=0.75)


def get_ai_methodology(stats, context, report_depth, provider):
    """Generate Methodology matching template detail level."""
    prompt = f"""
    Write a Methodology/Approach section for the CHAT Climate Health Vulnerability Assessment for {context['location_name']}.

    IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
    - CHAT = Climate Health Vulnerability Assessment Tool (CHAT). Do NOT call it "Climate Health Adaptation and Tracking" or "Climate Hazards and Health Tool" or any other variation.
    - WASH = Water, Sanitation and Healthcare Waste (WASH)
    - PHC = Primary Health Care (PHC)
    - WHO = World Health Organization (WHO)
    - eHA = eHealth Africa (eHA)

    Include these specific details:
    1. A Vulnerability Assessment methodology was applied to evaluate susceptibility to floods, heatwaves, and droughts.
    2. The assessment used the digitized WHO climate vulnerability checklist within the CHAT platform.
    3. Trained enumerators conducted structured, in-person interviews with facility heads and key staff.
    4. Enumerators were trained using a standardized curriculum for consistency.
    5. The process included supervisory oversight from trained government personnel and technical support from eHA.
    6. A pre-pilot session was conducted to simulate the actual assessment before full deployment.
    7. Following the assessment, a comprehensive debrief meeting was organized with stakeholders.
    8. Note limitations: some eligible facilities were excluded due to security constraints and limited resources.
    9. Total: {stats['facilities']} facilities assessed across {stats['lgas']} LGAs.

    IMPORTANT: Base all content STRICTLY on the data and context provided. Do NOT fabricate statistics or introduce external information.

    WRITING STYLE: Vary your sentence openings and phrasing. Do NOT use identical wording across different reports.
    Rephrase the methodology steps naturally each time while keeping the factual content accurate.

    Write as flowing prose paragraphs, NOT bullet points. Professional tone.
    Do NOT use markdown formatting.

    {get_length_instruction(report_depth, "methodology")}
    """
    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 1200, temperature=0.75)


def get_ai_domain_discussion(stats, context, report_depth, provider):
    """Generate per-domain Discussion section matching template format."""
    domain_data = stats.get('domain_tables', {})
    domain_details = ""
    for domain_key, data in domain_data.items():
        facilities = data.get('facilities', [])
        if facilities:
            avgs = [f['Average'] for f in facilities if f.get('Average') is not None]
            min_avg = min(avgs) if avgs else 0
            max_avg = max(avgs) if avgs else 0
            most_vuln = min(facilities, key=lambda x: x.get('Average', 999)) if facilities else {}
            domain_details += f"\n{data['display_name']}:\n"
            domain_details += f"  - Score range: {min_avg:.2f} to {max_avg:.2f}\n"
            domain_details += f"  - Most vulnerable facility: {most_vuln.get('name', 'N/A')} ({most_vuln.get('Average', 'N/A')})\n"
            domain_details += f"  - Domain average: {data.get('domain_avg', 'N/A')}\n"

    prompt = f"""Write the content for a Discussion section for the CHAT climate health vulnerability report for {context['location_name']}.

IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
- CHAT = Climate Health Vulnerability Assessment Tool (CHAT). Do NOT call it "Climate Health Adaptation and Tracking" or "Climate Hazards and Health Tool" or any other variation.
- WASH = Water, Sanitation and Healthcare Waste (WASH)
- PHC = Primary Health Care (PHC)
- WHO = World Health Organization (WHO)
- eHA = eHealth Africa (eHA)

Use the following data to write the discussion:
{domain_details}
Overall Vulnerability Index: {stats['avg_vuln']}/3.0, High Vulnerability: {stats['high_pct']}%

CRITICAL FORMAT INSTRUCTIONS:
You MUST write exactly 5 sections, each starting with a label line on its own. Use this EXACT format:

[HEALTH WORKFORCE]
Write one paragraph discussing the vulnerability scores, key issues like limited capacity development, weak communication, and insufficient emergency training. Note that some facilities showed moderate resilience.

[WASH]
Write one paragraph discussing vulnerability scores, positive findings like basic monitoring practices, and challenges like climate-sensitive water supply and waste management during floods.

[ENERGY SYSTEMS]
Write one paragraph discussing this as one of the most vulnerable domains with wide disparities in reliability. Note risks to cold chain management, emergency services, and night-time delivery. Note facilities with alternative energy showed stronger resilience.

[INFRASTRUCTURE]
Write one paragraph discussing generally moderate vulnerabilities, limited climate-adapted infrastructure, weak technology integration, and limited sustainability planning.

[OVERALL DISCUSSION]
Write one paragraph summarizing how climate risks pose significant operational challenges, alignment with WHO global assessments, and how CHAT demonstrates the effectiveness of digital vulnerability assessments.

RULES:
- Each section MUST start with the label in square brackets on its own line (e.g., [HEALTH WORKFORCE])
- Do NOT write "Discussion" as a title
- Do NOT repeat the label text inside the paragraph
- Base your discussion STRICTLY on the data provided above
- Vary your analytical language and sentence structure. Avoid formulaic phrasing that reads the same across reports.
- Use different ways to present the same types of findings (e.g., don't always start with "The [domain] domain shows...")
- Do not use any markdown formatting. Use plain text only.

{get_length_instruction(report_depth, "discussion")}"""
    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 2048, temperature=0.8)


def get_ai_challenges(stats, context, report_depth, provider):
    """Generate Challenges and Lessons Learned."""
    domain_summary = ""
    if 'domain_tables' in stats:
        for domain_key, domain_data in stats['domain_tables'].items():
            domain_avg = domain_data.get('domain_avg', 'N/A')
            domain_summary += f"- {domain_data['display_name']}: Average Score {domain_avg}/3.0\n"

    prompt = f"""
    Write a 'Challenges and Lessons Learned' section for {context['location_name']}.

    IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
    - CHAT = Climate Health Vulnerability Assessment Tool (CHAT). Do NOT call it "Climate Health Adaptation and Tracking" or "Climate Hazards and Health Tool" or any other variation.
    - WASH = Water, Sanitation and Healthcare Waste (WASH)
    - PHC = Primary Health Care (PHC)
    - WHO = World Health Organization (WHO)
    - eHA = eHealth Africa (eHA)

    ASSESSMENT DATA:
    - Location: {context['location_name']} ({context['location_type']})
    - Facilities Assessed: {stats['facilities']}
    - Overall Vulnerability Index: {stats['avg_vuln']}/3.0 (Scale: 1=High Vulnerability, 3=Low Vulnerability)
    - High Vulnerability: {stats['high_pct']}%
    - Medium Vulnerability: {stats['medium_pct']}%
    - Low Vulnerability: {stats['low_pct']}%

    DOMAIN SCORES:
    {domain_summary}

    IMPORTANT: Do NOT repeat the section title "Challenges and Lessons Learned" at the start of your output.
    Do NOT write "Implementation Challenges" as a standalone subtitle line.
    Start directly with the content.

    Structure:
    Start with "Key implementation challenges identified include:" then list the challenges as bullet points.
    The challenges MUST be specific to the {context['location_name']} assessment data above. Reference specific vulnerability scores,
    the most vulnerable domains, and the percentage of high-vulnerability facilities. Do NOT use generic challenges — tailor each
    point to the actual findings from this assessment.

    Then write "Key lessons learned from the project include:" then list the lessons as bullet points.
    The lessons MUST reflect what the data reveals about {context['location_name']}. Reference which domains showed the
    biggest gaps, what the vulnerability distribution tells us, and how the CHAT tool performed in this specific context.

    IMPORTANT: Base all content STRICTLY on the assessment data provided. Do NOT fabricate or introduce information not supported by the data.

    WRITING STYLE: Phrase each challenge and lesson differently from other reports. Use varied vocabulary and sentence patterns.

    Write concisely. Use plain text, no markdown formatting. Do NOT add any section titles or subtitles.

    {get_length_instruction(report_depth, "challenges")}
    """
    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 1024, temperature=0.75)


def get_ai_recommendations(stats, context, report_depth, provider):
    """Generate time-categorized Recommendations matching template format."""
    domain_summary = ""
    if 'domain_tables' in stats:
        for domain_key, domain_data in stats['domain_tables'].items():
            domain_avg = domain_data.get('domain_avg', 'N/A')
            domain_summary += f"- {domain_data['display_name']}: Average Score {domain_avg}/3.0\n"

    prompt = f"""
    Generate Recommendations for the CHAT report for {context['location_name']}.

    IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
    - CHAT = Climate Health Vulnerability Assessment Tool (CHAT). Do NOT call it "Climate Health Adaptation and Tracking" or "Climate Hazards and Health Tool" or any other variation.
    - WASH = Water, Sanitation and Healthcare Waste (WASH)
    - PHC = Primary Health Care (PHC)
    - WHO = World Health Organization (WHO)
    - eHA = eHealth Africa (eHA)

    VULNERABILITY DATA FROM THE ASSESSMENT:
    - Location: {context['location_name']} ({context['location_type']})
    - Facilities Assessed: {stats['facilities']}
    - Overall Vulnerability Index: {stats['avg_vuln']}/3.0 (Scale: 1=High Vulnerability, 3=Low Vulnerability)
    - High Vulnerability: {stats['high_pct']}%
    - Medium Vulnerability: {stats['medium_pct']}%
    - Low Vulnerability: {stats['low_pct']}%

    DOMAIN VULNERABILITY SCORES:
    {domain_summary}

    CRITICAL INSTRUCTIONS:
    - Recommendations MUST directly address the domains with the LOWEST scores (most vulnerable).
    - Recommendations MUST be specific to {context['location_name']} and its facilities — do NOT write generic recommendations.
    - Base every recommendation on the actual vulnerability data above. Do NOT introduce external data or fabricate statistics.
    - Prioritize domains with scores closest to 1.0 (highest vulnerability) in the short-term recommendations.

    STRUCTURE: THREE time categories (Short-Term, Medium-Term, Long-Term). The exact number of bullets per
    category is dictated by the LENGTH REQUIREMENT below — pick the most relevant/highest-priority recommendations
    that fit the count. Use the items below as examples of the TYPES of recommendations expected; adapt them
    to the data.

    CRITICAL FORMAT RULES (the roadmap infographic parser depends on these):
    - Each category MUST appear on its own line as one of exactly these headers:
          Short-Term (0-12 months)
          Medium-Term (1-3 years)
          Long-Term (3-5 years)
    - Under each header, every recommendation MUST begin with a hyphen followed by a space: "- ".
    - Do NOT use asterisks, bullets (\u2022), numbers (1., 2.), or any other marker.
    - Keep each bullet to ONE line of concrete, actionable text (aim for 8-18 words).
    - Do NOT repeat the category header inside the bullets.
    - Leave one blank line between categories.

    Short-Term (0-12 months) examples:
    - Conduct climate risk awareness training for health workers
    - Strengthen WASH monitoring and safety protocols
    - Institutionalize routine CHAT assessments
    - Improve facility-level documentation and preparedness planning

    Medium-Term (1-3 years) examples:
    - Invest in reliable and sustainable energy systems (e.g., solar hybrid systems)
    - Upgrade facility infrastructure to withstand flooding and heat
    - Develop facility-level climate emergency preparedness plans
    - Integrate CHAT data into {context['location_name']} health planning systems

    Long-Term (3-5 years) examples:
    - Scale CHAT across all LGAs in {context['location_name']}
    - Develop climate-resilient infrastructure standards for PHCs
    - Integrate climate resilience indicators into national health system monitoring frameworks
    - Strengthen collaboration between health, environment, and disaster management agencies

    Tailor the above to specifically reflect the vulnerability scores and data provided. Use plain text, no markdown. Keep each bullet actionable and specific to {context['location_name']}.

    WRITING STYLE: Word each recommendation differently. Avoid using the exact same phrasing across different state reports. Vary how you reference scores and data.

    {get_length_instruction(report_depth, "recommendations")}
    """
    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 1500, temperature=0.8)


def get_ai_conclusion(stats, context, report_depth, provider):
    """Generate Conclusion matching template format."""
    domain_conclusion = ""
    if 'domain_tables' in stats:
        domain_scores = []
        for domain_key, domain_data in stats['domain_tables'].items():
            avg = domain_data.get('domain_avg', 'N/A')
            domain_conclusion += f"- {domain_data['display_name']}: {avg}/3.0\n"
            if avg != 'N/A':
                domain_scores.append((domain_data['display_name'], float(avg)))
        if domain_scores:
            most_vuln = min(domain_scores, key=lambda x: x[1])
            least_vuln = max(domain_scores, key=lambda x: x[1])
            domain_conclusion += f"\nMost vulnerable domain: {most_vuln[0]} ({most_vuln[1]}/3.0)"
            domain_conclusion += f"\nLeast vulnerable domain: {least_vuln[0]} ({least_vuln[1]}/3.0)"

    prompt = f"""
    Write a Conclusion section for the CHAT report for {context['location_name']}.

    IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
    - CHAT = Climate Health Vulnerability Assessment Tool (CHAT)
    - WASH = Water, Sanitation and Healthcare Waste (WASH)
    - PHC = Primary Health Care (PHC)
    - WHO = World Health Organization (WHO)
    - eHA = eHealth Africa (eHA)

    ASSESSMENT DATA TO REFERENCE:
    - Location: {context['location_name']}
    - Facilities Assessed: {stats['facilities']}
    - Overall Vulnerability Index: {stats['avg_vuln']}/3.0
    - High Vulnerability: {stats['high_pct']}% | Medium: {stats['medium_pct']}% | Low: {stats['low_pct']}%
    Domain Scores:
    {domain_conclusion}

    Your conclusion MUST:
    1. Reference the actual vulnerability index ({stats['avg_vuln']}/3.0) and interpret what it means for {context['location_name']}
    2. Name the most and least vulnerable domains with their specific scores
    3. State what gaps remain based on the actual domain scores (not generic statements)
    4. Recommend scaling CHAT and coordinated investments specific to {context['location_name']}'s needs

    IMPORTANT: Every sentence must be traceable to the data above. Do NOT write generic conclusions.

    WRITING STYLE: Write a unique conclusion. Vary your opening — do NOT start with "The deployment of CHAT..." every time.

    Write as 2-3 cohesive paragraphs. Professional tone. No markdown formatting.

    {get_length_instruction(report_depth, "conclusion")}
    """
    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 800, temperature=0.8)


def get_ai_facility_assessment(facility_data, provider):
    """Generate AI assessment for a specific facility."""
    prompt = f"""
    Provide a detailed vulnerability assessment for this health facility.

    IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
    - CHAT = Climate Health Vulnerability Assessment Tool (CHAT). Do NOT call it "Climate Health Adaptation and Tracking" or "Climate Hazards and Health Tool" or any other variation.
    - WASH = Water, Sanitation and Healthcare Waste (WASH)
    - PHC = Primary Health Care (PHC)

    FACILITY: {facility_data['name']}
    LOCATION: {facility_data['lga']}, {facility_data['state']}

    VULNERABILITY DATA:
    - Total Assessments: {facility_data['total_assessments']}
    - Vulnerability Index: {facility_data['avg_vuln']}/3.0
    - High Vulnerability: {facility_data['high_pct']}%
    - Medium Vulnerability: {facility_data['medium_pct']}%
    - Low Vulnerability: {facility_data['low_pct']}%

    BY HAZARD: {json.dumps(facility_data['hazards'])}
    BY SECTION: {json.dumps(facility_data['sections'])}

    Provide:
    1. Overall Assessment (2-3 sentences)
    2. Critical Vulnerabilities (bullet points)
    3. Specific Recommendations for this facility (3-5 actionable items)

    IMPORTANT: Base your assessment STRICTLY on the data provided above. Do NOT hallucinate or introduce external data. Every claim must be supported by the vulnerability scores given.

    Be specific to {facility_data['name']}. No markdown formatting.
    """
    messages = [
        {"role": "system", "content": "You are a health facility climate resilience specialist. Base all analysis strictly on the provided data. Do not fabricate statistics or introduce external information."},
        {"role": "user", "content": prompt}
    ]
    return _call_and_clean(provider, messages, "comprehensive", 800, temperature=0.75)


def get_ai_overview_summary(stats, context, report_depth, provider):
    """Generate a single consolidated overview summary for Overview-depth reports.

    These reports skip the multi-section structure and render one short
    narrative that stands alone — covering location, scope, headline
    vulnerability findings, most/least vulnerable domain, and the single
    highest-priority recommendation.
    """
    domain_lines = ""
    most_vuln_name, most_vuln_score = None, None
    least_vuln_name, least_vuln_score = None, None
    if 'domain_tables' in stats:
        domain_scores = []
        for _, domain_data in stats['domain_tables'].items():
            avg = domain_data.get('domain_avg', 'N/A')
            domain_lines += f"- {domain_data['display_name']}: {avg}/3.0\n"
            if avg not in ('N/A', None):
                try:
                    domain_scores.append((domain_data['display_name'], float(avg)))
                except (TypeError, ValueError):
                    pass
        if domain_scores:
            most_vuln_name, most_vuln_score = min(domain_scores, key=lambda x: x[1])
            least_vuln_name, least_vuln_score = max(domain_scores, key=lambda x: x[1])

    prompt = f"""Write an OVERVIEW SUMMARY for the CHAT Climate Health Vulnerability Assessment for {context['location_name']}.

This overview summary is the ENTIRE report body — no other sections, no tables, no charts will follow it.
It must stand alone as a complete, publication-ready summary — a self-contained overview written as
connected prose for a professional reader.

IMPORTANT - USE THESE EXACT ACRONYMS AND DEFINITIONS (do NOT invent alternative names):
- CHAT = Climate Health Vulnerability Assessment Tool (CHAT)
- WASH = Water, Sanitation and Healthcare Waste (WASH)
- PHC = Primary Health Care (PHC)
- WHO = World Health Organization (WHO)
- eHA = eHealth Africa (eHA)

KEY DATA:
- Location: {context['location_name']} ({context['location_type']})
- Facilities assessed: {stats['facilities']} across {stats['lgas']} LGAs
- Total assessments: {stats['total']:,}
- Overall vulnerability index: {stats['avg_vuln']}/3.0 (1=High Vulnerability, 3=Low Vulnerability)
- High vulnerability: {stats['high_pct']}% | Medium: {stats['medium_pct']}% | Low: {stats['low_pct']}%

DOMAIN AVERAGES:
{domain_lines}
Most vulnerable domain: {most_vuln_name} ({most_vuln_score}/3.0)
Least vulnerable domain: {least_vuln_name} ({least_vuln_score}/3.0)

STRUCTURE — write as ONE cohesive paragraph that flows through:
1. A single opening sentence naming the location, the tool (CHAT), and the scope ({stats['facilities']} PHCs across {stats['lgas']} LGAs).
2. The headline vulnerability finding — state the index {stats['avg_vuln']}/3.0 and interpret it (critically / moderately / relatively resilient).
3. The most vulnerable domain ({most_vuln_name}) and what it means, contrasted briefly with the least vulnerable ({least_vuln_name}).
4. A single highest-priority recommendation specific to {context['location_name']}'s data.
5. A one-line closing on CHAT's value.

RULES:
- ONE paragraph only. No bullet points, no subheadings, no section titles.
- Every claim must trace back to the data above. Do NOT fabricate.
- No markdown formatting. Plain prose only.
- Do NOT refer to "the chart" or "the table" — nothing visual will accompany this text.

{get_length_instruction(report_depth, "overview_summary")}"""

    messages = [{"role": "user", "content": prompt}]
    return _call_and_clean(provider, messages, report_depth, 600, temperature=0.75)


# Map of section key -> prompt function. Single source of truth for what
# function produces which section. generate_all_sections picks from here
# based on the depth.
_SECTION_FUNCTIONS = {
    "overview_summary":  get_ai_overview_summary,
    "executive_summary": get_ai_executive_summary,
    "introduction":      get_ai_introduction,
    "methodology":       get_ai_methodology,
    "discussion":        get_ai_domain_discussion,
    "challenges":        get_ai_challenges,
    "recommendations":   get_ai_recommendations,
    "conclusion":        get_ai_conclusion,
}


def generate_all_sections(stats, context, report_depth, provider, progress_callback=None):
    """
    Generate the report sections appropriate for the given depth.
    - Overview Summary: one consolidated standalone narrative only.
    - Moderate: seven narrative sections (no tables/charts will accompany them).
    - Comprehensive: seven narrative sections (paired with tables/charts in PDF).

    Returns dict with section texts and metadata (model, latency, word_count per section).
    """
    sections = {}
    section_keys = get_sections_for_depth(report_depth)
    total = len(section_keys)

    for i, name in enumerate(section_keys):
        fn = _SECTION_FUNCTIONS.get(name)
        if fn is None:
            continue

        if progress_callback:
            progress_callback(i / total, f"Generating {name.replace('_', ' ').title()}...")

        text, model_used, latency = fn(stats, context, report_depth, provider)
        sections[name] = {
            "text": text,
            "model": model_used,
            "latency_seconds": latency,
            "word_count": len(text.split()) if text else 0,
        }

    if progress_callback:
        progress_callback(1.0, "Complete!")

    return sections
