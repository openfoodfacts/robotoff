from sklearn.base import TransformerMixin, BaseEstimator
from spellchecker import SpellChecker
import re
import string
import unicodedata
import pandas as pd
import nltk

# Transformer with SpellCheck
class Cleaner():


    def __init__(self):
        return None

    def remove_punc(text):
        """Expects a string; Returns a string without punctuation"""
        for punctuation in string.punctuation:
            text = text.replace(punctuation, ' ')
            text = re.sub(" +", " ", text)
        return text

    def remove_specialchar(text):
        return ''.join(word for word in text if word.isalpha() or word == ' ')

    def remove_nonalpha(text):
        """Expects a string; Returns a string without non alphanumeric characters"""
        text = ''.join(c for c in text if c.isalpha() or c == ' ')
        return re.sub(" +", " ", text)

    def corrected(text):
        """Expects a string in French; Returns a string without spelling mistakes"""
        # Init SpellChecker
        spell = SpellChecker(language='fr', distance=1, case_sensitive=False)
        # Get misspellings and corrections
        text_splitted = text.split()
        misspelled = spell.unknown(text_splitted)
        correction = {word:spell.correction(word) for word in misspelled}

        # Replace misspellings in text
        for k,v in correction.items():
            text = text.replace(k,v)
        return text

    def remove_accents(text):
        """Expects a string; Returns a string without accentuated characters"""
        return ''.join(c for c in unicodedata.normalize('NFKD', text)
                        if unicodedata.category(c) != 'Mn')

    @staticmethod
    def clean_ocr_text(text, spellcheck=None):
        """Expects a string; Returns a string without punctuation, non-alphanum characters, spelling mistakes"""
        #lower and \n remover
        text = text.lower().replace('\n',' ')

        #choice to spellcheck or not
        if spellcheck:
            clean_funcs = [Cleaner.remove_punc, Cleaner.remove_nonalpha, Cleaner.corrected, Cleaner.remove_accents]
        else:
            clean_funcs = [Cleaner.remove_punc, Cleaner.remove_nonalpha, Cleaner.remove_accents]

        for func in clean_funcs:
            text = func(text)
        return text.strip(" ")

#if __name__ == '__main__':

    #cleaner = Cleaner()
    #print(cleaner.clean_ocr_text(text="oeuf, viande", spellcheck=None))


