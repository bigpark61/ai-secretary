from statistics import fmean
from typing import Any


METRICS = {
    "production_volume": "생산량",
    "defect_rate": "불량률(%)",
    "energy_consumption": "에너지 소비량",
    "energy_efficiency": "에너지 효율",
    "downtime_percentage": "가동 중단율(%)",
    "maintenance_hours": "정비 시간",
    "energy_per_unit": "단위당 에너지",
}


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "count": 0,
            "record_range": None,
            "metrics": {},
            "trend": None,
            "trend_note": "원본 데이터에 날짜가 없어 시간 추세 대신 RecordID 순서를 비교합니다.",
        }

    metrics = {
        key: {
            "label": label,
            "average": round(fmean(float(record[key]) for record in records), 3),
            "min": round(min(float(record[key]) for record in records), 3),
            "max": round(max(float(record[key]) for record in records), 3),
        }
        for key, label in METRICS.items()
    }

    dated_records = sorted(
        (record for record in records if record.get("source_record_id") is not None),
        key=lambda record: int(record["source_record_id"]),
    )
    trend = None
    if len(dated_records) >= 2:
        cohort_size = max(1, len(dated_records) // 5)
        earlier = dated_records[:cohort_size]
        later = dated_records[-cohort_size:]
        trend = {
            "basis": "RecordID 오름차순의 앞·뒤 20% 비교 (시간순 데이터가 아님)",
            "cohort_size": cohort_size,
            "production_volume": _change(
                _mean(earlier, "production_volume"),
                _mean(later, "production_volume"),
            ),
            "defect_rate": _change(
                _mean(earlier, "defect_rate"),
                _mean(later, "defect_rate"),
            ),
        }

    source_ids = [int(record["source_record_id"]) for record in dated_records]
    return {
        "count": len(records),
        "record_range": (
            {"first": min(source_ids), "last": max(source_ids)}
            if source_ids
            else None
        ),
        "metrics": metrics,
        "trend": trend,
        "trend_note": "날짜 필드가 없어 시간 추세가 아닙니다. RecordID가 있는 원본 표본의 순서만 비교합니다.",
    }


def _mean(records: list[dict[str, Any]], key: str) -> float:
    return fmean(float(record[key]) for record in records)


def _change(earlier: float, later: float) -> dict[str, Any]:
    percent = ((later - earlier) / abs(earlier) * 100) if earlier else None
    if percent is None:
        direction = "비교 불가"
    elif percent > 2:
        direction = "증가"
    elif percent < -2:
        direction = "감소"
    else:
        direction = "유지"
    return {
        "earlier_average": round(earlier, 3),
        "later_average": round(later, 3),
        "change_percent": round(percent, 2) if percent is not None else None,
        "direction": direction,
    }
