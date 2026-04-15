"""
CHAT Model Evaluation - LLM Abstraction (Groq / Llama)
"""

import os
import time
import streamlit as st

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# Provider configuration
# NOTE: All depths are pinned to the same primary model so that differences
# between Brief / Moderate / Comprehensive reports come purely from the
# prompt structure and the set of sections rendered — not from model capability.
# The `fallback` list is preserved and used by `_call_groq` if the primary
# model rate-limits or errors.
PRIMARY_MODEL = "llama-3.3-70b-versatile"

PROVIDERS = {
    "groq": {
        "name": "Groq (Llama 3.3 70B)",
        "models": {
            "comprehensive":    PRIMARY_MODEL,
            "moderate":         PRIMARY_MODEL,
            "short":            PRIMARY_MODEL,
            "brief":            PRIMARY_MODEL,
            "overview summary": PRIMARY_MODEL,
            "overview":         PRIMARY_MODEL,
        },
        "fallback": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct"
        ]
    },
}

# System prompt enforcing correct acronyms (shared across all providers)
SYSTEM_PROMPT = (
    "You are an expert Climate Assessment Manager writing reports for eHealth Africa (eHA). "
    "CRITICAL: Always use these exact acronym definitions - "
    "CHAT = Climate Health Vulnerability Assessment Tool, "
    "WASH = Water, Sanitation and Healthcare Waste, "
    "PHC = Primary Health Care, "
    "WHO = World Health Organization, "
    "eHA = eHealth Africa. "
    "NEVER invent alternative expansions such as 'Climate Health Adaptation and Tracking' or 'Climate Hazards and Health Tool'. "
    "\n\nCOUNTRY AND GEOGRAPHIC SCOPE: "
    "Pay very careful attention to the geographic scope and country context of the data. "
    "For example, Niger State is a state in Nigeria - do NOT confuse it with Niger Republic (a separate West African country). "
    "FCT (Federal Capital Territory) is the same as Abuja, Nigeria. "
    "Always interpret state names (e.g., Kano State, Niger State, Borno State) within the correct country context. "
    "CHAT is used globally, so always verify and respect the specific country and sub-national context of the data provided. "
    "\n\nDATA INTEGRITY: "
    "You MUST base your analysis strictly and exclusively on the dataset provided. "
    "Do NOT hallucinate, fabricate, or infer data points that are not in the provided dataset. "
    "Do NOT introduce third-party information, external statistics, or unrelated references. "
    "Do NOT make claims that cannot be directly supported by the data given to you. "
    "Focus purely on analytics derived from the dataset. Act as an expert analyst interpreting the data as-is."
)


# Depth controls THREE things now:
#   (a) the token budget sent to the LLM,
#   (b) per-section word targets injected into prompts,
#   (c) STRUCTURAL shape of the section (how the model frames its output).
#
# The report_builder also reads depth to decide which sections, tables,
# and charts to render at all — so Brief, Moderate, and Comprehensive
# produce visibly different artifacts, not just different-length prose.
#
# Depth keys: "comprehensive" | "moderate" | "short" (alias: "brief")

DEPTH_CONFIG = {
    "comprehensive": {
        "token_multiplier": 1.0,
        "style_note": (
            "Provide a thorough, in-depth analysis with rich detail, context, and nuanced interpretation. "
            "Expand on implications, compare domain scores, and include supporting reasoning. "
            "This report will be paired with domain tables, per-domain charts, a radar plot, a roadmap, "
            "and a facility heatmap — so your prose should cross-reference those visuals where natural."
        ),
        "word_targets": {
            "executive_summary": "approximately 300-380 words",
            "introduction": "approximately 450-550 words",
            "methodology": "approximately 380-480 words",
            "discussion": "approximately 120-160 words for EACH of the 5 labeled subsections",
            "challenges": "approximately 280-360 words with 4 challenges and 3 lessons",
            "recommendations": "approximately 400-500 words, 4 bullets under EACH time category",
            "conclusion": "approximately 240-320 words across 2-3 paragraphs",
        },
    },
    "moderate": {
        "token_multiplier": 0.55,
        "style_note": (
            "Produce a NARRATIVE-ONLY report — no tables, charts, or graphs will accompany this output. "
            "The reader depends entirely on your prose, so embed concrete numbers (vulnerability index, "
            "domain averages, percentages) directly in the text rather than referring to 'the chart' or "
            "'the table'. Cover key findings and implications without exhaustive elaboration."
        ),
        "word_targets": {
            "executive_summary": "approximately 170-220 words",
            "introduction": "approximately 250-320 words",
            "methodology": "approximately 220-280 words",
            "discussion": "approximately 65-90 words for EACH of the 5 labeled subsections",
            "challenges": "approximately 160-210 words with 3 challenges and 2 lessons",
            "recommendations": "approximately 230-290 words, 3 bullets under EACH time category",
            "conclusion": "approximately 140-190 words across 2 short paragraphs",
        },
    },
    "short": {
        "token_multiplier": 0.3,
        "style_note": (
            "Produce a single-paragraph OVERVIEW SUMMARY — a short standalone narrative meant to serve as the "
            "entire report body. No tables, charts, or subsections will follow. Every sentence must carry "
            "weight. Embed the most critical numbers (overall vulnerability index, high-vulnerability %, "
            "most and least vulnerable domain) directly in the prose."
        ),
        "word_targets": {
            # For Overview Summary depth, only the overview_summary section is
            # generated — other keys kept as safe fallbacks in case something
            # asks for them.
            "overview_summary": "approximately 140-180 words as a single cohesive paragraph",
            "executive_summary": "approximately 90-130 words",
            "introduction": "approximately 130-170 words",
            "methodology": "approximately 120-160 words",
            "discussion": "approximately 35-55 words for EACH of the 5 labeled subsections",
            "challenges": "approximately 90-130 words with 2 challenges and 2 lessons",
            "recommendations": "approximately 140-190 words, 2 bullets under EACH time category",
            "conclusion": "approximately 70-110 words in a single paragraph",
        },
    },
}

