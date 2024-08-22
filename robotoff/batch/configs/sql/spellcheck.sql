SELECT code, ingredients_text AS text, product_name, (CAST(unknown_ingredients_n AS FLOAT) / CAST(ingredients_n AS FLOAT)) AS fraction
FROM read_ndjson('DATASET_PATH', ignore_errors=True)
WHERE ingredients_text NOT LIKE ''
AND fraction > 0 AND fraction <= 0.4
ORDER BY random() 
LIMIT 100
;