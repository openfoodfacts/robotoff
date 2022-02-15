import datetime
import uuid
from typing import Any, Dict, List, Optional

import pytest

from robotoff.insights.dataclass import InsightType
from robotoff.insights.importer import (
    BrandInsightImporter,
    CategoryImporter,
    ExpirationDateImporter,
    InsightImporter,
    LabelInsightImporter,
    PackagerCodeInsightImporter,
    PackagingInsightImporter,
    ProductWeightImporter,
    StoreInsightImporter,
    import_insights_for_products,
    is_recent_image,
    is_selected_image,
    is_trustworthy_insight_image,
    is_valid_insight_image,
    sort_predictions,
)
from robotoff.models import ProductInsight
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
from robotoff.products import Product

DEFAULT_BARCODE = "3760094310634"
DEFAULT_SERVER_DOMAIN = "api.openfoodfacts.org"
DEFAULT_UPLOADED_T = "1644332825"


@pytest.mark.parametrize(
    "images,image_id,max_timedelta,expected",
    [
        (
            {"1": {"uploaded_t": DEFAULT_UPLOADED_T}},
            "1",
            datetime.timedelta(seconds=10),
            True,
        ),
        (
            {
                "1": {"uploaded_t": DEFAULT_UPLOADED_T},
                "2": {"uploaded_t": str(int(DEFAULT_UPLOADED_T) + 9)},
            },
            "1",
            datetime.timedelta(seconds=10),
            True,
        ),
        (
            {
                "1": {"uploaded_t": DEFAULT_UPLOADED_T},
                "2": {"uploaded_t": str(int(DEFAULT_UPLOADED_T) + 11)},
            },
            "1",
            datetime.timedelta(seconds=10),
            False,
        ),
    ],
)
def test_is_recent_image(images, image_id, max_timedelta, expected):
    assert is_recent_image(images, image_id, max_timedelta) is expected


@pytest.mark.parametrize(
    "images,image_id,expected",
    [
        (
            {"1": {}, "2": {}, "front_fr": {"imgid": "2"}},
            "1",
            False,
        ),
        (
            {"1": {}, "2": {}, "ingredients_fr": {"imgid": "1"}},
            "1",
            True,
        ),
    ],
)
def test_is_selected_image(images, image_id, expected):
    assert is_selected_image(images, image_id) is expected


@pytest.mark.parametrize(
    "images,image_id,max_timedelta,expected",
    [
        (
            {"1": {"uploaded_t": DEFAULT_UPLOADED_T}},
            "1",
            datetime.timedelta(seconds=10),
            True,
        ),
        (
            {
                "1": {"uploaded_t": DEFAULT_UPLOADED_T},
                "2": {"uploaded_t": str(int(DEFAULT_UPLOADED_T) + 9)},
            },
            "1",
            datetime.timedelta(seconds=10),
            True,
        ),
        (
            {
                "1": {"uploaded_t": DEFAULT_UPLOADED_T},
                "2": {"uploaded_t": str(int(DEFAULT_UPLOADED_T) + 11)},
            },
            "1",
            datetime.timedelta(seconds=10),
            False,
        ),
        (
            {
                "1": {"uploaded_t": DEFAULT_UPLOADED_T},
                "2": {"uploaded_t": DEFAULT_UPLOADED_T},
                "ingredients_fr": {"imgid": "1"},
            },
            "1",
            datetime.timedelta(seconds=10),
            True,
        ),
        (
            {
                "2": {"uploaded_t": DEFAULT_UPLOADED_T},
            },
            "1",
            datetime.timedelta(seconds=10),
            False,
        ),
        (
            {
                "1": {"uploaded_t": DEFAULT_UPLOADED_T},
            },
            "front_fr",
            datetime.timedelta(seconds=10),
            False,
        ),
    ],
)
def test_is_trustworthy_insight_image(images, image_id, max_timedelta, expected):
    assert is_trustworthy_insight_image(images, image_id, max_timedelta) is expected


@pytest.mark.parametrize(
    "images,image_id,expected",
    [
        (
            {"1": {}, "2": {}},
            "1",
            True,
        ),
        (
            {"2": {}},
            "1",
            False,
        ),
        (
            {"1": {}, "front_fr": {}},
            "front_fr",
            False,
        ),
    ],
)
def test_is_valid_insight_image(images, image_id, expected):
    assert is_valid_insight_image(images, image_id) is expected


