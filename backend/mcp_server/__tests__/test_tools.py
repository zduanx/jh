"""
Unit tests for the MCP tool LOGIC (Phase 7B).

These call the tool functions directly (they're plain Python with `@mcp.tool()`
on top — see ADR-030: "thin wrappers over existing Python logic, called
in-process"). We assert the SHAPE and OWNERSHIP/scoping contracts each tool's
docstring promises:

  - search_jobs_semantic: resume-vs-query modes, limit, company filter, ownership
  - get_job:             full detail, None when missing/not owned
  - get_resume:          text or None
  - score_against_jd:    similarity signal or None when resume/job missing

The live Voyage call is faked (see conftest.fake_voyage); the pgvector search,
SQL, and ownership filters run for real against the test DB.

Run: python3 -m pytest mcp_server/__tests__/test_tools.py -v
"""
import time

import pytest

from mcp_server.server import (
    search_jobs_semantic,
    get_job,
    get_resume,
    score_against_jd,
)
from mcp_server.__tests__.conftest import fake_embedding
from models.job import Job
from models.resume import Resume


def make_job(db, user_id, *, company="anthropic", title="Staff Engineer",
             location="Remote", embed_text=None, status="ready", **kw):
    """
    Insert a job for `user_id` with a (fake) embedding and return it.

    Defaults to status="ready": the vector search (search_jobs_by_vector) only
    returns READY jobs with a non-null embedding, so seeded jobs must be READY to
    be retrievable. (get_job/score_against_jd don't filter on status.)
    """
    job = Job(
        user_id=user_id,
        company=company,
        external_id=f"ext-{int(time.time() * 1_000_000)}-{title}",
        url=f"https://example.com/{title}".replace(" ", "-"),
        title=title,
        location=location,
        status=status,
        description=kw.get("description", f"{title} working on distributed systems"),
        requirements=kw.get("requirements", "Python, infra, scale"),
        embedding=fake_embedding(embed_text or f"{title} {company}"),
    )
    db.add(job)
    db.flush()  # assign id without committing (rolled back by fixture)
    return job


def make_resume(db, user_id, *, text="Senior engineer, distributed systems, Python.",
                embed_text=None, filename="resume.pdf"):
    resume = Resume(
        user_id=user_id,
        filename=filename,
        extracted_text=text,
        embedding=fake_embedding(embed_text or text),
    )
    db.add(resume)
    db.flush()
    return resume


