
import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, DATE, or_, true, String, case
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta
from collections import defaultdict

from db.database import get_db, SessionLocal
from db.models import ResearchReport, IdentifiedProfile, Profile
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import logging

from dependencies import get_current_user
from utils.trial_utils import get_trial_limits

dashboard_router = APIRouter(tags=['Dashboard'])
_log = logging.getLogger(__name__)

# ── Simple in-process response cache ─────────────────────────────────────────
# Dashboard data is heavy to compute but changes slowly — 5-min TTL is fine.
_CACHE_TTL = timedelta(minutes=5)
_stats_cache:     dict[str, tuple[object, datetime]] = {}
_analytics_cache: dict[str, tuple[object, datetime]] = {}

def _cache_get(store: dict, key: str):
    entry = store.get(key)
    if entry and datetime.utcnow() - entry[1] < _CACHE_TTL:
        return entry[0]
    return None

def _cache_set(store: dict, key: str, value):
    store[key] = (value, datetime.utcnow())

# ── Pydantic models ───────────────────────────────────────────────────────────

class UsageStats(BaseModel):
    used: int
    limit: int
    remaining: int

class DashboardStats(BaseModel):
    total_leads: int
    avg_lead_score: float
    high_potential_leads: int
    time_saved_hours: float
    trial_mode: bool = False
    research_usage: Optional[UsageStats] = None
    classification_usage: Optional[UsageStats] = None
    lead_discovery_usage: Optional[UsageStats] = None

class AnalyticsDataPoint(BaseModel):
    date: str
    count: int

class TieredBreakdownItem(BaseModel):
    name: str
    # Current period
    hot: int = 0
    hand_raiser: int = 0
    qualified: int = 0
    unqualified: int = 0
    total: int = 0
    # Previous period (same duration, immediately before current)
    prev_hot: int = 0
    prev_hand_raiser: int = 0
    prev_qualified: int = 0
    prev_unqualified: int = 0
    prev_total: int = 0

class ReclassificationItem(BaseModel):
    name: str
    linkedin_url: Optional[str] = None
    report_id: Optional[str] = None  # ResearchReport.id — for direct link to the full report
    initial_tier: str   # tier from basic AI
    lead_score: int     # score from deep research

class ReclassificationStats(BaseModel):
    total_with_reports: int = 0
    overestimated_count: int = 0   # basic said good, research says < 40
    underestimated_count: int = 0  # basic said unqualified, research says > 70
    confirmed_high_count: int = 0  # both agree it's good
    confirmed_low_count: int = 0   # both agree it's low
    accuracy_pct: float = 0.0      # % where basic AI and research agreed
    overestimated: List[ReclassificationItem] = []
    underestimated: List[ReclassificationItem] = []

class DashboardAnalytics(BaseModel):
    period: str = "30d"
    daily_trends: List[AnalyticsDataPoint]
    # Overall tier counts
    lead_quality: Dict[str, int]              # current period {hot, hand_raiser, qualified, unqualified}
    previous_summary: Optional[Dict[str, int]] = None  # previous period
    # Breakdowns — each item embeds both current and previous period data
    competitor_breakdown: List[TieredBreakdownItem]
    keyword_breakdown: List[TieredBreakdownItem]
    source_breakdown: List[TieredBreakdownItem]  # by lead_source (apollo/keyword/competitor/linkedin_jobs/…)
    # Accuracy check — basic AI vs deep research
    reclassification: Optional[ReclassificationStats] = None

# ── Stats endpoint ────────────────────────────────────────────────────────────

