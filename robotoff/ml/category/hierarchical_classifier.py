import datetime
import json
import os
import pathlib
import re
from typing import List, Optional, Dict, Set

import networkx
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import (TfidfTransformer, CountVectorizer,
                                             strip_accents_ascii)

from sklearn.linear_model import LogisticRegression

from sklearn.model_selection import train_test_split
from sklearn.externals import joblib
from sklearn.pipeline import Pipeline

from sklearn_hierarchical_classification.classifier import HierarchicalClassifier
from sklearn_hierarchical_classification.constants import ROOT
from sklearn_hierarchical_classification.metrics import fill_ancestors

from robotoff import settings
from robotoff.products import ProductDataset
from robotoff.taxonomy import Taxonomy, TaxonomyType, \
    generate_category_hierarchy, get_taxonomy, TaxonomyNode
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


PUNCTUATION_REGEX = re.compile(r"""[:,;.&~"'|`_\\={}%()\[\]]+""")
DIGIT_REGEX = re.compile(r"[0-9]+")
MULTIPLE_SPACES_REGEX = re.compile(r" +")


class CategoryClassifier:
    TRANSFORMER_PATH = 'transformer.joblib'
    CLASSIFIER_PATH = 'clf.joblib'
    CATEGORY_TAXONOMY_PATH = 'category_taxonomy.json'

    def __init__(self, category_taxonomy: Taxonomy):
        self.category_taxonomy: Taxonomy = category_taxonomy
        self.categories_set: Set[str] = set(category_taxonomy.keys())
        self.categories: List[str] = sorted(self.categories_set)
        self.categories_to_index: Dict[str, int] = {cat: i for (i, cat) in
                                                    enumerate(self.categories)}
        self.transformer: Optional[ColumnTransformer] = None
        self.classifier: Optional[HierarchicalClassifier] = None

    def generate_training_df(self,
                             dataset: ProductDataset) -> pd.DataFrame:
        training_dataset_iter = (dataset.stream()
                                 .filter_by_country_tag('en:france')
                                 .filter_nonempty_text_field('product_name')
                                 .filter_nonempty_tag_field('categories_tags'))

        training_dataset = []

        processed = 0
        for product in training_dataset_iter:
            processed += 1
            transformed_product = self.transform_product(product,
                                                         add_category=True)

            if 'deepest_category' in transformed_product:
                training_dataset.append(transformed_product)

        logger.info("{} training samples discarded (category not in "
                    "taxonomy), {} remaining"
                    "".format(processed - len(training_dataset),
                              len(training_dataset)))
        return pd.DataFrame(training_dataset)

    def generate_prediction_df(self,
                               dataset: ProductDataset) -> pd.DataFrame:
        dataset_iter = (dataset.stream()
                               .filter_by_country_tag('en:france')
                               .filter_nonempty_text_field('product_name'))
        return pd.DataFrame((self.transform_product(p) for p in dataset_iter))

    def transform_product(self, product: Dict,
                          add_category: bool = False) -> Dict:
        item = {
            'barcode': product['code'],
            'ingredients_tags': product.get('ingredients_tags', []),
            'product_name': product.get('product_name', ''),
        }

        if add_category:
            categories_tags: List[str] = product['categories_tags']
            category_nodes: List[TaxonomyNode] = [
                self.category_taxonomy[c] for c in categories_tags
                if c in self.category_taxonomy
            ]

            deepest_categories: List[TaxonomyNode] = (self.category_taxonomy
                                                   .find_deepest_nodes(category_nodes))

            if deepest_categories is not None:
                deepest_category = deepest_categories[0].id
                item['deepest_category'] = deepest_category
                item['deepest_category_int'] = self.categories_to_index[deepest_category]

        return item

    def train(self, dataset: ProductDataset):
        category_hierarchy = generate_category_hierarchy(self.category_taxonomy,
                                                         self.categories_to_index,
                                                         ROOT)

        logger.info("Number of categories: {}".format(len(self.categories)))

        df = self.generate_training_df(dataset)
        train_df, test_df = train_test_split(df, random_state=42)
        y_train = train_df.deepest_category_int.values

        logger.info("Training started")
        self.classifier = self.create_classifier(category_hierarchy)
        self.transformer = self.create_transformer()

        X_train = self.transformer.fit_transform(train_df)
        self.classifier.fit(X_train, y_train)
        logger.info("End of training")

        return train_df, test_df

    def generate_insights(self, dataset: ProductDataset) -> List[JSONType]:
        self.raise_if_not_loaded()
        df = self.generate_prediction_df(dataset)
        y_pred = self.classifier.predict(self.transformer.transform(df))

        insights = []
        for i, row in enumerate(df.itertuples()):
            category = self.categories[y_pred]

            insights.append({
                'barcode': row.barcode,
                'category': category,
                'model': 'hierarchical_classifier',
            })

        return insights

    def raise_if_not_loaded(self):
        if self.classifier is None or self.transformer is None:
            raise RuntimeError("The model must be loaded or trained "
                               "before prediction")

    def predict(self, product: Dict):
        self.raise_if_not_loaded()

        transformed = {
            'product_name': product.get('product_name', ''),
            'ingredients_tags': product.get('ingredients_tags', []),
        }
        df = pd.DataFrame([transformed])
        y_pred = self.classifier.predict(self.transformer.transform(df))[0]
        return self.categories[y_pred]

    def save(self, output_dir: str) -> None:
        output_dir_path = pathlib.Path(output_dir)
        joblib.dump(self.transformer,
                    str(output_dir_path / self.TRANSFORMER_PATH))
        joblib.dump(self.classifier,
                    str(output_dir_path / self.CLASSIFIER_PATH))

        with open(str(output_dir_path / self.CATEGORY_TAXONOMY_PATH), 'w') as f:
            json.dump(self.category_taxonomy.to_dict(), f)

    @classmethod
    def load(cls, model_dir: str) -> 'CategoryClassifier':
        model_dir_path = pathlib.Path(model_dir)
        transformer = joblib.load(str(model_dir_path / cls.TRANSFORMER_PATH))
        classifier = joblib.load(str(model_dir_path / cls.CLASSIFIER_PATH))

        with open(str(model_dir_path /
                      cls.CATEGORY_TAXONOMY_PATH), 'r') as f:
            category_taxonomy_data = json.load(f)

        category_taxonomy = Taxonomy.from_dict(category_taxonomy_data)
        instance = cls(category_taxonomy)
        instance.transformer = transformer
        instance.classifier = classifier
        return instance

    @classmethod
    def create_classifier(cls, category_hierarchy):
        return HierarchicalClassifier(base_estimator=cls
                                      .create_base_classifier(),
                                      class_hierarchy=category_hierarchy,
                                      prediction_depth='nmlnp',
                                      algorithm='lcpn',
                                      stopping_criteria=0.5)

    @staticmethod
    def create_base_classifier():
        return Pipeline([
            ('tfidf', TfidfTransformer()),
            ('clf', LogisticRegression())])

    @staticmethod
    def create_transformer():
        return ColumnTransformer([
            ('ingredients_vectorizer',
             CountVectorizer(min_df=5,
                             preprocessor=ingredient_preprocess,
                             analyzer='word',
                             token_pattern=r"[a-zA-Z-:]+"),
             'ingredients_tags'),
            ('product_name_vectorizer',
             CountVectorizer(min_df=5,
                             preprocessor=preprocess_product_name),
             'product_name'),
        ])

    def evaluate(self, test_df: pd.DataFrame) -> JSONType:
        self.raise_if_not_loaded()
        y_test = test_df.deepest_category_int.values
        y_pred = self.classifier.predict(self.transformer.transform(test_df))
        return self._evaluate(self.classifier.graph_,
                              y_test, y_pred, len(self.categories))

    @staticmethod
    def _evaluate(category_graph: networkx.DiGraph,
                  y_true: np.ndarray,
                  y_pred: np.ndarray,
                  category_count: int) -> JSONType:
        y_true_matrix = np.zeros((y_true.shape[0], category_count))
        y_true_matrix[:, y_true] = 1

        y_pred_matrix = np.zeros((y_pred.shape[0], category_count))
        y_pred_matrix[:, y_pred] = 1

        return precision_recall_f1(y_true_matrix, y_pred_matrix, category_graph)