# Aliases so the UI can use friendlier labels while code keeps "short" canonical.
# The UI label is "Overview Summary"; we normalize to lowercase for lookup.
DEPTH_CONFIG["brief"] = DEPTH_CONFIG["short"]
DEPTH_CONFIG["overview summary"] = DEPTH_CONFIG["short"]
DEPTH_CONFIG["overview"] = DEPTH_CONFIG["short"]


# Which sections each depth actually generates. The report_builder uses the
# same keys to decide what to render, so this is the single source of truth.
DEPTH_SECTIONS = {
    "comprehensive": [
        "executive_summary", "introduction", "methodology",
        "discussion", "challenges", "recommendations", "conclusion",
    ],
    "moderate": [
        "executive_summary", "introduction", "methodology",
        "discussion", "challenges", "recommendations", "conclusion",
    ],
    "short":             ["overview_summary"],
    "brief":             ["overview_summary"],
    "overview summary":  ["overview_summary"],
    "overview":          ["overview_summary"],
}


def _normalize_depth(report_depth):
    return (report_depth or "").strip().lower()


def get_depth_config(report_depth):
    """Return depth config (token_multiplier, style_note, word_targets)."""
    return DEPTH_CONFIG.get(_normalize_depth(report_depth), DEPTH_CONFIG["moderate"])


def get_sections_for_depth(report_depth):
    """Return the list of section keys that should be generated for this depth."""
    return DEPTH_SECTIONS.get(_normalize_depth(report_depth), DEPTH_SECTIONS["moderate"])


def get_length_instruction(report_depth, section_key):
    """Return a prompt-injectable instruction block enforcing depth-specific length + shape."""
    cfg = get_depth_config(report_depth)
    target = cfg["word_targets"].get(section_key, "")
    if not target:
        return cfg["style_note"]
    return (
        f"LENGTH REQUIREMENT (STRICT): Write {target}. "
        f"Do NOT exceed this range. {cfg['style_note']}"
    )


def get_model_for_depth(provider_key, report_depth):
    """Get the appropriate model for the given provider and report depth."""
    provider = PROVIDERS[provider_key]
    return provider["models"].get(_normalize_depth(report_depth), provider["models"]["moderate"])


def _call_groq(messages, model, max_tokens, temperature):
    """Call Groq API with fallback."""
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    models_to_try = [model] + [m for m in PROVIDERS["groq"]["fallback"] if m != model]

    for try_model in models_to_try:
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=try_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content, try_model
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                continue
            return f"Error: {error_str}", try_model

    return "AI analysis temporarily unavailable. Please try again later.", model


_CALL_FNS = {
    "groq": _call_groq,
}


def call_llm(provider_key, messages, model_tier, max_tokens, temperature=0.7):
    """
    Call an LLM provider.

    Returns: (response_text, model_used, latency_seconds)
    """
    model = get_model_for_depth(provider_key, model_tier)

    # Scale token budget by depth so Short/Moderate/Comprehensive produce
    # materially different-length responses (floor 256 to avoid truncation).
    multiplier = get_depth_config(model_tier)["token_multiplier"]
    scaled_max_tokens = max(256, int(max_tokens * multiplier))

    # Prepend system message if not already present
    if not any(m.get("role") == "system" for m in messages):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    call_fn = _CALL_FNS[provider_key]

    start = time.time()
    text, model_used = call_fn(messages, model, scaled_max_tokens, temperature)
    latency = round(time.time() - start, 2)

    return text, model_used, latency


def get_provider_names():
    """Return dict of provider_key -> display name."""
    return {k: v["name"] for k, v in PROVIDERS.items()}


def check_api_keys():
    """Check which API keys are configured."""
    return {
        "groq": bool(GROQ_API_KEY),
    }
