from typing import Dict, List

from robotoff.insights.ocr.dataclass import OCRResult, SafeSearchAnnotationLikelihood


def flag_image(ocr_result: OCRResult) -> List[Dict]:
    safe_search_annotation = ocr_result.get_safe_search_annotation()
    label_annotations = ocr_result.get_label_annotations()
    insights: List[Dict] = []

    if safe_search_annotation:
        for key in ("adult", "violence"):
            value: SafeSearchAnnotationLikelihood = getattr(safe_search_annotation, key)
            if value >= SafeSearchAnnotationLikelihood.VERY_LIKELY:
                insights.append(
                    {
                        "type": key,
                        "likelihood": value.name,
                    }
                )

    for label_annotation in label_annotations:
        if (
            label_annotation.description in ("Face", "Head", "Selfie")
            and label_annotation.score >= 0.8
        ):
            insights.append(
                {
                    "type": label_annotation.description.lower(),
                    "likelihood": label_annotation.score,
                }
            )
            break

    return insights
