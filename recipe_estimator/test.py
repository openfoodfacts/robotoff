from ortools.linear_solver import pywraplp
import csv
from robotoff.mongo import MONGO_CLIENT_CACHE
import os

# Load Ciqual data
ciqual_ingredients = {}
filename = os.path.join(os.path.dirname(__file__), 'Ciqual.csv.0')
with open(filename, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        ciqual_ingredients[row['alim_code']] = row

#print(ciqual_ingredients['42501'])

# Load OFF Ciqual Nitrient mapping
nutrient_map = {}
filename = os.path.join(os.path.dirname(__file__), 'nutrient_map.csv')
with open(filename, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if (row['ciqual_id']):
            nutrient_map[row['off_id']] = row

#print(nutrient_map['pantothenic-acid'])
#print(len(nutrient_map))

def EstimateRecipe(query):
    mongo_client = MONGO_CLIENT_CACHE.get()
    collection = mongo_client.off.products
    product = collection.find_one(query)

    product_ingredients = product['ingredients']
    product_off_nutrients = product['nutriments']
    print(product['product_name'])
    #print(product_ingredients)
    print(product['ingredients_text'])
    print(product_off_nutrients)

    """Linear programming sample."""
    # Instantiate a Glop solver, naming it LinearExample.
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return

    product_nutrients = {}
    for off_nutrient_key in product_off_nutrients:
        if off_nutrient_key in nutrient_map:
            ciqual_nutrient = nutrient_map[off_nutrient_key]
            ciqual_unit = ciqual_nutrient['ciqual_unit']
            factor = 1.0
            if ciqual_unit == 'mg':
                factor = 1000.0
            elif ciqual_unit == 'µg':
                factor = 1000000.0
            product_nutrients[ciqual_nutrient['ciqual_id']] = product_off_nutrients[off_nutrient_key] * factor
    print(product_nutrients)

    ingredient_percentages = [solver.NumVar(0.0, solver.infinity(), ingredient['id']) for ingredient in product_ingredients]
    
    # This doesn't work
    #known = solver.Constraint(95.97,96.03,'known')
    #known.SetCoefficient(ingredient_percentages[0],1)
    
    # Add constraints so each ingredient can never be bigger than the one preceding it
    # TODO: Cope with hierarchies
    for i,ingredient in enumerate(product_ingredients[1:]):
        # Ingredient n - Ingredient (n+1) >= 0
        # But if ingredient n+1 contains water then it could be dried
        ciqual_ingredient = ciqual_ingredients[ingredient['ciqual_food_code']]
        # TODO: Put quantity parsing in a function
        water_content = float(ciqual_ingredient.get('Water (g/100g)','0').replace(',','.').replace('<','').replace('traces','0'))
        limit = solver.Constraint(0,solver.infinity(), ingredient['id'])
        limit.SetCoefficient(ingredient_percentages[i], 1)
        limit.SetCoefficient(ingredient_percentages[i+1], -0.01 * (100 - water_content))
    
    # And total of ingredients must add up to at least 100 (allow more than 100 to account for loss of water in processing)
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
    for nutrient in product_nutrients:
        for j, ingredient in enumerate(product_ingredients):
            # TODO: Ingredients with no ciqual code
            # TODO: Ciqual code not found
            ciqual_ingredient = ciqual_ingredients[ingredient['ciqual_food_code']]
            ciqual_nutrient = ciqual_ingredient[nutrient]
            if ciqual_nutrient == '-':
                print('Skippping ' + nutrient + ' as no known value for ' + ingredient['text'] + ' (' + ingredient['ciqual_food_code'] + ')')
                break
            # TODO: Figure out whether to do anything special with < ...
            ingredient['ciqual_nutrient_value'] = float(ciqual_nutrient.replace(',','.').replace('<','').replace('traces','0'))
        else:
            print(nutrient + ':')
            # This should only happen if the above loop completed without a break
            total_nutrient = product_nutrients[nutrient]
            # TODO: Decide weighting where product nutrient is zero
            nutrient_weighting = 1 / total_nutrient
            nutrient_distance = solver.NumVar(0, solver.infinity(), nutrient)

            negative_constraint = solver.Constraint(-nutrient_weighting * total_nutrient,solver.infinity())
            negative_constraint.SetCoefficient(nutrient_distance, 1)
            positive_constraint = solver.Constraint(nutrient_weighting * total_nutrient, solver.infinity())
            positive_constraint.SetCoefficient(nutrient_distance, 1)
            for j, ingredient in enumerate(product_ingredients):
                ciqual_nutrient_value = ingredient['ciqual_nutrient_value']
                print(' - ' + ingredient['text'] + ' (' + ingredient['ciqual_food_code'] + ') : ' + str(ciqual_nutrient_value))
                negative_constraint.SetCoefficient(ingredient_percentages[j], -nutrient_weighting * ciqual_nutrient_value / 100)
                positive_constraint.SetCoefficient(ingredient_percentages[j], nutrient_weighting * ciqual_nutrient_value / 100)

            objective.SetCoefficient(nutrient_distance, 1)

    objective.SetMinimization()

    status = solver.Solve()

    # Check that the problem has an optimal solution.
    if status == solver.OPTIMAL:
        print('An optimal solution was found in', solver.iterations(), 'iterations')
    else:
        print('The problem does not have an optimal solution!')
        if status == solver.FEASIBLE:
            print('A potentially suboptimal solution was found in', solver.iterations(), 'iterations')
        else:
            print('The solver could not solve the problem.')
            exit(1)

    for i, ingredient_percentage in enumerate(ingredient_percentages):
        print(ingredient_percentage.name(), ingredient_percentage.solution_value())

    # TODO: Print calculated nutrients