# --------------------------------------------------------------------------- #
# search_jobs_semantic
# --------------------------------------------------------------------------- #
class TestSearchJobsSemantic:
    def test_matches_resume_when_no_query(self, mcp_db, fake_voyage, seed_user):
        make_resume(mcp_db, seed_user.user_id)
        make_job(mcp_db, seed_user.user_id, title="Backend Engineer")
        make_job(mcp_db, seed_user.user_id, title="Data Scientist", company="meta")

        results = search_jobs_semantic(user_id=seed_user.user_id)

        assert isinstance(results, list)
        assert len(results) == 2
        # contract: each row has exactly the documented keys, best-first
        for r in results:
            assert set(r) == {"job_id", "company", "title", "location", "similarity"}
            assert -1.0 <= r["similarity"] <= 1.0
        sims = [r["similarity"] for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_no_resume_returns_empty(self, mcp_db, fake_voyage, seed_user):
        make_job(mcp_db, seed_user.user_id)
        # user has jobs but no resume -> nothing to match against
        assert search_jobs_semantic(user_id=seed_user.user_id) == []

    def test_query_mode_uses_embedding(self, mcp_db, fake_voyage, seed_user):
        # No resume on purpose: a query must still work (matches topic, not resume)
        make_job(mcp_db, seed_user.user_id, title="ML Infra Engineer")
        results = search_jobs_semantic(user_id=seed_user.user_id, query="machine learning")
        assert len(results) == 1
        assert results[0]["title"] == "ML Infra Engineer"

    def test_limit_caps_results(self, mcp_db, fake_voyage, seed_user):
        make_resume(mcp_db, seed_user.user_id)
        for i in range(5):
            make_job(mcp_db, seed_user.user_id, title=f"Role {i}")
        assert len(search_jobs_semantic(user_id=seed_user.user_id, limit=3)) == 3

    def test_company_filter(self, mcp_db, fake_voyage, seed_user):
        make_resume(mcp_db, seed_user.user_id)
        make_job(mcp_db, seed_user.user_id, company="anthropic", title="A")
        make_job(mcp_db, seed_user.user_id, company="meta", title="B")
        results = search_jobs_semantic(user_id=seed_user.user_id, company="anthropic")
        assert results
        assert all(r["company"] == "anthropic" for r in results)

    def test_company_filter_case_insensitive(self, mcp_db, fake_voyage, seed_user):
        make_resume(mcp_db, seed_user.user_id)
        make_job(mcp_db, seed_user.user_id, company="anthropic")
        assert search_jobs_semantic(user_id=seed_user.user_id, company="ANTHROPIC")

    def test_does_not_leak_other_users_jobs(self, mcp_db, fake_voyage, seed_user):
        from db.user_service import create_user
        other = create_user(mcp_db, f"other_{int(time.time()*1000)}@example.com", "Other")
        mcp_db.flush()
        make_resume(mcp_db, seed_user.user_id)
        make_job(mcp_db, other.user_id, title="Other's Secret Job")  # different owner
        results = search_jobs_semantic(user_id=seed_user.user_id)
        assert all(r["title"] != "Other's Secret Job" for r in results)


# --------------------------------------------------------------------------- #
# get_job
# --------------------------------------------------------------------------- #
class TestGetJob:
    def test_returns_full_detail(self, mcp_db, seed_user):
        job = make_job(mcp_db, seed_user.user_id, title="Platform Engineer")
        result = get_job(user_id=seed_user.user_id, job_id=job.id)
        assert result is not None
        assert result["job_id"] == job.id
        assert result["title"] == "Platform Engineer"
        assert set(result) >= {
            "job_id", "company", "title", "location", "url",
            "description", "requirements", "status",
        }

    def test_missing_returns_none(self, mcp_db, seed_user):
        assert get_job(user_id=seed_user.user_id, job_id=999_999) is None

    def test_not_owned_returns_none(self, mcp_db, seed_user):
        from db.user_service import create_user
        other = create_user(mcp_db, f"other_{int(time.time()*1000)}@example.com", "Other")
        mcp_db.flush()
        job = make_job(mcp_db, other.user_id)
        # seed_user must NOT be able to read another user's job
        assert get_job(user_id=seed_user.user_id, job_id=job.id) is None


# --------------------------------------------------------------------------- #
# get_resume
# --------------------------------------------------------------------------- #
class TestGetResume:
    def test_returns_text(self, mcp_db, seed_user):
        make_resume(mcp_db, seed_user.user_id, text="My resume body", filename="cv.pdf")
        result = get_resume(user_id=seed_user.user_id)
        assert result == {"filename": "cv.pdf", "text": "My resume body"}

    def test_none_when_no_resume(self, mcp_db, seed_user):
        assert get_resume(user_id=seed_user.user_id) is None


# --------------------------------------------------------------------------- #
# score_against_jd
# --------------------------------------------------------------------------- #
class TestScoreAgainstJd:
    def test_returns_similarity(self, mcp_db, seed_user):
        make_resume(mcp_db, seed_user.user_id)
        job = make_job(mcp_db, seed_user.user_id, title="SRE")
        result = score_against_jd(user_id=seed_user.user_id, job_id=job.id)
        assert result is not None
        assert result["job_id"] == job.id
        assert result["title"] == "SRE"
        assert -1.0 <= result["similarity"] <= 1.0

    def test_identical_vectors_similarity_one(self, mcp_db, seed_user):
        # resume and job embedded from the SAME text -> cosine ~= 1.0
        make_resume(mcp_db, seed_user.user_id, embed_text="same")
        job = make_job(mcp_db, seed_user.user_id, embed_text="same")
        result = score_against_jd(user_id=seed_user.user_id, job_id=job.id)
        assert result["similarity"] == pytest.approx(1.0, abs=1e-3)

    def test_none_when_no_resume(self, mcp_db, seed_user):
        job = make_job(mcp_db, seed_user.user_id)
        assert score_against_jd(user_id=seed_user.user_id, job_id=job.id) is None

    def test_none_when_job_missing(self, mcp_db, seed_user):
        make_resume(mcp_db, seed_user.user_id)
        assert score_against_jd(user_id=seed_user.user_id, job_id=999_999) is None
