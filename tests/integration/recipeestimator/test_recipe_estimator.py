from recipe_estimator.test import EstimateRecipe

def test_recipe_estimator():
    EstimateRecipe({"ingredients_without_ciqual_codes_n": 0,"ingredients_n":{"$gt": 1}})