@dashboard_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    import time as _time
    _t0 = _time.monotonic()

    cache_key = str(current_user.organization_id or current_user.id)
    if cached := _cache_get(_stats_cache, cache_key):
        _log.info("stats: cache hit in %.0fms", (_time.monotonic() - _t0) * 1000)
        return cached

    _log.info("stats: cache miss (key=%s)", cache_key)
    trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"

    # Single scan: COUNT(*), AVG(score), COUNT(*) FILTER (WHERE score > 70)
    report_scope = ResearchReport.organization_id == current_user.organization_id \
        if current_user.organization_id \
        else ResearchReport.created_by_id == current_user.id

    report_q = select(
        func.count(ResearchReport.id),
        func.avg(ResearchReport.lead_score),
        func.count(ResearchReport.id).filter(ResearchReport.lead_score > 70),
    ).where(report_scope)

    research_usage = classification_usage = lead_discovery_usage = None

    async def _run(q):
        _ts = _time.monotonic()
        async with SessionLocal() as s:
            _tc = _time.monotonic()
            rows = (await s.execute(q)).all()
            _log.info("stats _run: connect=%.0fms query=%.0fms",
                      (_tc - _ts) * 1000, (_time.monotonic() - _tc) * 1000)
            return rows

    if trial_mode:
        limits      = get_trial_limits()
        res_limit   = limits["research_limit"]
        class_limit = limits["classification_limit"]
        id_limit    = limits["identified_limit"]

        id_scope = IdentifiedProfile.organization_id == current_user.organization_id \
            if current_user.organization_id \
            else IdentifiedProfile.created_by_id == current_user.id

        # Single scan: total identified + classified count in one query
        id_q = select(
            func.count(IdentifiedProfile.id),
            func.count(IdentifiedProfile.id).filter(
                or_(IdentifiedProfile.is_fit == True, IdentifiedProfile.intent.isnot(None))
            ),
        ).where(id_scope)

        (report_rows, id_rows) = await asyncio.gather(_run(report_q), _run(id_q))

        total_leads, avg_score, high_potential_leads = report_rows[0]
        id_total, class_used = id_rows[0]

        total_leads        = total_leads or 0
        avg_score          = avg_score or 0.0
        high_potential_leads = high_potential_leads or 0

        research_usage       = UsageStats(used=total_leads, limit=res_limit,   remaining=max(0, res_limit - total_leads))
        classification_usage = UsageStats(used=class_used,  limit=class_limit, remaining=max(0, class_limit - class_used))
        lead_discovery_usage = UsageStats(used=id_total,    limit=id_limit,    remaining=max(0, id_limit - id_total))
    else:
        report_rows = await _run(report_q)
        total_leads, avg_score, high_potential_leads = report_rows[0]
        total_leads          = total_leads or 0
        avg_score            = avg_score or 0.0
        high_potential_leads = high_potential_leads or 0

    _log.info("stats: total=%.0fms", (_time.monotonic() - _t0) * 1000)

    result = DashboardStats(
        total_leads=total_leads,
        avg_lead_score=round(float(avg_score), 1),
        high_potential_leads=high_potential_leads,
        time_saved_hours=total_leads * 0.5,
        trial_mode=trial_mode,
        research_usage=research_usage,
        classification_usage=classification_usage,
        lead_discovery_usage=lead_discovery_usage,
    )
    _cache_set(_stats_cache, cache_key, result)
    return result

# ── Analytics endpoint ────────────────────────────────────────────────────────