def precision_recall_f1(y_true: np.ndarray,
                        y_pred: np.ndarray,
                        class_hierarchy: networkx.DiGraph):
    y_true_ = fill_ancestors(y_true, graph=class_hierarchy)
    y_pred_ = fill_ancestors(y_pred, graph=class_hierarchy)

    ix = np.where((y_true_ != 0) & (y_pred_ != 0))

    true_positives = len(ix[0])
    all_results = np.count_nonzero(y_pred_)
    all_positives = np.count_nonzero(y_true_)

    h_precision = true_positives / all_results
    h_recall = true_positives / all_positives
    beta = 1
    h_f_1 = (1. + beta ** 2.) * h_precision * h_recall / (beta ** 2. * h_precision + h_recall)

    return {
        'h_precision': h_precision,
        'h_recall': h_recall,
        'h_f1': h_f_1,
    }


def ingredient_preprocess(ingredients_tags: List[str]) -> str:
    return ' '.join(ingredients_tags)


def preprocess_product_name(text):
    text = strip_accents_ascii(text)
    text = text.lower()
    text = PUNCTUATION_REGEX.sub(' ', text)
    text = DIGIT_REGEX.sub(' ', text)
    return MULTIPLE_SPACES_REGEX.sub(' ', text)


def train(model_output_dir: pathlib.Path, comment: Optional[str] = None):
    category_taxonomy: Taxonomy = get_taxonomy(TaxonomyType.category.name)
    category_classifier = CategoryClassifier(category_taxonomy)
    dataset: ProductDataset = ProductDataset.load()
    train_df, test_df = category_classifier.train(dataset)

    category_classifier.save(str(model_output_dir))
    test_metrics = category_classifier.evaluate(test_df)
    dataset_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(settings.JSONL_DATASET_PATH))

    meta = {
        'metrics': {
            'test': test_metrics,
        },
        'dataset_id': dataset_timestamp.date().isoformat(),
        'training_set_count': len(train_df),
        'test_set_count': len(test_df),
    }

    if comment:
        meta['comment'] = comment

    with open(str(model_output_dir / 'meta.json'), 'w') as f:
        json.dump(meta, f)
