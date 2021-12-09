import dataclasses
from typing import Optional


@dataclasses.dataclass
class TextPreprocessingConfig:
    lower: bool
    strip_accent: bool
    remove_punct: bool
    remove_digit: bool


@dataclasses.dataclass
class ModelConfig:
    product_name_lstm_recurrent_dropout: float
    product_name_lstm_dropout: float
    product_name_embedding_size: int
    product_name_lstm_units: int
    product_name_max_length: int
    hidden_dim: int
    hidden_dropout: float
    output_dim: Optional[int] = None
    product_name_voc_size: Optional[int] = None
    ingredient_voc_size: Optional[int] = None


@dataclasses.dataclass
class Config:
    product_name_preprocessing_config: TextPreprocessingConfig
    model_config: ModelConfig
    lang: str
    product_name_min_count: int
    category_min_count: int = 0
    ingredient_min_count: int = 0