@dashboard_router.get("/dashboard/analytics", response_model=DashboardAnalytics)
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
    period: str = Query("30d", pattern="^(7d|14d|30d|90d|12w|12m)$"),
):
    analytics_cache_key = f"{current_user.organization_id or current_user.id}:{period}"
    if cached := _cache_get(_analytics_cache, analytics_cache_key):
        return cached

    # ── Time windows ──────────────────────────────────────────────────────────
    now = datetime.utcnow()
    if period == "12m":
        since = now - timedelta(days=365)
        trunc_expr = func.date_trunc("month", IdentifiedProfile.created_at).label("date")
    elif period == "12w":
        since = now - timedelta(weeks=12)
        trunc_expr = func.date_trunc("week", IdentifiedProfile.created_at).label("date")
    elif period == "90d":
        since = now - timedelta(days=90)
        trunc_expr = cast(IdentifiedProfile.created_at, DATE).label("date")
    elif period == "14d":
        since = now - timedelta(days=14)
        trunc_expr = cast(IdentifiedProfile.created_at, DATE).label("date")
    elif period == "7d":
        since = now - timedelta(days=7)
        trunc_expr = cast(IdentifiedProfile.created_at, DATE).label("date")
    else:
        since = now - timedelta(days=30)
        trunc_expr = cast(IdentifiedProfile.created_at, DATE).label("date")

    prev_since = since - (now - since)  # equal-length window immediately before current

    # ── Scope helper ─────────────────────────────────────────────────────────
    def _scope(q):
        if current_user.organization_id:
            return q.where(IdentifiedProfile.organization_id == current_user.organization_id)
        return q.where(IdentifiedProfile.created_by_id == current_user.id)

    # ── Tier classifier ───────────────────────────────────────────────────────
    # profile_metadata["is_buy_signal"] is intentionally excluded — reading it
    # requires a TEXT→JSONB cast + TOAST fetch for every row (major perf cost).
    # Intent and depth already cover hot-tier detection adequately.
    def _tier(is_fit, is_dm, intent, depth) -> str:
        if is_fit and is_dm:
            if intent in ("prospect_pain", "pain_point") \
               or depth in ("discovery_friction", "complaining_keywords"):
                return "hot"
            if intent == "hand_raiser":
                return "hand_raiser"
            return "qualified"
        return "unqualified"

    def _empty_tier() -> Dict[str, int]:
        return {"hot": 0, "hand_raiser": 0, "qualified": 0, "unqualified": 0}

    # Bucket label: 'current' or 'previous' per row — lets us do one scan for both periods
    _bucket = case(
        (IdentifiedProfile.created_at >= since, "current"),
        else_="previous",
    ).label("bucket")

    # Lateral unnest expression for source_posts JSONB array
    posts_func = func.jsonb_array_elements(
        cast(func.coalesce(IdentifiedProfile.source_posts, "[]"), JSONB)
    ).table_valued("value").lateral("post")

    # ── Build 5 independent queries (current + previous in one scan each) ────

    # 1. Growth trend (current period only — aggregated, no prev needed)
    trends_q = _scope(
        select(trunc_expr, func.count(IdentifiedProfile.id))
        .where(IdentifiedProfile.created_at >= since)
        .group_by(trunc_expr)
        .order_by(trunc_expr)
    )

    # 2. Tier quality — one scan covering both current and previous period
    tier_q = _scope(
        select(
            _bucket,
            IdentifiedProfile.is_fit,
            IdentifiedProfile.is_decision_maker,
            IdentifiedProfile.intent,
            IdentifiedProfile.post_topic_depth,
        ).where(IdentifiedProfile.created_at >= prev_since)
    )

    # 3. Competitor/keyword lateral — one scan covering both periods
    # Pre-filter rows with no source_posts before the lateral unnest — avoids
    # running jsonb_array_elements on the majority of rows that have NULL/'[]'.
    lateral_q = _scope(
        select(
            _bucket,
            cast(posts_func.c.value, JSONB)["competitor"].astext.label("competitor_name"),
            IdentifiedProfile.is_fit,
            IdentifiedProfile.is_decision_maker,
            IdentifiedProfile.intent,
            IdentifiedProfile.post_topic_depth,
        )
        .join(posts_func, true())
        .where(
            IdentifiedProfile.created_at >= prev_since,
            IdentifiedProfile.source_posts.isnot(None),
            IdentifiedProfile.source_posts != "[]",
            IdentifiedProfile.source_posts != "",
        )
    )

    # 4. Source breakdown — one scan covering both periods
    source_q = _scope(
        select(
            _bucket,
            IdentifiedProfile.lead_source,
            IdentifiedProfile.is_fit,
            IdentifiedProfile.is_decision_maker,
            IdentifiedProfile.intent,
            IdentifiedProfile.post_topic_depth,
        ).where(IdentifiedProfile.created_at >= prev_since, IdentifiedProfile.lead_source.isnot(None))
    )

    # 5. Reclassification join (ResearchReport × IdentifiedProfile)
    reclassif_q = (
        select(
            IdentifiedProfile.is_fit,
            IdentifiedProfile.is_decision_maker,
            IdentifiedProfile.intent,
            IdentifiedProfile.post_topic_depth,
            ResearchReport.lead_score,
            ResearchReport.fullname,
            ResearchReport.normalized_linkedin_url,
            ResearchReport.id.cast(String).label("report_id"),
        )
        .join(ResearchReport, ResearchReport.normalized_linkedin_url == IdentifiedProfile.normalized_linkedin_url)
        .where(ResearchReport.lead_score.isnot(None), ResearchReport.created_at >= since)
    )
    if current_user.organization_id:
        reclassif_q = reclassif_q.where(
            IdentifiedProfile.organization_id == current_user.organization_id,
            ResearchReport.organization_id    == current_user.organization_id,
        )
    else:
        reclassif_q = reclassif_q.where(
            IdentifiedProfile.created_by_id == current_user.id,
            ResearchReport.created_by_id    == current_user.id,
        )

    # ── Execute all 5 queries in parallel (separate sessions = separate connections) ──
    import time as _time

    async def _run(name: str, q):
        _ts = _time.monotonic()
        async with SessionLocal() as s:
            rows = (await s.execute(q)).all()
            _log.info("analytics _run[%s]: %.0fms (%d rows)", name, (_time.monotonic() - _ts) * 1000, len(rows))
            return rows

    trend_rows, tier_rows, lateral_rows, src_rows, reclassif_rows = await asyncio.gather(
        _run("trends",    trends_q),
        _run("tiers",     tier_q),
        _run("lateral",   lateral_q),
        _run("source",    source_q),
        _run("reclassif", reclassif_q),
    )

    # ── Parse trend ───────────────────────────────────────────────────────────
    daily_trends = [AnalyticsDataPoint(date=str(r[0]), count=r[1]) for r in trend_rows]

    # ── Parse tier quality ────────────────────────────────────────────────────
    lead_quality     = _empty_tier()
    previous_summary = _empty_tier()
    for bucket, *rest in tier_rows:
        t = _tier(*rest)
        if bucket == "current":
            lead_quality[t] += 1
        else:
            previous_summary[t] += 1

    # ── Parse lateral (competitor + keyword breakdown) ────────────────────────
    curr_comp: dict = defaultdict(_empty_tier)
    curr_kw:   dict = defaultdict(_empty_tier)
    prev_comp: dict = defaultdict(_empty_tier)
    prev_kw:   dict = defaultdict(_empty_tier)
    for bucket, comp_name, *rest in lateral_rows:
        if not comp_name:
            continue
        t = _tier(*rest)
        is_curr = bucket == "current"
        if comp_name.startswith("Keyword: "):
            (curr_kw if is_curr else prev_kw)[comp_name.removeprefix("Keyword: ")][t] += 1
        else:
            (curr_comp if is_curr else prev_comp)[comp_name][t] += 1

    # ── Parse source breakdown ────────────────────────────────────────────────
    curr_src: dict = defaultdict(_empty_tier)
    prev_src: dict = defaultdict(_empty_tier)
    for bucket, lead_source, *rest in src_rows:
        (curr_src if bucket == "current" else prev_src)[lead_source or "unknown"][_tier(*rest)] += 1

    # ── Build TieredBreakdownItem lists ───────────────────────────────────────
    def _build_items(curr_d: dict, prev_d: dict, limit: int = 10) -> List[TieredBreakdownItem]:
        all_names = set(curr_d) | set(prev_d)
        items = []
        for name in all_names:
            c = curr_d.get(name, _empty_tier())
            p = prev_d.get(name, _empty_tier())
            items.append(TieredBreakdownItem(
                name=name,
                hot=c["hot"], hand_raiser=c["hand_raiser"], qualified=c["qualified"], unqualified=c["unqualified"],
                total=sum(c.values()),
                prev_hot=p["hot"], prev_hand_raiser=p["hand_raiser"], prev_qualified=p["qualified"], prev_unqualified=p["unqualified"],
                prev_total=sum(p.values()),
            ))
        items.sort(key=lambda x: -x.total)
        return items[:limit]

    comp_items = _build_items(curr_comp, prev_comp)
    kw_items   = _build_items(curr_kw,   prev_kw)
    src_items  = _build_items(curr_src,  prev_src, limit=20)

    # ── Reclassification accuracy: basic AI tier vs deep research score ────────
    SCORE_LOW  = 40
    SCORE_HIGH = 70

    overestimated:  list[ReclassificationItem] = []
    underestimated: list[ReclassificationItem] = []
    confirmed_high = confirmed_low = 0

    for is_fit, is_dm, intent, depth, score, name, url, report_id in reclassif_rows:
        if score is None:
            continue
        initial = _tier(is_fit, is_dm, intent, depth)
        positive = initial in ("hot", "hand_raiser", "qualified")
        if positive and score < SCORE_LOW:
            overestimated.append(ReclassificationItem(
                name=name or "Unknown", linkedin_url=url, report_id=report_id,
                initial_tier=initial, lead_score=score,
            ))
        elif not positive and score > SCORE_HIGH:
            underestimated.append(ReclassificationItem(
                name=name or "Unknown", linkedin_url=url, report_id=report_id,
                initial_tier=initial, lead_score=score,
            ))
        elif positive and score >= SCORE_HIGH:
            confirmed_high += 1
        else:
            confirmed_low += 1

    overestimated.sort(key=lambda x: x.lead_score)
    underestimated.sort(key=lambda x: -x.lead_score)

    total_with_reports = len(reclassif_rows)
    agreed = confirmed_high + confirmed_low
    accuracy_pct = round(agreed / total_with_reports * 100, 1) if total_with_reports else 0.0

    reclassification = ReclassificationStats(
        total_with_reports=total_with_reports,
        overestimated_count=len(overestimated),
        underestimated_count=len(underestimated),
        confirmed_high_count=confirmed_high,
        confirmed_low_count=confirmed_low,
        accuracy_pct=accuracy_pct,
        overestimated=overestimated[:10],
        underestimated=underestimated[:10],
    )

    _log.info("analytics (%s): %d keywords, %d competitors, %d channels, %d reclassified",
              period, len(kw_items), len(comp_items), len(src_items), len(overestimated) + len(underestimated))

    result = DashboardAnalytics(
        period=period,
        daily_trends=daily_trends,
        lead_quality=lead_quality,
        previous_summary=previous_summary,
        competitor_breakdown=comp_items,
        keyword_breakdown=kw_items,
        source_breakdown=src_items,
        reclassification=reclassification,
    )
    _cache_set(_analytics_cache, analytics_cache_key, result)
    return result
