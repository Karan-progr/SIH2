from app.services.engine import SentinelEngine


def test_seed_has_synthetic_events():
    engine = SentinelEngine()
    engine._seed(5000)
    assert len(engine.posts) == 5000
    assert all(post["metadata"]["synthetic"] for post in engine.posts)


def test_topics_and_findings_are_traceable():
    engine = SentinelEngine()
    engine._seed(100)
    narrative = engine.narrative("nar-project-orion")
    assert narrative["supporting_posts"]
    assert engine.rising_topics()[0]["trend_score"] <= 1


def test_signal_is_evidence_first():
    engine = SentinelEngine()
    engine._seed(100)
    signal = engine.signals()[0]
    assert signal["accounts_involved"] == 27
    assert signal["evidence_post_ids"]
