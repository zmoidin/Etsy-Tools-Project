from etsytools.safety.listing_checks import listing_safety_warnings, sanitize_etsy_tags


def test_sanitize_etsy_tags_enforces_count_length_and_uniqueness():
    tags = ["Very Long Keyword That Exceeds Etsy Limit", "Cat", "cat", "  Cat  "]

    result = sanitize_etsy_tags(tags)

    assert len(result) == 13
    assert all(len(tag) <= 20 for tag in result)
    assert len(result) == len(set(result))


def test_listing_safety_flags_trademark_terms_and_claims():
    listing = {
        "title": "Disney style commercial use PNG",
        "description": "Best seller guaranteed.",
        "tags": ["mickey shirt"],
    }

    warnings = listing_safety_warnings(listing)

    assert any("disney" in warning.lower() for warning in warnings)
    assert any("commercial use" in warning.lower() for warning in warnings)
    assert any("seller review required" in warning.lower() for warning in warnings)

