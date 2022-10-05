from robotoff.utils.i18n import TranslationStore


def test_load_store():
    store = TranslationStore()
    store.load()
