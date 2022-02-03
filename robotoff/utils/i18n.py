import gettext
from typing import Dict, Optional, Set

from robotoff import settings


class TranslationStore:
    SUPPORTED_LANGUAGES: Set[str] = {
        "fr",
        "es",
        "it",
        "de",
    }

    def __init__(self):
        self.translations: Dict[str, gettext.NullTranslations] = {}

    def load(self):
        for lang in self.SUPPORTED_LANGUAGES:
            t = gettext.translation(
                "robotoff", str(settings.I18N_DIR), languages=[lang]
            )
            if t is not None:
                self.translations[lang] = t

    def get(self, lang: str) -> Optional[gettext.NullTranslations]:
        return self.translations.get(lang)

    def gettext(self, lang: str, message: str) -> str:
        translation = self.translations.get(lang)

        if translation is None:
            return message

        return translation.gettext(message)
