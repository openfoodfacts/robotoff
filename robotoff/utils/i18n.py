import gettext
from typing import Optional

from robotoff import settings


class TranslationStore:
    def __init__(self):
        self.translations: dict[str, gettext.NullTranslations] = {}

    def load(self):
        for lang_dir in settings.I18N_DIR.glob("*"):
            if not lang_dir.is_dir():
                continue

            lang = lang_dir.name
            t = gettext.translation(
                "robotoff", str(settings.I18N_DIR), languages=[lang]
            )
            self.translations[lang] = t

    def get(self, lang: str) -> Optional[gettext.NullTranslations]:
        return self.translations.get(lang)

    def gettext(self, lang: str, message: str) -> str:
        translation = self.translations.get(lang)

        if translation is None:
            return message

        return translation.gettext(message)
