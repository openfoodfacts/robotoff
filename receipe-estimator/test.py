from ortools.linear_solver import pywraplp

def LinearProgrammingExample():
    """Linear programming sample."""
    # Instantiate a Glop solver, naming it LinearExample.
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return

    ciqual_ingredients = {
        'en:Rehydrated Textured _Soya_ Protein': {
            'starch': 0.35,
            'salt': 0.013,
            'proteins': 18.6,
            'fiber': 5.61,
            'fat': 2.9,
            'sugars': 3.65,
            'carbohydrates': 7.03,
        },
        'en:rapeseed-oil': {
            'starch': 0,
            'salt': 0,
            'proteins': 0,
            'fiber': 0,
            'fat': 100,
            'sugars': 0,
            'carbohydrates': 0,
        },
        'en:yeast-extract': {
            'starch': 0,
            'salt': 0,
            'proteins': 32,
            'fiber': 0,
            'fat': 0,
            'sugars': 0,
            'carbohydrates': 53,
        },
        'en:barley-malt-extract': {
            'starch': 0,
            'salt': 0,
            'proteins': 4,
            'fiber': 0,
            'fat': 0,
            'sugars': 0,
            'carbohydrates': 76,
        },
        'en:onion-powder': {
            'starch': 0,
            'salt': 0.053,
            'proteins': 8.95,
            'fiber': 9.2,
            'fat': 0.46,
            'sugars': 37.4,
            'carbohydrates': 75,
        },
        'en:garlic-powder': {
            'starch': 0,
            'salt': 0.11,
            'proteins': 16.7,
            'fiber': 9.45,
            'fat': 0.77,
            'sugars': 2.43,
            'carbohydrates': 62.8,
        },
        'en:corn-flour': {
            'starch': 0,
            'salt': 0.0025,
            'proteins': 6.23,
            'fiber': 2.55,
            'fat': 2.1,
            'sugars': 0.64,
            'carbohydrates': 78.1,
        },
        'en:dextrose': {
            'starch': 0,
            'salt': 0,
            'proteins': 0,
            'fiber': 0,
            'fat': 0,
            'sugars': 100,
            'carbohydrates': 100,
        },
        'en:salt': {
            'starch': 0,
            'salt': 100,
            'proteins': 0,
            'fiber': 0,
            'fat': 0,
            'sugars': 0,
            'carbohydrates': 0,
        },
        'en:white-pepper': {
            'starch': 0,
            'salt': 0.013,
            'proteins': 11.4,
            'fiber': 26.2,
            'fat': 2.11,
            'sugars': 0,
            'carbohydrates': 48.3,
        },
        'en:protein': {
            'starch': 0,
            'salt': 0,
            'proteins': 100,
            'fiber': 0,
            'fat': 0,
            'sugars': 0,
            'carbohydrates': 0,
        },
    }

    """
    # Simple test
    product_nutrients = {
        'proteins': 20,
        'fat': 10,
        'carbohydrates': 70,
    }
    product_ingredients = [
        {
            'id': 'en:dextrose'
        },
        {
            'id': 'en:protein'
        },
        {
            'id': 'en:rapeseed-oil'
        },
    ]

    """
    # Vege Mince
    product_nutrients = {
        'starch': 5.1,
        'salt': 0.51,
        'proteins': 20.1,
        'fiber': 5.1,
        'fat': 2.6,
        'sugars': 1.6,
        'carbohydrates': 6.7,
    }
    product_ingredients = [
        {
            'id': 'en:Rehydrated Textured _Soya_ Protein'
        },
        {
            'id': 'en:rapeseed-oil'
        },
        {
            'id': 'en:yeast-extract'
        },
        {
            'id': 'en:barley-malt-extract'
        },
        {
            'id': 'en:onion-powder'
        },
        {
            'id': 'en:garlic-powder'
        },
        {
            'id': 'en:corn-flour'
        },
        {
            'id': 'en:dextrose'
        },
        {
            'id': 'en:salt'
        },
        {
            'id': 'en:white-pepper'
        },
    ]
    

    ingredient_percentages = [solver.NumVar(0.0, solver.infinity(), ingredient['id']) for ingredient in product_ingredients]
    
    # This doesn't work
    #known = solver.Constraint(95.97,96.03,'known')
    #known.SetCoefficient(ingredient_percentages[0],1)
    
    # Use 1% tolerance for now
    tolerance = 0.00

    # Add constraints so each ingredient can never be bigger than the one preceding it
    for i,ingredient in enumerate(product_ingredients[1:]):
        limit = solver.Constraint(0,solver.infinity(), ingredient['id'])
        limit.SetCoefficient(ingredient_percentages[i], 1)
        limit.SetCoefficient(ingredient_percentages[i+1], -1)
    
    # And total of ingredients must add up to at least 100
    total_ingredients = solver.Constraint(100,solver.infinity(), 'sum')
    for ingredient_percentage in ingredient_percentages:
        total_ingredients.SetCoefficient(ingredient_percentage, 1)

    """
    # Min / max approach. Doesn't seem to work for real example    
    # Create the constraints for the sum of nutrients from each ingredient
    for i, nutrient in enumerate(product_nutrients):
        nutrient_sum = solver.Constraint(product_nutrients[nutrient] * (1 - tolerance),product_nutrients[nutrient] * (1 + tolerance), nutrient)
        for j, ingredient in enumerate(product_ingredients):
            ciqual_ingredient = ciqual_ingredients[ingredient['id']]
            nutrient_sum.SetCoefficient(ingredient_percentages[j], ciqual_ingredient[nutrient] / 100)

    objective = solver.Objective()
    objective.SetCoefficient(ingredient_percentages[0], 1)
    objective.SetMaximization()
    """

    objective = solver.Objective()
    for i, nutrient in enumerate(product_nutrients):
        total_nutrient = product_nutrients[nutrient]
        nutrient_weighting = 1 / total_nutrient
        nutrient_distance = solver.NumVar(0, solver.infinity(), nutrient)

        negative_constraint = solver.Constraint(-nutrient_weighting * total_nutrient,solver.infinity())
        negative_constraint.SetCoefficient(nutrient_distance, 1)
        positive_constraint = solver.Constraint(nutrient_weighting * total_nutrient, solver.infinity())
        positive_constraint.SetCoefficient(nutrient_distance, 1)
        for j, ingredient in enumerate(product_ingredients):
            ciqual_ingredient = ciqual_ingredients[ingredient['id']]
            negative_constraint.SetCoefficient(ingredient_percentages[j], -nutrient_weighting * ciqual_ingredient[nutrient] / 100)
            positive_constraint.SetCoefficient(ingredient_percentages[j], nutrient_weighting * ciqual_ingredient[nutrient] / 100)

        objective.SetCoefficient(nutrient_distance, 1)

    objective.SetMinimization()

    status = solver.Solve()

    # Check that the problem has an optimal solution.
    if status == solver.OPTIMAL:
        print('An optional solution was found in', solver.iterations(), 'iterations')
    else:
        print('The problem does not have an optimal solution!')
        if status == solver.FEASIBLE:
            print('A potentially suboptimal solution was found in', solver.iterations(), 'iterations')
        else:
            print('The solver could not solve the problem.')
            exit(1)

    for i, ingredient_percentage in enumerate(ingredient_percentages):
        print(ingredient_percentage.name(), ingredient_percentage.solution_value())


LinearProgrammingExample()
