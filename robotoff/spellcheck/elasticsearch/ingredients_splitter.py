import re

from robotoff.spellcheck.data_utils import Offset, Ingredients


class IngredientsSplitter:

    SPLITTER_CHAR = {"(", ")", ",", ";", "[", "]", "-", "{", "}"}

    # Food additives (EXXX) may be mistaken from one another, because of their edit distance proximity
    BLACKLIST_RE = re.compile(r"(?:\d+(?:[,.]\d+)?\s*%)|(?:[0-9])(?![\w-])")
    PUNCTUATION_BLACKLIST_RE = re.compile(r"[_•:]")
    E_BLACKLIST_RE = re.compile(r"(?<!\w)(?:E ?\d{3,5}[a-z]*)")

    def __init__(self, remove_blacklist: bool = True):
        self.remove_blacklist = remove_blacklist

    def split(self, text: str) -> Ingredients:
        if self.remove_blacklist:
            normalized_text = self.process_remove_blacklist(text)
        else:
            normalized_text = text

        offsets = []
        chars = []
        start_idx = 0

        for idx, char in enumerate(normalized_text):
            if char in self.SPLITTER_CHAR:
                offsets.append(Offset(start_idx, idx))
                start_idx = idx + 1
                chars.append(" ")
            else:
                chars.append(char)

        if start_idx != len(normalized_text):
            offsets.append(Offset(start_idx, len(normalized_text)))

        normalized_text = "".join(chars)
        return Ingredients(text, normalized_text, offsets)

    @classmethod
    def process_remove_blacklist(cls, text: str) -> str:
        text_without_blacklist = text

        for regex in (
            cls.E_BLACKLIST_RE,
            cls.BLACKLIST_RE,
            cls.PUNCTUATION_BLACKLIST_RE,
        ):
            while True:
                try:
                    match = next(regex.finditer(text_without_blacklist))
                except StopIteration:
                    break
                if match:
                    start = match.start()
                    end = match.end()
                    text_without_blacklist = (
                        text_without_blacklist[:start]
                        + " " * (end - start)
                        + text_without_blacklist[end:]
                    )
                else:
                    break

        return text_without_blacklist
