# Image Orientation Detection

The image orientation feature automatically detects and corrects incorrectly oriented selected product images (front, ingredients, nutrition, and packaging) using text orientation analysis.

## How it works

1. **Detection**: Google Cloud Vision OCR analyzes text orientation in uploaded product images.

2. **Insight Generation**: When text is detected with non-upright orientation (≥95% confidence) in a selected image, an `image_orientation` insight is generated.

3. **Rotation Application**: When the insight is accepted, or if the insight was marked as automatically processable, the selected image is rotated to the correct orientation via the Product Opener API, while preserving any crop bounding boxes.

## Technical Implementation

### Detection Algorithm

The detection uses OCR orientation metadata to identify incorrectly oriented images. The algorithm:

1. Counts text blocks in each orientation (up, left, right, down).
2. Calculates the confidence as the percentage of text in the dominant non-upright orientation.
3. Determines the required rotation angle (0, 90, 180, or 270 degrees).

Only images with ≥95% confidence in a consistent non-upright orientation generate insights. If more than 10 words are detected on the image, **we mark the insight as automatically processable**, which means the rotation will be automatically applied without user confirmation.
This 10-word threshold is a heuristic is based on manual inspection of the generated insights: almost all false positives were generated from images with less than 10 words.

### Importer

The `ImageOrientationImporter` class:

- Validates that images are selected (front, nutrition, ingredients, packaging).
- Ensures the confidence threshold (≥95%) is met.
- Checks that the current rotation angle differs from the predicted one.
- Creates insights with appropriate rotation information.

### Annotator

The `ImageOrientationAnnotator` class:

- Processes the rotation annotation.
- Transforms any existing crop bounding boxes to account for the rotation.
- Calls the Product Opener API to apply the rotation.

### Bounding Box Transformation

When rotating images with existing crop bounding boxes, the coordinates are transformed using matrix rotation to maintain the correct cropping area in the new orientation:

1. The original coordinates are converted to a standard format.
2. A rotation transformation is applied based on the rotation angle.
3. The transformed coordinates are adjusted to fit within image boundaries.

## Example

For a sideways nutrition image:

1. OCR analysis detects text oriented to the right.
2. An insight with `rotation: 270` is generated.
3. When applied, the image is rotated 270° counter-clockwise.
4. Any crop bounding box is automatically transformed to match the new orientation.

## Limitations

- Requires clear, readable text for reliable orientation detection.
- Images with mixed text orientations may not reach the confidence threshold.
- Rotation applies to the entire selected image, affecting all cropping areas.
