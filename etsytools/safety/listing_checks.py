from __future__ import annotations

import re


TRADEMARK_RISK_TERMS = {
    "barbie",
    "disney",
    "harry potter",
    "hello kitty",
    "mickey",
    "nike",
    "pokemon",
    "star wars",
    "taylor swift",
}

UNSUPPORTED_CLAIM_PATTERNS = {
    "commercial use": "Only use this if you personally own or grant those rights.",
    "copyright free": "Avoid unless you verified rights ownership.",
    "guaranteed": "Avoid guarantees about sales, print outcomes, or platform results.",
    "best seller": "Avoid sales-rank claims unless you can prove them.",
    "trademark": "Avoid implying trademark permission unless documented.",
}


def sanitize_etsy_tags(tags: list[str], target_count: int = 13) -> list[str]:
    """Normalize Etsy tags to Etsy's 20-character / 13-tag constraints."""
    cleaned_tags: list[str] = []
    for tag in tags:
        t = re.sub(r"\s+", " ", str(tag).strip().lower())[:20]
        if t and t not in cleaned_tags:
            cleaned_tags.append(t)

    default_keywords = [
        "digital design png",
        "clipart downloads",
        "sublimation print",
        "instant download",
        "shirt graphic",
        "printable clip art",
        "diy transfer",
        "png download",
        "craft supply",
        "digital artwork",
        "print file",
        "transparent png",
        "downloadable art",
    ]
    for kw in default_keywords:
        if len(cleaned_tags) >= target_count:
            break
        kw_clean = kw[:20]
        if kw_clean not in cleaned_tags:
            cleaned_tags.append(kw_clean)

    return cleaned_tags[:target_count]


def listing_safety_warnings(listing: dict) -> list[str]:
    """Return seller-review warnings for legally or financially risky copy."""
    text = " ".join(
        [
            str(listing.get("title", "")),
            str(listing.get("description", "")),
            " ".join(str(t) for t in listing.get("tags", [])),
        ]
    ).lower()

    warnings: list[str] = []
    for term in sorted(TRADEMARK_RISK_TERMS):
        if term in text:
            warnings.append(
                f"Trademark/IP risk: `{term}` appears in the listing copy. Verify rights before publishing."
            )

    for pattern, explanation in UNSUPPORTED_CLAIM_PATTERNS.items():
        if pattern in text:
            warnings.append(f"Claim review: `{pattern}` appears in the copy. {explanation}")

    warnings.append(
        "Seller review required: verify Etsy policy compliance, rights ownership, file quality, and AI disclosure requirements before publishing."
    )
    return warnings
