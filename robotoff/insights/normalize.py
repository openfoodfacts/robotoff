from robotoff.utils.text import strip_accents_v1


def normalize_emb_code(emb_code: str):
    """replacing space, hyphen, and dot
    so that "fr 40.261.001 ce" changes to "fr40261001ce'"
    """

    emb_code = (
        emb_code.strip().lower().replace(" ", "").replace("-", "").replace(".", "")
    )

    emb_code = strip_accents_v1(emb_code)

    """if the code ends with "ce" replace it with "ec"
    here "fr40261001ce" becomes "fr40261001ec"
    """

    if emb_code.endswith("ce"):
        emb_code = emb_code[:-2] + "ec"

    return emb_code
