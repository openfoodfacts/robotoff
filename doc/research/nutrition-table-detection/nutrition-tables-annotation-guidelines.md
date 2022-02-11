# Nutrition Table Annotation Guidelines

Guidelines on what and how to label.

Adapted from <http://host.robots.ox.ac.uk/pascal/VOC/voc2011/guidelines.html>

## What to label


All objects of the defined categories, unless:

- you are unsure what the object is.
- the object is very small (at your discretion).
- less than 10-20% of the object is visible, such that you cannot be sure what class it is.

### Bounding box
Mark the bounding box of the visible area of the object (not the estimated total extent of the object).
Bounding box should contain all visible pixels. The bounding box should enclose the object as tight as possible.

### Clothing/mud/ snow etc.
If an object is ‘occluded’ by a close-fitting occluder e.g. clothing, mud, snow etc., then the occluder should be treated as part of the object.

### Transparency
Do label objects visible through glass, but treat reflections on the glass as occlusion.

### Mirrors
Do label objects in mirrors.

### Pictures
Label objects in pictures/posters/signs only if they are photorealistic but not if cartoons, symbols etc.


## Guidelines on categorization

*nutrition-table*: a _table_ containing nutrition facts.
*nutrition-table-text*: variant where the nutrition facts are not displayed in a table. Ex: `Nutritional facts for 100g: Energy - 252 kJ, fat: 12g,...`.
*nutrition-table-small-energy*: symbol often found on the front image of the product, indicating the kJ/kcal of a portion/100g of the product. The bounding box should only enclose the symbol, and not additional texts around it. Do not use this label if other nutritional information are layed out next to the object, see nutrition-table-small.
*nutrition-table-small*: pack of symbols often found on the front image of the product, indicating the nutrition facts.

If there are several nutrition-table or nutrition-table-text on the image (often found on multilingual products), label each object.
