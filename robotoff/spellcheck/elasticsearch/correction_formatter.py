from typing import List, Dict

from robotoff.spellcheck.data_utils import (
    TermCorrection,
    Correction,
    Offset,
    TokenLengthMismatchException,
)


class CorrectionFormatter:
    def format(
        self,
        original_tokens: List[Dict],
        suggestion_tokens: List[Dict],
        offset: int,
        score: int,
    ) -> Correction:
        if len(original_tokens) != len(suggestion_tokens):
            raise TokenLengthMismatchException()

        correction = Correction(term_corrections=[], score=score)

        for original_token, suggestion_token in zip(original_tokens, suggestion_tokens):
            original_token_str = original_token["token"]
            suggestion_token_str = suggestion_token["token"]

            if original_token_str.lower() != suggestion_token_str:
                if original_token_str.isupper():
                    token_str = suggestion_token_str.upper()
                elif original_token_str.istitle():
                    token_str = suggestion_token_str.capitalize()
                else:
                    token_str = suggestion_token_str

                correction.add_term(
                    original=original_token_str,
                    correction=token_str,
                    offset=Offset(
                        offset.start + original_token["start_offset"],
                        offset.start + original_token["end_offset"],
                    ),
                )

        return correction