@pytest.mark.parametrize(
    "predictions,order",
    [
        (
            [
                Prediction(
                    PredictionType.category,
                    data={"priority": 2},
                    source_image="/123/fr_front.jpg",
                ),
                Prediction(
                    PredictionType.category, data={"priority": 3}, source_image=None
                ),
                Prediction(
                    PredictionType.category,
                    data={"priority": 2},
                    source_image="/123/3.jpg",
                ),
                Prediction(
                    PredictionType.category, data={"priority": 1}, source_image=None
                ),
                Prediction(
                    PredictionType.category,
                    data={"priority": 4},
                    source_image="/123/1.jpg",
                ),
                Prediction(
                    PredictionType.category,
                    data={"priority": 1},
                    source_image="/123/3.jpg",
                ),
                Prediction(
                    PredictionType.category,
                    data={"priority": 8},
                    source_image="/123/2.jpg",
                ),
            ],
            [5, 3, 2, 0, 1, 4, 6],
        ),
    ],
)
def test_sort_predictions(predictions, order):
    assert sort_predictions(predictions) == [predictions[idx] for idx in order]


class FakeProductStore:
    def __init__(self, data: Optional[Dict] = None):
        self.data = data or {}

    def __getitem__(self, item):
        return self.data.get(item)


class InsightImporterWithIsConflictingInsight(InsightImporter):
    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag


class TestInsightImporter:
    def test_get_insight_update_no_reference(self):
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE, type=InsightType.label, value_tag="tag1"
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE, type=InsightType.label, value_tag="tag2"
            ),
        ]
        (
            to_create,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(candidates, [])
        assert to_create == candidates
        assert to_delete == []

    def test_get_insight_update_duplicates(self):
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE, type=InsightType.label, value_tag="tag1"
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE, type=InsightType.label, value_tag="tag1"
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE, type=InsightType.label, value_tag="tag2"
            ),
        ]
        (
            to_create,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(candidates, [])
        assert to_create == [candidates[0], candidates[2]]
        assert to_delete == []

    def test_get_insight_update_conflicting_reference(self):
        class TestInsightImporter(InsightImporter):
            @classmethod
            def is_conflicting_insight(cls, candidate, reference):
                return candidate.value_tag == reference.value_tag

        references = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                id=uuid.UUID("a6aa784b-4d39-4baa-a16c-b2f1c9dac9f9"),
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag3",
                id=uuid.UUID("f3fca6c5-15be-4bd7-bd72-90c7abd2ed4c"),
            ),
        ]
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                id=uuid.UUID("5d71c235-2304-4473-ba1c-63f3569f44a0"),
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag2",
                id=uuid.UUID("c984b252-fb31-41ea-b78e-6ca08b9f5e4b"),
            ),
        ]
        (
            to_create,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(
            candidates, references
        )
        # only the insight with a different value_tag is removed / created
        assert to_create == [candidates[1]]
        assert to_delete == [references[1]]

    def test_generate_insights_no_predictions(self):
        assert (
            list(
                InsightImporter.generate_insights(
                    [],
                    DEFAULT_SERVER_DOMAIN,
                    automatic=True,
                    product_store=FakeProductStore(),
                )
            )
            == []
        )

    def test_generate_insights_missing_product_no_references(self, mocker):
        get_existing_insight_mock = mocker.patch(
            "robotoff.insights.importer.get_existing_insight", return_value=[]
        )
        assert (
            list(
                InsightImporter.generate_insights(
                    [
                        Prediction(
                            type=PredictionType.category,
                            barcode=DEFAULT_BARCODE,
                            data={},
                        )
                    ],
                    DEFAULT_SERVER_DOMAIN,
                    automatic=True,
                    product_store=FakeProductStore(),
                )
            )
            == []
        )
        get_existing_insight_mock.assert_called_once()

    def test_generate_insights_missing_product_with_reference(self, mocker):
        reference = ProductInsight(barcode=DEFAULT_BARCODE, type=InsightType.category)
        get_existing_insight_mock = mocker.patch(
            "robotoff.insights.importer.get_existing_insight",
            return_value=[reference],
        )
        generated = list(
            InsightImporter.generate_insights(
                [
                    Prediction(
                        type=PredictionType.category,
                        barcode=DEFAULT_BARCODE,
                        data={},
                    )
                ],
                DEFAULT_SERVER_DOMAIN,
                automatic=True,
                product_store=FakeProductStore(),
            )
        )
        assert generated == [([], [reference])]
        get_existing_insight_mock.assert_called_once()

    def test_generate_insights_creation_and_deletion(self, mocker):
        """Test `get_insight_update` method in the following case:

        - product exists
        - an insight of the same type already exists for this product
        - the insight update triggers the deletion of the old insight and
        the creation of a new one
        """

        class FakeImporter(InsightImporter):
            @classmethod
            def generate_candidates(cls, product, predictions):
                yield from (
                    ProductInsight(**prediction.to_dict()) for prediction in predictions
                )

            @classmethod
            def get_insight_update(cls, candidates, references):
                return candidates, references

        reference = ProductInsight(
            barcode=DEFAULT_BARCODE, type=InsightType.category, value_tag="tag1"
        )
        get_existing_insight_mock = mocker.patch(
            "robotoff.insights.importer.get_existing_insight",
            return_value=[reference],
        )
        prediction = Prediction(
            type=PredictionType.category,
            barcode=DEFAULT_BARCODE,
            value_tag="tag2",
            data={"k": "v"},
            automatic_processing=True,
            source_image="/images/products/322/982/001/9192/8.jpg",
        )
        generated = list(
            FakeImporter.generate_insights(
                [prediction],
                DEFAULT_SERVER_DOMAIN,
                automatic=False,
                product_store=FakeProductStore(
                    data={
                        DEFAULT_BARCODE: Product(
                            {
                                "code": DEFAULT_BARCODE,
                                "images": {"8": {"uploaded_t": DEFAULT_UPLOADED_T}},
                            }
                        )
                    }
                ),
            )
        )
        assert len(generated) == 1
        to_create, to_delete = generated[0]
        assert len(to_create) == 1
        created_insight = to_create[0]
        assert isinstance(created_insight, ProductInsight)
        assert created_insight.automatic_processing is False
        assert isinstance(created_insight.timestamp, datetime.datetime)
        assert created_insight.type == "category"
        assert created_insight.value_tag == "tag2"
        assert created_insight.data == {"k": "v"}
        assert created_insight.barcode == DEFAULT_BARCODE
        assert created_insight.server_domain == DEFAULT_SERVER_DOMAIN
        assert created_insight.server_type == "off"
        assert created_insight.process_after is None
        uuid.UUID(created_insight.id)
        assert to_delete == [reference]
        get_existing_insight_mock.assert_called_once()

    def test_generate_insights_automatic_processing(self, mocker):
        class FakeImporter(InsightImporter):
            @classmethod
            def generate_candidates(cls, product, predictions):
                yield from (
                    ProductInsight(**prediction.to_dict()) for prediction in predictions
                )

            @classmethod
            def get_insight_update(cls, candidates, references):
                return candidates, references

        mocker.patch(
            "robotoff.insights.importer.get_existing_insight",
            return_value=[],
        )
        prediction = Prediction(
            type=PredictionType.category,
            barcode=DEFAULT_BARCODE,
            data={},
            automatic_processing=True,
        )
        generated = list(
            FakeImporter.generate_insights(
                [prediction],
                DEFAULT_SERVER_DOMAIN,
                automatic=True,
                product_store=FakeProductStore(
                    data={DEFAULT_BARCODE: Product({"code": DEFAULT_BARCODE})}
                ),
            )
        )
        assert len(generated) == 1
        to_create, to_delete = generated[0]
        assert not to_delete
        assert len(to_create) == 1
        created_insight = to_create[0]
        assert isinstance(created_insight.process_after, datetime.datetime)

    def test_import_insights_invalid_types(self):
        class FakeImporter(InsightImporter):
            @staticmethod
            def get_required_prediction_types():
                return {PredictionType.category, PredictionType.image_flag}

        with pytest.raises(ValueError, match="unexpected prediction type: 'label'"):
            FakeImporter.import_insights(
                [Prediction(type=PredictionType.label)],
                DEFAULT_SERVER_DOMAIN,
                automatic=True,
                product_store=FakeProductStore(),
            )

    def test_import_insights(self, mocker):
        class FakeImporter(InsightImporter):
            @staticmethod
            def get_required_prediction_types():
                return {PredictionType.label}

            @classmethod
            def generate_insights(
                cls, predictions, server_domain, automatic, product_store
            ):
                yield [
                    ProductInsight(
                        barcode=DEFAULT_BARCODE,
                        type=InsightType.label.name,
                        value_tag="tag1",
                    )
                ], [
                    ProductInsight(
                        barcode=DEFAULT_BARCODE,
                        type=InsightType.label.name,
                        value_tag="tag2",
                    )
                ]

        product_insight_delete_mock = mocker.patch.object(ProductInsight, "delete")
        batch_insert_mock = mocker.patch(
            "robotoff.insights.importer.batch_insert", return_value=1
        )
        imported = FakeImporter.import_insights(
            [Prediction(type=PredictionType.label)],
            DEFAULT_SERVER_DOMAIN,
            automatic=True,
            product_store=FakeProductStore(),
        )
        assert imported == 1
        batch_insert_mock.assert_called_once()
        product_insight_delete_mock.assert_called_once()


class TestPackagerCodeInsightImporter:
    def test_get_type(self):
        assert PackagerCodeInsightImporter.get_type() == InsightType.packager_code

    def test_get_required_prediction_types(self):
        assert PackagerCodeInsightImporter.get_required_prediction_types() == {
            PredictionType.packager_code
        }

    def test_is_conflicting_insight(self):
        assert PackagerCodeInsightImporter.is_conflicting_insight(
            ProductInsight(value="tag1"), ProductInsight(value="tag1")
        )
        assert not PackagerCodeInsightImporter.is_conflicting_insight(
            ProductInsight(value="tag1"), ProductInsight(value="tag2")
        )

    @pytest.mark.parametrize(
        "product,emb_code,expected",
        [
            (
                Product({"emb_codes_tags": ["FR 40.261.001 CE"]}),
                "fr 40261001 ce",
                False,
            ),
            (
                Product({"emb_codes_tags": ["FR 40.261.001 CE"]}),
                "fr 50262601 ce",
                True,
            ),
        ],
    )
    def test_is_prediction_valid(self, product, emb_code, expected):
        assert (
            PackagerCodeInsightImporter.is_prediction_valid(product, emb_code)
            is expected
        )

    def test_generate_candidates(self):
        prediction = Prediction(
            type=PredictionType.packager_code, value="fr 40.261.001 ce"
        )
        selected = list(
            PackagerCodeInsightImporter.generate_candidates(
                Product({"emb_codes_tags": ["FR 50.200.000 CE"]}),
                [prediction],
            )
        )
        assert len(selected) == 1
        insight = selected[0]
        assert isinstance(insight, ProductInsight)
        assert insight.value == prediction.value
        assert insight.type == InsightType.packager_code


class TestLabelInsightImporter:
    def test_get_type(self):
        assert LabelInsightImporter.get_type() == InsightType.label

    def test_get_required_prediction_types(self):
        assert LabelInsightImporter.get_required_prediction_types() == {
            PredictionType.label
        }

    @pytest.mark.parametrize(
        "label,to_check_labels,expected",
        [
            ("en:organic", {"en:eu-organic"}, True),
            ("en:eu-organic", {"en:organic"}, False),
            ("en:organic", {"en:fsc"}, False),
            ("en:fsc", {"en:organic"}, False),
        ],
    )
    def test_is_parent_label(self, label, to_check_labels, expected):
        assert LabelInsightImporter.is_parent_label(label, to_check_labels) is expected


class TestCategoryImporter:
    def test_get_type(self):
        assert CategoryImporter.get_type() == InsightType.category

    def test_get_required_prediction_types(self):
        assert CategoryImporter.get_required_prediction_types() == {
            PredictionType.category
        }

    @pytest.mark.parametrize(
        "category,to_check_categories,expected",
        [
            ("en:salmons", {"en:smoked-salmons"}, True),
            ("en:smoked-salmons", {"en:salmons"}, False),
            ("en:snacks", {"en:dairies"}, False),
            ("en:dairies", {"en:snacks"}, False),
        ],
    )
    def test_is_parent_category(self, category, to_check_categories, expected):
        assert (
            CategoryImporter.is_parent_category(category, to_check_categories)
            is expected
        )


class TestProductWeightImporter:
    def test_get_type(self):
        assert ProductWeightImporter.get_type() == InsightType.product_weight

    def test_get_required_prediction_types(self):
        assert ProductWeightImporter.get_required_prediction_types() == {
            PredictionType.product_weight
        }

    def test_is_conflicting_insight(self):
        assert ProductWeightImporter.is_conflicting_insight(
            ProductInsight(value="30 g"), ProductInsight(value="30 g")
        )
        assert not ProductWeightImporter.is_conflicting_insight(
            ProductInsight(value="30 g"), ProductInsight(value="40 g")
        )

    @staticmethod
    def generate_prediction(
        value, data: Dict[str, Any], automatic_processing: Optional[bool] = None
    ):
        return Prediction(
            barcode=DEFAULT_BARCODE,
            value=value,
            type=PredictionType.product_weight,
            data=data,
            automatic_processing=automatic_processing,
            predictor="ocr",
        )

    @staticmethod
    def get_product(quantity: Optional[str] = None):
        return Product({"code": DEFAULT_BARCODE, "quantity": quantity})

    @staticmethod
    def get_product_weight_predictions(
        predictions: List[Prediction],
        barcode: Optional[str] = None,
        source_image: Optional[str] = None,
    ):
        return ProductPredictions(
            predictions=predictions,
            barcode=barcode or DEFAULT_BARCODE,
            type=PredictionType.product_weight,
            source_image=source_image,
        )

    def test_generate_candidates_product_with_weight(self):
        value = "30 g"
        insight_data = {"matcher_type": "with_mention", "text": value}
        predictions = [self.generate_prediction(value, insight_data)]
        assert (
            list(
                ProductWeightImporter.generate_candidates(
                    self.get_product(quantity="30 g"), predictions
                )
            )
            == []
        )

    def test_generate_candidates_single(self):
        value = "30 g"
        insight_data = {"matcher_type": "with_mention", "text": value}
        predictions = [self.generate_prediction(value, insight_data)]
        candidates = list(
            ProductWeightImporter.generate_candidates(self.get_product(), predictions)
        )
        assert len(candidates) == 1
        candidate = candidates[0]
        assert isinstance(candidate, ProductInsight)
        assert candidate.automatic_processing is None
        assert candidate.type == "product_weight"
        assert candidate.data == insight_data
        assert candidate.value_tag is None
        assert candidate.predictor == "ocr"
        assert candidate.barcode == DEFAULT_BARCODE

    def test_generate_candidates_multiple_predictions(self):
        value_1 = "30 g net"
        value_2 = "150 g"
        data_1 = {"matcher_type": "no_mention", "text": value_1}
        data_2 = {"matcher_type": "no_mention", "text": value_2}
        predictions = [
            self.generate_prediction(value_1, data_1),
            self.generate_prediction(value_2, data_2),
        ]
        candidates = list(
            ProductWeightImporter.generate_candidates(self.get_product(), predictions)
        )
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.value == value_1
        assert candidate.automatic_processing is False

    def test_generate_candidates_multiple_predictions_different_subtypes(self):
        value_1 = "30 g net"
        value_2 = "150 g"
        data_1 = {"matcher_type": "with_ending_mention", "text": value_1}
        data_2 = {"matcher_type": "no_mention", "text": value_2}
        predictions = [
            self.generate_prediction(value_1, data_1),
            self.generate_prediction(value_2, data_2),
        ]
        candidates = list(
            ProductWeightImporter.generate_candidates(self.get_product(), predictions)
        )
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.automatic_processing is None
        assert candidate.value == value_1

    def test_generate_candidates_from_product_name(self):
        value_1 = "30 g net"
        data_1 = {
            "matcher_type": "with_ending_mention",
            "text": value_1,
            "source": "product_name",
        }
        predictions = [
            self.generate_prediction(value_1, data_1),
        ]
        candidates = list(
            ProductWeightImporter.generate_candidates(self.get_product(), predictions)
        )
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.automatic_processing is False
        assert candidate.value == value_1


class TestExpirationDateImporter:
    def test_get_type(self):
        assert ExpirationDateImporter.get_type() == InsightType.expiration_date

    def test_get_required_prediction_types(self):
        assert ExpirationDateImporter.get_required_prediction_types() == {
            PredictionType.expiration_date
        }

    def test_is_conflicting_insight(self):
        assert ExpirationDateImporter.is_conflicting_insight(
            ProductInsight(value="tag1"), ProductInsight(value="tag1")
        )
        assert not ExpirationDateImporter.is_conflicting_insight(
            ProductInsight(value="tag1"), ProductInsight(value="tag2")
        )


class TestBrandInsightInsightImporter:
    def test_get_type(self):
        assert BrandInsightImporter.get_type() == InsightType.brand

    def test_get_required_prediction_types(self):
        assert BrandInsightImporter.get_required_prediction_types() == {
            PredictionType.brand
        }

    def test_is_conflicting_insight(self):
        assert BrandInsightImporter.is_conflicting_insight(
            ProductInsight(value_tag="tag1"), ProductInsight(value_tag="tag1")
        )
        assert not BrandInsightImporter.is_conflicting_insight(
            ProductInsight(value_tag="tag1"), ProductInsight(value_tag="tag2")
        )


class TestStoreInsightImporter:
    def test_get_type(self):
        assert StoreInsightImporter.get_type() == InsightType.store

    def test_get_required_prediction_types(self):
        assert StoreInsightImporter.get_required_prediction_types() == {
            PredictionType.store
        }

    def test_is_conflicting_insight(self):
        assert StoreInsightImporter.is_conflicting_insight(
            ProductInsight(value_tag="tag1"), ProductInsight(value_tag="tag1")
        )
        assert not StoreInsightImporter.is_conflicting_insight(
            ProductInsight(value_tag="tag1"), ProductInsight(value_tag="tag2")
        )


class TestPackagingInsightImporter:
    def test_get_type(self):
        assert PackagingInsightImporter.get_type() == InsightType.packaging

    def test_get_required_prediction_types(self):
        assert PackagingInsightImporter.get_required_prediction_types() == {
            PredictionType.packaging
        }

    def test_is_conflicting_insight(self):
        assert PackagingInsightImporter.is_conflicting_insight(
            ProductInsight(value_tag="tag1"), ProductInsight(value_tag="tag1")
        )
        assert not PackagingInsightImporter.is_conflicting_insight(
            ProductInsight(value_tag="tag1"), ProductInsight(value_tag="tag2")
        )


class TestImportInsightsForProducts:
    def test_import_insights_no_element(self, mocker):
        get_product_predictions_mock = mocker.patch(
            "robotoff.insights.importer.get_product_predictions", return_value=[]
        )
        import_insights_mock = mocker.patch(
            "robotoff.insights.importer.InsightImporter.import_insights",
            return_value=0,
        )
        product_store = FakeProductStore()
        import_insights_for_products(
            {DEFAULT_BARCODE: {PredictionType.category}},
            DEFAULT_SERVER_DOMAIN,
            automatic=True,
            product_store=product_store,
        )
        get_product_predictions_mock.assert_called_once()
        import_insights_mock.assert_called_once_with(
            [], DEFAULT_SERVER_DOMAIN, True, product_store
        )

    def test_import_insights_single_product(self, mocker):
        prediction_dict = {
            "barcode": DEFAULT_BARCODE,
            "type": PredictionType.category.name,
            "data": {},
        }
        prediction = Prediction(
            barcode=DEFAULT_BARCODE,
            type=PredictionType.category,
            data={},
        )
        get_product_predictions_mock = mocker.patch(
            "robotoff.insights.importer.get_product_predictions",
            return_value=[
                prediction_dict,
            ],
        )
        import_insights_mock = mocker.patch(
            "robotoff.insights.importer.InsightImporter.import_insights",
            return_value=1,
        )
        product_store = FakeProductStore()
        imported = import_insights_for_products(
            {DEFAULT_BARCODE: {PredictionType.category}},
            DEFAULT_SERVER_DOMAIN,
            automatic=True,
            product_store=product_store,
        )
        assert imported == 1
        get_product_predictions_mock.assert_called_once()
        import_insights_mock.assert_called_once_with(
            [prediction], DEFAULT_SERVER_DOMAIN, True, product_store
        )

    def test_import_insights_type_mismatch(self, mocker):
        prediction_dict = {
            "barcode": DEFAULT_BARCODE,
            "type": PredictionType.image_orientation.name,
            "data": {},
        }
        get_product_predictions_mock = mocker.patch(
            "robotoff.insights.importer.get_product_predictions",
            return_value=[
                prediction_dict,
            ],
        )
        import_insights_mock = mocker.patch(
            "robotoff.insights.importer.InsightImporter.import_insights",
            return_value=0,
        )
        product_store = FakeProductStore()
        imported = import_insights_for_products(
            {DEFAULT_BARCODE: {PredictionType.image_orientation}},
            DEFAULT_SERVER_DOMAIN,
            automatic=True,
            product_store=product_store,
        )
        assert imported == 0
        assert not get_product_predictions_mock.called
        assert not import_insights_mock.called
