"""Pydantic models for Local SEO endpoints — field names match database table columns."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SEOProfileResponse(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    completeness_score: int = 0
    missing_fields: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    keyword_suggestions: List[str] = Field(default_factory=list)
    last_analyzed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DashboardWidgetResponse(BaseModel):
    completeness_score: int = 0
    top_recommendations: List[str] = Field(default_factory=list)
    review_count: int = 0
    keyword_count: int = 0


# --- SEO Audit models (match seo_audits table) ---

class SEOIssue(BaseModel):
    category: str
    severity: str  # "critical", "warning", "passed"
    title: str
    description: str
    recommendation: Optional[str] = None
    page_url: Optional[str] = None


class SEOCategoryScore(BaseModel):
    score: int = 0
    issues: List[SEOIssue] = Field(default_factory=list)


class SEOAuditResponse(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    overall_score: int = 0
    categories: Dict[str, Any] = Field(default_factory=dict)
    critical_issues: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    passed_checks: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    pages_analyzed: int = 0
    created_at: Optional[str] = None


class SEOAuditHistoryItem(BaseModel):
    id: str
    overall_score: int = 0
    pages_analyzed: int = 0
    critical_count: int = 0
    warning_count: int = 0
    passed_count: int = 0
    created_at: Optional[str] = None


# --- GEO Score models (match geo_scores table) ---

class GEOScoreRequest(BaseModel):
    business_name: Optional[str] = Field(None, max_length=200)
    business_type: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=2000)


class GEOScoreResponse(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    overall_score: int = 0
    platform_scores: Dict[str, Any] = Field(default_factory=dict)
    visibility_factors: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None


# --- Keyword Tracking models (match keyword_rankings table) ---

class KeywordTrackRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1, max_length=20)


class KeywordRankingItem(BaseModel):
    id: Optional[str] = None
    keyword: str
    difficulty_score: int = 50
    estimated_position: Optional[str] = None
    search_volume_estimate: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)
    last_analyzed_at: Optional[str] = None


class KeywordRankingsResponse(BaseModel):
    tenant_id: str
    keywords: List[KeywordRankingItem] = Field(default_factory=list)


# --- Competitor Analysis ---

class CompetitorRequest(BaseModel):
    competitors: List[str] = Field(..., min_length=1, max_length=5, description="Competitor business names (1-5)")
