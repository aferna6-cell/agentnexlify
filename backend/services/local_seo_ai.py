"""Local SEO AI runners — Claude-backed SEO/GEO/keyword analysis.

Extracted from `backend/routers/local_seo.py` to keep the router thin.
All functions are async; all call `call_claude_messages` and return parsed JSON.
"""

import json
import logging
from typing import Optional

import anthropic

from backend.config import settings
from backend.services.llm_runtime import call_claude_messages
from backend.services.local_seo_scoring import (
    _parse_json_array_response,
    _parse_json_object_response,
)

logger = logging.getLogger(__name__)


async def _generate_keywords(business_type: Optional[str], city: Optional[str]) -> list[str]:
    """Use Claude to generate local keyword suggestions based on business type and city."""
    if not business_type and not city:
        return []

    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping keyword generation")
        return []

    location_desc = city or "your area"
    biz_desc = business_type or "local business"
    raw = ""

    try:
        resp = await call_claude_messages(
            operation="seo.generate_keywords",
            model="claude-sonnet-4-6",
            max_tokens=400,
            temperature=0.5,
            timeout=30.0,
            system=(
                "You are a local SEO expert. Return ONLY a JSON array of keyword strings. "
                "No explanations, no markdown, just the raw JSON array."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Generate 10-15 high-value local SEO keywords for a {biz_desc} "
                    f"in {location_desc}. Include a mix of:\n"
                    "- Service-based keywords (e.g., 'emergency plumber near me')\n"
                    "- Location-based keywords (e.g., 'plumber in [city]')\n"
                    "- Long-tail keywords (e.g., 'best affordable plumber [city]')\n"
                    "Return ONLY the JSON array."
                ),
            }],
            metadata={"business_type": biz_desc, "city": location_desc},
        )
        raw = resp.text.strip()
        keywords = _parse_json_array_response(raw)
        return [str(k) for k in keywords[:20]]
    except (json.JSONDecodeError, ValueError):
        logger.error("Failed to parse keyword suggestions JSON from Claude: %.200s", raw)
        return []
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during keyword generation")
        return []
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during keyword generation")
        return []
    except anthropic.APIError as e:
        logger.error("Anthropic API error during keyword generation: %s", str(e))
        return []
    except Exception:
        logger.error("Keyword generation failed unexpectedly", exc_info=True)
        return []


