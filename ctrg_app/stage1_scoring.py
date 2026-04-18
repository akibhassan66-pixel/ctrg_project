from decimal import Decimal

from .models import Stage1Reviews


SCORE_FIELDS = (
    "score_originality",
    "score_clarity",
    "score_lit_review",
    "score_methodology",
    "score_impact",
    "score_publication",
    "score_budget",
    "score_timeframe",
)


def calculate_stage1_total(*scores):
    total = sum(int(score or 0) for score in scores)
    return Decimal(total).quantize(Decimal("0.00"))


def calculate_stage1_total_for_review(review):
    return calculate_stage1_total(*(getattr(review, field_name, 0) for field_name in SCORE_FIELDS))


def ensure_stage1_total(review):
    if review.total_percentage is not None:
        return review.total_percentage

    total = calculate_stage1_total_for_review(review)
    Stage1Reviews.objects.filter(stage1_review_id=review.stage1_review_id).update(total_percentage=total)
    review.total_percentage = total
    return total
