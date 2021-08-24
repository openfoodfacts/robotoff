from robotoff.utils.text import strip_accents_ascii


def normalize_emb_code(emb_code: str):
    emb_code = (
        emb_code.strip().lower().replace(" ", "").replace("-", "").replace(".", "")
    )

    emb_code = strip_accents_ascii(emb_code)

    if emb_code.endswith("ce"):
        emb_code = emb_code[:-2] + "ec"

    return emb_code
