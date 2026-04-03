"""
CHAT Model Evaluation - LLM Abstraction (Groq / Llama)
"""

import os
import time
import streamlit as st

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# Provider configuration
PROVIDERS = {
    "groq": {
        "name": "Groq (Llama 3.3 70B)",
        "models": {
            "comprehensive": "llama-3.3-70b-versatile",
            "moderate": "llama-3.1-8b-instant",
            "short": "llama-3.1-8b-instant",
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


def get_model_for_depth(provider_key, report_depth):
    """Get the appropriate model for the given provider and report depth."""
    provider = PROVIDERS[provider_key]
    return provider["models"].get(report_depth.lower(), provider["models"]["moderate"])


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

    # Prepend system message if not already present
    if not any(m.get("role") == "system" for m in messages):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    call_fn = _CALL_FNS[provider_key]

    start = time.time()
    text, model_used = call_fn(messages, model, max_tokens, temperature)
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
