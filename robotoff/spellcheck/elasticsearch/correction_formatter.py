from typing import Dict, List

from robotoff.spellcheck.exceptions import TokenLengthMismatchException
from robotoff.spellcheck.items import AtomicCorrection, Offset


class CorrectionFormatter:
    def format(
        self,
        original_tokens: List[Dict],
        suggestion_tokens: List[Dict],
        offset: Offset,
        score: int,
    ) -> List[AtomicCorrection]:
        if len(original_tokens) != len(suggestion_tokens):
            raise TokenLengthMismatchException()

        atomic_corrections = []
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

                atomic_corrections.append(
                    AtomicCorrection(
                        original=original_token_str,
                        correction=token_str,
                        offset=Offset(
                            offset.start + original_token["start_offset"],
                            offset.start + original_token["end_offset"],
                        ),
                        score=score,
                    )
                )
        return atomic_corrections
