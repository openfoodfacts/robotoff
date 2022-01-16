import pytest

from robotoff.insights import InsightType
from robotoff.prediction.ocr.category import predict_ocr_categories


@pytest.mark.parametrize(
    "text,predicted_category,confidence",
    [
        (
            "sirop renergie des saveu au coeur enthe laciale ",
            "sweetened beverages",
            0.0726,
        ),
        ("champignons de paris en conserve", "vegetables", 0.1658,),
        ("pate de dattes dalgerie elbaraka tolga eldaraka", "fruits", 0.0998,),
        (
            "our sucre pour barbe a papa parfum framboise msation deshydratee aromatisee et coloree ants sucre dextrose ardme gluten coloant antagglomerant dioxy e de silicium inanel traces de ouf sofe aat fruits a coque g pour g de produit deshydrate o e kcal naiut t etique kj bupds s satures e suktes asg o g ref pu lngrang ne s",
            "sweets",
            0.0952,
        ),
        (
            "valeurs typical nutrition valuel voedi matieres dont acides gras satureslwaarvan g of which saturatesdavon verzadigde vetzuren gesattigte g drate kohlenhydrate dont sucres waarvan which sugars davon zucker g proteines eiwittenproteineiweib selzoutsaltsalz",
            "fats",
            0.0722,
        ),
        (
            "cal ou cons a conse endroll conserva conv ia prer des atis des an emboutailide par aquamar a spu bad finement",
            "waters and flavored waters",
            0.0708,
        ),
        (
            "lectlon raoul mayonnaise a lluile de tournesol rendezvous des gourme xma chausjules cesar beauc poids net gr ou geysa valeurs n",
            "dressings and sauces",
            0.0862,
        ),
        (
            "francine forma kg familia nsatx farine de bes fluide originale garantie antigrumeaulx t",
            "cereals",
            0.0738,
        ),
        (
            "pd e olives vertes denoyautes poids ne egouite g produit du maroc",
            "salty and fatty products",
            0.1243,
        ),
        (
            "fabrique en france inopho sauce tomato ketchup ecesar ous des gou sucreoigr entstomate valeure nuitionnelles pour ooeersie a x kal",
            "dressings and sauces",
            0.3151,
        ),
        (
            "nestle m e n i e r p a t i s s i e r on dessert de o kits pour petits patissiers a gagner",
            "chocolate products",
            0.0853,
        ),
        (
            "ngredientsfarine de ble graines de tournesol farine de seigle raines de lin brun gluten de ble levain de ble deshydrate et ersactive emulsifiant ee dextrose malt dorge agentde traitement de la farine e enzyme cereales presence eventuelle de soja de lait doeuf de graines de sesameet de fruits a coque",
            "bread",
            0.093,
        ),
        (
            "tion raou jus de fruits pur jus pomme trouble abore avecdes fruits fras gey e rendezvous des gourm clecti",
            "fruit juices",
            0.1102,
        ),
        (
            "ker chant local decoupes de poulet conditionne par ldc bretagne lanfains rais classe a origine france prodtre et c offre speciale ne eleve prepare local dans notre region cuisdej plt sat kerchant fx origine france volaille francaise prixkg paids net prin apayer kg to a consommer jusqu au r conserver entre d c et c expedie le loc bretagne lanfains autrit pens",
            "meat",
            0.1285,
        ),
        (
            "lagrange france sucre pour barbe a papa ramboise pour la boite barbes a papa de g",
            "sweets",
            0.1421,
        ),
        (
            "valeurs nutritionnelles moyennes pour gde gde corn flakes corn ml de lait flakes corn flakes demiecreme valeur kcal kcal koal energetique kj a la proteines glucides totaux g g ont sucres totaux g ont amidon g g lipides g g dont satures g g fibres alimentaires g g sodium g g g equivalent sel g g en vitamines en en des aur des aur des aur b mg b r mg mg b mg b acide folique hg b ug mineraux csla mg fer ja ajr apports journaliers recommandes",
            "breakfast cereals",
            0.1845,
        ),
    ],
)
def test_predict_ocr_categories(
    text: str, predicted_category: str, confidence: float
) -> None:
    insights = predict_ocr_categories(text)

    # No hesitation in the examples
    assert len(insights) == 1
    insight = insights[0]

    # Predicted a category
    assert insight.type == InsightType.category

    # Assert predictions are accurate
    assert insight.predictor == "ridge_model-ml"
    assert insight.value_tag == predicted_category
    assert insight.data == {"confidence": confidence}