async def _run_seo_audit_ai(pages_json: list, extracted_text: str, business_name: str, business_type: str) -> dict:
    """Use Claude AI to perform comprehensive SEO analysis on crawled website content."""
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping SEO audit AI analysis")
        return {}

    page_summaries = []
    for page in pages_json[:20]:
        page_url = page.get("url", "unknown")
        page_content = page.get("content", page.get("markdown", page.get("text", "")))
        if isinstance(page_content, str) and len(page_content) > 3000:
            page_content = page_content[:3000] + "\n[truncated]"
        page_summaries.append(f"--- PAGE: {page_url} ---\n{page_content}")

    all_pages_text = "\n\n".join(page_summaries)
    if len(all_pages_text) > 30000:
        all_pages_text = all_pages_text[:30000] + "\n\n[Additional pages truncated]"

    prompt = f"""Analyze this website for SEO quality. The business is "{business_name}" ({business_type}).

WEBSITE CONTENT:
{all_pages_text}

Analyze these SEO factors and return a JSON object with this EXACT structure:
{{
  "overall_score": <0-100 integer>,
  "categories": {{
    "technical": {{
      "score": <0-100>,
      "issues": [
        {{"severity": "critical|warning|passed", "title": "...", "description": "...", "recommendation": "..."}}
      ]
    }},
    "content": {{
      "score": <0-100>,
      "issues": [...]
    }},
    "on_page": {{
      "score": <0-100>,
      "issues": [...]
    }},
    "user_experience": {{
      "score": <0-100>,
      "issues": [...]
    }}
  }},
  "recommendations": ["actionable recommendation 1", "actionable recommendation 2", ...]
}}

Check for:
TECHNICAL:
- Meta titles present, unique, 50-60 chars
- Meta descriptions present, unique, 150-160 chars
- Heading structure (single H1 per page, logical H2-H6 hierarchy)
- Image alt text coverage
- Internal linking structure
- HTTPS usage
- Canonical tags
- robots.txt/sitemap indicators

CONTENT:
- Content quality and depth
- Keyword usage and density
- Duplicate content indicators
- Fresh/dated content
- Content length per page
- Local SEO content (city/location mentions)

ON-PAGE:
- URL structure (clean, descriptive)
- Schema markup indicators
- Open Graph / social meta tags
- Mobile viewport meta
- External link quality

USER EXPERIENCE:
- Page structure clarity
- Navigation depth
- Call-to-action presence
- Contact information visibility
- Mobile-friendly indicators from HTML structure

Return ONLY the raw JSON object, no markdown fences or explanations."""
    raw = ""

    try:
        resp = await call_claude_messages(
            operation="seo.run_audit",
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0.2,
            timeout=60.0,
            max_retries=1,
            retry_delay_seconds=1.0,
            system=(
                "You are an expert SEO auditor. Analyze websites and return structured JSON audit results. "
                "Be specific and actionable in your recommendations. Score fairly based on actual evidence in the content. "
                "Return ONLY valid JSON, no markdown fences."
            ),
            messages=[{"role": "user", "content": prompt}],
            metadata={"business_name": business_name, "business_type": business_type, "page_count": min(len(pages_json), 20)},
        )
        raw = resp.text.strip()
        return _parse_json_object_response(raw)
    except (json.JSONDecodeError, ValueError):
        logger.error("Failed to parse SEO audit JSON from Claude: %.500s", raw)
        return {}
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during SEO audit")
        return {}
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during SEO audit")
        return {}
    except anthropic.APIError as e:
        logger.error("Anthropic API error during SEO audit: %s", str(e))
        return {}
    except Exception:
        logger.error("SEO audit AI analysis failed unexpectedly", exc_info=True)
        return {}


async def _run_geo_score_ai(
    business_name: str,
    business_type: str,
    city: str,
    website_url: str,
    extracted_text: Optional[str] = None,
) -> dict:
    """Use Claude AI to estimate GEO (Generative Engine Optimization) visibility."""
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping GEO scoring")
        return {}

    website_context = ""
    if extracted_text:
        truncated = extracted_text[:5000]
        if len(extracted_text) > 5000:
            truncated += "\n[truncated]"
        website_context = f"\n\nWEBSITE CONTENT SAMPLE:\n{truncated}"

    prompt = f"""Evaluate the AI/GEO (Generative Engine Optimization) visibility for this business:

Business Name: {business_name}
Business Type: {business_type}
City: {city}
Website: {website_url}{website_context}

GEO (Generative Engine Optimization) measures how visible and recommendable a business is when people ask AI assistants (ChatGPT, Claude, Perplexity, Google Gemini) for local business recommendations.

Analyze and return a JSON object with this EXACT structure:
{{
  "overall_score": <0-100 integer>,
  "platform_scores": {{
    "chatgpt": <0-100>,
    "claude": <0-100>,
    "perplexity": <0-100>,
    "gemini": <0-100>
  }},
  "visibility_factors": [
    {{
      "factor": "factor name",
      "status": "strong|moderate|weak",
      "score": <0-100>,
      "explanation": "why this matters and current state"
    }}
  ],
  "recommendations": [
    "specific actionable recommendation 1",
    "specific actionable recommendation 2"
  ]
}}

Evaluate these visibility factors:
1. Brand Authority — Is this business likely known to AI training data? (reviews, press, citations)
2. Content Quality — Does the website have substantive, unique content AI can learn from?
3. Local Citations — Would the business appear in local directories, Google Business, Yelp, etc.?
4. Structured Data — Does the website have schema markup that AI can parse?
5. Topical Authority — Is the website focused and authoritative in its niche?
6. Review Presence — Are there reviews AI platforms might index?
7. Social Signals — Social media presence and engagement
8. E-E-A-T Signals — Experience, Expertise, Authoritativeness, Trustworthiness

Score conservatively. Most small local businesses score 20-50 unless they have strong online presence.
Return ONLY the raw JSON object, no markdown fences."""
    raw = ""

    try:
        resp = await call_claude_messages(
            operation="seo.geo_score",
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.3,
            timeout=45.0,
            max_retries=1,
            retry_delay_seconds=1.0,
            system=(
                "You are an expert in GEO (Generative Engine Optimization) and AI visibility. "
                "Score businesses on how likely AI platforms are to recommend them. "
                "Be realistic and conservative — most small businesses have low AI visibility. "
                "Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": prompt}],
            metadata={"business_name": business_name, "business_type": business_type, "city": city},
        )
        raw = resp.text.strip()
        return _parse_json_object_response(raw)
    except (json.JSONDecodeError, ValueError):
        logger.error("Failed to parse GEO score JSON from Claude: %.500s", raw)
        return {}
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during GEO scoring")
        return {}
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during GEO scoring")
        return {}
    except anthropic.APIError as e:
        logger.error("Anthropic API error during GEO scoring: %s", str(e))
        return {}
    except Exception:
        logger.error("GEO scoring AI analysis failed unexpectedly", exc_info=True)
        return {}


