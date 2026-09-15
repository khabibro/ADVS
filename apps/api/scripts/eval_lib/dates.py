from datetime import date


def format_date_variant(iso_date: str, variant_idx: int) -> str:
    """Renders an ISO date (YYYY-MM-DD) in one of the Korean forms
    normalize_date() is documented to accept."""
    d = date.fromisoformat(iso_date)
    variants = [
        f"{d.year}-{d.month:02d}-{d.day:02d}",
        f"{d.year}. {d.month}. {d.day}.",
        f"{d.year}/{d.month:02d}/{d.day:02d}",
        f"{d.year}년 {d.month}월 {d.day}일",
    ]
    return variants[variant_idx % len(variants)]
