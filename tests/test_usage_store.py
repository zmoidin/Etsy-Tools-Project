from etsytools.storage.usage_store import get_tavily_usage, increment_tavily_usage


def test_usage_store_initializes_and_increments(tmp_path):
    usage_path = tmp_path / "usage.json"

    initial = get_tavily_usage(usage_path)
    count = increment_tavily_usage(usage_path)
    updated = get_tavily_usage(usage_path)

    assert initial["tavily_searches"] == 0
    assert count == 1
    assert updated["tavily_searches"] == 1
