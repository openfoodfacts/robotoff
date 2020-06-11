class SpellcheckerException(Exception):
    pass


class TokenLengthMismatchException(SpellcheckerException):
    pass


class LanguageNotAllowedException(SpellcheckerException):
    pass
