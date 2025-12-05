# Image flagging

The image flagging system automatically identifies inappropriate or problematic content in product images to help maintain Open Food Facts' image quality standards.

## How it works

Image flagging uses multiple detection methods to identify content that may not be appropriate for a food database:

1. **Face Detection** – Uses Google Cloud Vision's Face Detection API to identify images containing human faces.
2. **Label Annotation** – Scans for labels indicating the presence of humans, pets, electronics, or other non-food items.
3. **Safe Search** – Uses Google Cloud Vision's Safe Search API to detect adult content or violence.
4. **Text Detection** – Analyzes OCR text for keywords related to beauty products or other inappropriate content.

When flagged content is detected, an `image_flag` prediction is generated with details about the issue and the associated confidence level. These predictions trigger notifications to moderation services where humans can review potentially problematic images.

## Detection Methods

### Face Detection

The system processes `faceAnnotations` from Google Cloud Vision to detect human faces. If multiple faces are detected, the one with the highest confidence score is used. Only faces with a detection confidence ≥ 0.6 are flagged to minimize false positives.

Prediction data includes:

- `type`: "face_annotation"
- `label`: "face"
- `likelihood`: Detection confidence score

### Label Annotation Detection

The system flags images containing specific labels from Google Cloud Vision with confidence scores ≥ 0.6. Only the first matching label is flagged per image.

**Human-related labels**:

- Face, Head, Selfie, Hair, Forehead, Chin, Cheek
- Arm, Tooth, Human Leg, Ankle, Eyebrow, Ear, Neck, Jaw, Nose
- Facial Expression, Glasses, Eyewear
- Child, Baby, Human

**Other flagged labels**:

- **Pets**: Dog, Cat
- **Technology**: Computer, Laptop, Refrigerator
- **Clothing**: Jeans, Shoe

The prediction data includes:

- `type`: "label_annotation"
- `label`: The detected label (lowercase)
- `likelihood`: Label confidence score

### Safe Search Detection

The Safe Search API flags the following categories only if marked as "VERY_LIKELY":

- **Adult content** – Sexually explicit material
- **Violence** – Graphic or violent imagery

The prediction data includes:

- `type`: "safe_search_annotation"
- `label`: "adult" or "violence"
- `likelihood`: Likelihood level name

### Text-based Detection

The system scans OCR-extracted text for keywords from predefined keyword files. Only the first matching keyword is flagged per image.

- **Beauty products** – Cosmetic-related terms from beauty keyword file
- **Miscellaneous** – Other inappropriate content keywords from miscellaneous keyword file

The prediction data includes:

- `type`: "text"
- `label`: "beauty" or "miscellaneous"
- `text`: The matched text phrase
