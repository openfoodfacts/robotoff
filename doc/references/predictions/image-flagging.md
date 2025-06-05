# Image flagging

The image flagging system automatically identifies inappropriate or problematic content in product images to help maintain Open Food Facts' image quality standards.

## How it works

Image flagging uses multiple detection methods to identify content that may not be appropriate for a food database:

1. **Face Detection**: Uses Google Cloud Vision's Face Detection API to identify images containing human faces
2. **Label Annotation**: Scans for specific labels that indicate human content, pets, electronics, or other non-food items
3. **Safe Search**: Detects adult content or violence using Google Cloud Vision's Safe Search API
4. **Text Detection**: Searches OCR text for keywords related to beauty products or other inappropriate content

When any flagged content is detected, an `image_flag` prediction is generated with details about what was found and the confidence level.

## Detection Methods

### Face Detection

The system processes Google Cloud Vision's `faceAnnotations` to detect human faces in images. When multiple faces are detected, the one with the highest confidence is selected. Only faces with detection confidence ≥ 0.6 are flagged to reduce false positives.

The prediction data includes:

- `type`: "face_annotation"
- `label`: "face"
- `likelihood`: Detection confidence score

### Label Annotation Detection

The system flags images containing specific labels from Google Cloud Vision with confidence ≥ 0.6:

**Human-related labels**:

- Face, Head, Selfie, Hair, Forehead, Chin, Cheek
- Arm, Tooth, Human Leg, Ankle, Eyebrow, Ear, Neck, Jaw, Nose
- Facial Expression, Glasses, Eyewear
- Child, Baby, Human

**Other flagged content**:

- Pets: Dog, Cat
- Technology: Computer, Laptop, Refrigerator
- Clothing: Jeans, Shoe

Labels with confidence ≥ 0.6 are flagged as `label_annotation` type predictions.

### 3. Safe Search Detection

Google Cloud Vision's Safe Search API detects:

- **Adult content**: Sexually explicit material
- **Violence**: Violent or graphic content

Only content marked as "VERY_LIKELY" for these categories is flagged.

### 4. Text-based Detection

The system scans OCR text for keywords related to:

- **Beauty products**: Cosmetic-related terms that may indicate non-food products
- **Miscellaneous**: Other inappropriate content identifiers
