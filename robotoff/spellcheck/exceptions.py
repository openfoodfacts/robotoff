class SpellcheckerException(Exception):
    pass


class TokenLengthMismatchException(SpellcheckerException):
    pass


class PipelineSpellcheckerException(SpellcheckerException):
    pass


class LanguageNotAllowedException(SpellcheckerException):
    pass
