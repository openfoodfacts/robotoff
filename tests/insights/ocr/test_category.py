from typing import List
import pytest
from robotoff.insights.ocr.category import find_category


@pytest.mark.parametrize(
    "text,data",
    [
        ("sirop renergie des saveu au coeur enthe laciale ", ["sweetened beverages"]),
        ("champignons de paris en conserve", ["vegetables"]),
        ("pate de dattes dalgerie elbaraka tolga eldaraka", ["fruits"]),
        ("our sucre pour barbe a papa parfum framboise msation deshydratee aromatisee et coloree ants sucre dextrose ardme gluten coloant antagglomerant dioxy e de silicium inanel traces de ouf sofe aat fruits a coque g pour g de produit deshydrate o e kcal naiut t etique kj bupds s satures e suktes asg o g ref pu lngrang ne s", ["sweets"]),
        ("valeurs typical nutrition valuel voedi matieres dont acides gras satureslwaarvan g of which saturatesdavon verzadigde vetzuren gesattigte g drate kohlenhydrate dont sucres waarvan which sugars davon zucker g proteines eiwittenproteineiweib selzoutsaltsalz", ["fats"]),
        ("cal ou cons a conse endroll conserva conv ia prer des atis des an emboutailide par aquamar a spu bad finement", ["waters and flavored waters"]),
        ("lectlon raoul mayonnaise a lluile de tournesol rendezvous des gourme xma chausjules cesar beauc poids net gr ou geysa valeurs n", ["dressings and sauces"]),
        ("francine forma kg familia nsatx farine de bes fluide originale garantie antigrumeaulx t", ['cereals']),
        ("pd e olives vertes denoyautes poids ne egouite g produit du maroc", ["salty and fatty products"]),
        ("fabrique en france inopho sauce tomato ketchup ecesar ous des gou sucreoigr entstomate valeure nuitionnelles pour ooeersie a x kal", ["dressings and sauces"]),
        ("nestle m e n i e r p a t i s s i e r on dessert de o kits pour petits patissiers a gagner", ['chocolate products']),
        ("ngredientsfarine de ble graines de tournesol farine de seigle raines de lin brun gluten de ble levain de ble deshydrate et ersactive emulsifiant ee dextrose malt dorge agentde traitement de la farine e enzyme cereales presence eventuelle de soja de lait doeuf de graines de sesameet de fruits a coque", ['bread']),
        ('tion raou jus de fruits pur jus pomme trouble abore avecdes fruits fras gey e rendezvous des gourm clecti', ['fruit juices']),
        ('ker chant local decoupes de poulet conditionne par ldc bretagne lanfains rais classe a origine france prodtre et c offre speciale ne eleve prepare local dans notre region cuisdej plt sat kerchant fx origine france volaille francaise prixkg paids net prin apayer kg to a consommer jusqu au r conserver entre d c et c expedie le loc bretagne lanfains autrit pens', ['meat']),
        ('lagrange france sucre pour barbe a papa ramboise pour la boite barbes a papa de g', ['sweets']),
        ('valeurs nutritionnelles moyennes pour gde gde corn flakes corn ml de lait flakes corn flakes demiecreme valeur kcal kcal koal energetique kj a la proteines glucides totaux g g ont sucres totaux g ont amidon g g lipides g g dont satures g g fibres alimentaires g g sodium g g g equivalent sel g g en vitamines en en des aur des aur des aur b mg b r mg mg b mg b acide folique hg b ug mineraux csla mg fer ja ajr apports journaliers recommandes', ['breakfast cereals'])
         ]
)

def test_find_category(text: str, data: List[str]):
    insights = find_category(text)
    detected_data = set(i.data['proba'] for i in insights)
    assert detected_data == set(data)


