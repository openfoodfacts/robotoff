from typing import List, Dict

from robotoff.insights.ocr.dataclass import OCRResult, SafeSearchAnnotationLikelihood


LABELS_TO_FLAG = {'Face', 'Head', 'Selfie', 'Hair', 'Forehead', 'Chin', 'Cheek',
                  'Arm', 'Tooth', 'Leg', 'Human Leg', 'Ankle',
                  'Eyebrow', 'Ear', 'Neck', 'Jaw', 'Nose', 'Smile', 'Facial Expression',
                  'Glasses', 'Eyewear', 'Gesture', 'Thumb',
                  'Footwear', 'Jeans', 'Shoe',
                  'Child', 'Baby', 'Human',
                  'Dog', 'Cat',
                  'Computer', 'Laptop', 'Refrigerator',
                  }


def flag_image(ocr_result: OCRResult) -> List[Dict]:
    safe_search_annotation = ocr_result.get_safe_search_annotation()
    label_annotations = ocr_result.get_label_annotations()
    insights: List[Dict] = []

    if safe_search_annotation:
        for key in ('adult', 'violence'):
            value: SafeSearchAnnotationLikelihood = \
                getattr(safe_search_annotation, key)
            if value >= SafeSearchAnnotationLikelihood.VERY_LIKELY:
                insights.append({
                    'type': key,
                    'likelihood': value.name,
                })

    for label_annotation in label_annotations:
        if (label_annotation.description in LABELS_TO_FLAG and
                label_annotation.score >= 0.6):
            insights.append({
                'type': label_annotation.description.lower(),
                'likelihood': label_annotation.score
            })
            break

    return insights
