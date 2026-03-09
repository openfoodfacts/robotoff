# Brand Prediction

Brand prediction identifies the brand name of a product from OCR text or logo detection.

Robotoff uses multiple data sources to detect brands:

1. **Curated brand list**: A manually curated list of common brands
2. **Brand taxonomy**: Brands extracted from the Open Food Facts [brand taxonomy](https://static.openfoodfacts.org/data/taxonomies/brands.full.json)
3. **Logo detection**: Google Cloud Vision logo annotations

## Data Sources

### Curated Brand List

A manually curated list of brand names stored in `OCR_BRANDS_PATH` (`brand.txt`). This list contains well-known brands that are frequently found on product packaging.

> This source is deprecated, and will be removed in favor of the more comprehensive taxonomy-based approach.

### Brand Taxonomy

Brands extracted from the Open Food Facts brand taxonomy. The taxonomy is processed to:

- Filter out numeric-only entries
- Apply a minimum product count threshold (configured via `BRAND_MATCHING_MIN_COUNT`)
- Apply a minimum name length filter (configured via `BRAND_MATCHING_MIN_LENGTH`)
- Exclude blacklisted brands

The processed taxonomy is stored in `OCR_TAXONOMY_BRANDS_PATH` (`brand_from_taxonomy.gz`).

### Logo Annotation

Google Cloud Vision logo detection results are matched against a mapping file (`OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH` - `brand_logo_annotation.txt`). The file uses `||` as separator:

```
logo_description||brand_tag
```

## Prediction Process

The brand prediction process (defined in `robotoff/prediction/ocr/brand.py`) works as follows:

1. **OCR text extraction**: Extract text from product images using OCR
2. **Keyword matching**: Use flashtext's `KeywordProcessor` to find brand mentions in the text
3. **Bounding box extraction**: When available, extract the bounding box coordinates for the matched brand text
4. **Prediction generation**: Create predictions with:
   - `value`: The matched brand name. Example: "Nestlé"
   - `value_tag`: A normalized tag (e.g., `en:nestle` for "Nestlé")
   - `predictor`: The data source used (`curated-list`, `taxonomy`, or `google-cloud-vision`)
   - `automatic_processing`: Whether the insight can be applied automatically

## Predictors

| Predictor | Source | Automatic Processing | Description |
|-----------|--------|---------------------|-------------|
| `curated-list` | Manually curated brand list | Yes | High-confidence brands from curated list |
| `taxonomy` | Open Food Facts taxonomy | No | Brands from the taxonomy (need validation) |
| `google-cloud-vision` | Logo detection | No | Brands detected via logo recognition |

## Validation

Brand predictions undergo validation before becoming insights.
These checks are only applied to `taxonomy` and `curated-list` predictors.

### Blacklist Check

Certain brands are blacklisted (stored in `OCR_TAXONOMY_BRANDS_BLACKLIST_PATH`) and excluded from automatic detection. This includes:

- Brands that are too generic
- Brands that cause frequent false positives

### Barcode Range Validation

Each brand is associated with a set of barcode prefixes they typically use. This is computed from existing product data and stored in `BRAND_PREFIX_PATH`. The validation:

1. Generates a barcode prefix (first 7 digits for EAN-13)
2. Checks if the (brand_tag, barcode_prefix) pair exists in the brand prefix dataset
3. Rejects predictions where the barcode is outside the expected range

This prevents incorrect brand assignments, for example assigning a chocolate brand to a dairy product.

## Insight Generation

The `BrandInsightImporter` class (`robotoff/insights/importer.py`) handles converting predictions to insights:

1. **Existing brand check**: If the product already has brands filled in, no new insights are created
2. **Validation**: Apply blacklist and barcode range checks for `taxonomy` and `curated-list` predictors
3. **Automatic processing**: Set based on the predictor type and data source

### Conflict Resolution

Insights conflict if they have the same `value_tag`. When conflicts occur, the system prioritizes:

1. Insights from the most recent source image
2. Insights with automatic processing enabled

## Data Files

| File | Path | Description |
|------|------|-------------|
| Brand list | `data/ocr/brand.txt` | Curated brand names |
| Taxonomy brands | `data/ocr/brand_from_taxonomy.gz` | Compressed taxonomy brands |
| Logo annotations | `data/ocr/brand_logo_annotation.txt` | Logo-to-brand mapping |
| Brand blacklist | `data/ocr/brand_taxonomy_blacklist.txt` | Blacklisted brands |
| Brand prefixes | `data/BrandPrefixes.json.gz` | Barcode prefix ranges |

## Configuration

Key settings in `robotoff/settings.py`:

- `BRAND_MATCHING_MIN_COUNT`: Minimum product count for taxonomy brands
- `BRAND_MATCHING_MIN_LENGTH`: Minimum brand name length
- `OCR_BRANDS_PATH`: Path to curated brand list
- `OCR_TAXONOMY_BRANDS_PATH`: Path to taxonomy brands
- `OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH`: Path to logo annotations
- `OCR_TAXONOMY_BRANDS_BLACKLIST_PATH`: Path to brand blacklist

## See Also

- Brand Insight Importer module (`robotoff.insights.importer`) - Insight import logic
- Brand Module (`robotoff.brands`) - Brand data management and barcode range validation
