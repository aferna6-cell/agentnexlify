"""
scripts.leadgen - Internal lead-generation CLI for AgentNexLiFy outreach.

Pulls local businesses from Google Places, enriches with email addresses
scraped from each business website, deduplicates, and writes a CSV ready
for cold-email tools (Instantly, Apollo, etc.).

Usage:
    python -m scripts.leadgen.build_leads --vertical "roofing" --city "Austin, TX" --out leads.csv

This package does NOT touch FastAPI, Supabase, tenants, or any backend schema.
"""