async def _analyze_keywords_ai(
    keywords: list[str],
    business_type: str,
    city: str,
) -> list[dict]:
    """Use Claude AI to analyze keyword competitiveness and ranking potential."""
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured; skipping keyword analysis")
        return []

    keywords_str = "\n".join(f"- {kw}" for kw in keywords)
    prompt = f"""Analyze these keywords for a {business_type} in {city}:

{keywords_str}

For each keyword, return a JSON array of objects with this EXACT structure:
[
  {{
    "keyword": "the keyword",
    "difficulty_score": <1-100 integer, 100 being hardest>,
    "estimated_position": "1-3" or "4-10" or "11-20" or "21-50" or "50+",
    "search_volume_estimate": "high" or "medium" or "low" or "very_low",
    "recommendations": ["recommendation 1", "recommendation 2"]
  }}
]

Guidelines:
- difficulty_score: Consider competition level. Generic keywords (e.g., "plumber") are 80-100. Long-tail local keywords (e.g., "emergency plumber in [small city]") are 20-50.
- estimated_position: Where a well-optimized local business page would likely rank. Be realistic.
- search_volume_estimate: Relative search volume for the local market.
- recommendations: 1-3 specific tips to rank for this keyword.

Return ONLY the raw JSON array, no markdown fences."""
    raw = ""

    try:
        resp = await call_claude_messages(
            operation="seo.analyze_keywords",
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            timeout=45.0,
            max_retries=1,
            retry_delay_seconds=1.0,
            system=(
                "You are an expert local SEO analyst. Analyze keyword competitiveness for local businesses. "
                "Be realistic about ranking potential. Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": prompt}],
            metadata={"business_type": business_type, "city": city, "keyword_count": len(keywords)},
        )
        raw = resp.text.strip()
        return _parse_json_array_response(raw)
    except (json.JSONDecodeError, ValueError):
        logger.error("Failed to parse keyword analysis JSON from Claude: %.500s", raw)
        return []
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limited during keyword analysis")
        return []
    except anthropic.AuthenticationError:
        logger.error("Anthropic API auth failure during keyword analysis")
        return []
    except anthropic.APIError as e:
        logger.error("Anthropic API error during keyword analysis: %s", str(e))
        return []
    except Exception:
        logger.error("Keyword analysis AI failed unexpectedly", exc_info=True)
        return []
