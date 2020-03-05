if "fiber" or "fibre" in ocr:
  if product.fiber is empty:
    if product.states contains nutrition-facts-completed:
        create_insight(product.code, fiber_detected_while_no_fiber_stored)
