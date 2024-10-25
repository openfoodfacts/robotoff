import datetime
import uuid
from typing import Any, Iterator, Optional

import pytest

from robotoff.insights.importer import (
    BrandInsightImporter,
    CategoryImporter,
    ExpirationDateImporter,
    InsightImporter,
    LabelInsightImporter,
    NutrientExtractionImporter,
    NutritionImageImporter,
    PackagerCodeInsightImporter,
    PackagingImporter,
    ProductWeightImporter,
    StoreInsightImporter,
    UPCImageImporter,
    import_insights_for_products,
    is_recent_image,
    is_selected_image,
    is_valid_insight_image,
    select_deepest_taxonomized_candidates,
)
from robotoff.models import ProductInsight
from robotoff.products import Product
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.types import (
    InsightType,
    JSONType,
    Prediction,
    PredictionType,
    ProductIdentifier,
    ProductInsightImportResult,
    ServerType,
)

DEFAULT_BARCODE = "3760094310634"
DEFAULT_SOURCE_IMAGE = "/376/009/431/0634/1.jpg"
DEFAULT_SERVER_TYPE = ServerType.off
DEFAULT_PRODUCT_ID = ProductIdentifier(DEFAULT_BARCODE, DEFAULT_SERVER_TYPE)
# 2022-02-08 16:07
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
    "image_ids,image_id,expected",
    [
        (
            ["1", "2"],
            "/151/525/1.jpg",
            True,
        ),
        (
            ["2"],
            "/151/525/1.jpg",
            False,
        ),
        (
            ["1", "front_fr"],
            "/151/525/front_fr.jpg",
            False,
        ),
    ],
)
def test_is_valid_insight_image(image_ids, image_id, expected):
    assert is_valid_insight_image(image_ids, image_id) is expected


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
    assert InsightImporter.sort_predictions(predictions) == [
        predictions[idx] for idx in order
    ]


@pytest.mark.parametrize(
    "candidates,taxonomy_name,kept_indices",
    [
        (
            [
                Prediction(PredictionType.category, value_tag="en:meats"),
                Prediction(PredictionType.category, value_tag="en:pork"),
            ],
            "category",
            [1],
        ),
        (
            [
                Prediction(PredictionType.category, value_tag="en:plant-based-foods"),
                Prediction(
                    PredictionType.category,
                    value_tag="en:plant-based-foods-and-beverages",
                ),
            ],
            "category",
            [0],
        ),
        (
            [
                Prediction(PredictionType.category, value_tag="en:miso-soup"),
                Prediction(PredictionType.category, value_tag="en:meats"),
                Prediction(PredictionType.category, value_tag="en:soups"),
                Prediction(PredictionType.category, value_tag="en:apricots"),
            ],
            "category",
            [0, 1, 3],
        ),
    ],
)
def test_select_deepest_taxonomized_candidates(candidates, taxonomy_name, kept_indices):
    taxonomy = get_taxonomy(taxonomy_name, offline=True)
    assert select_deepest_taxonomized_candidates(candidates, taxonomy) == [
        candidates[idx] for idx in kept_indices
    ]


class FakeProductStore:
    def __init__(self, data: Optional[dict] = None):
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
    def test_get_insight_update_annotated_references(self):
        candidates = []
        references = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                annotation=-1,
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag2",
            ),
        ]
        (
            to_create,
            to_update,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(
            candidates, references
        )
        assert to_create == []
        assert to_update == []
        assert to_delete == [references[1]]

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
            to_update,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(candidates, [])
        assert to_create == candidates
        assert to_update == []
        assert to_delete == []

    def test_get_insight_update_duplicates(self):
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                source_image="/1/1.jpg",
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                source_image="/1/2.jpg",
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                source_image="/1/2.jpg",
                predictor="PREDICTOR",
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag2",
                source_image="/1/1.jpg",
            ),
        ]
        (
            to_create,
            to_update,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(candidates, [])
        # the third candidate has a more recent image and a predictor so it
        # has higher priority
        assert to_create == [candidates[2], candidates[3]]
        assert to_delete == []
        assert to_update == []

    def test_get_insight_update_conflicting_reference(self):
        references = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
            ),
            # annotated product should be kept
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag3",
                annotation=1,
            ),
        ]
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag2",
            ),
        ]
        (
            to_create,
            to_update,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(
            candidates, references
        )
        # only the existing annotated insight is kept
        assert to_create == [candidates[1]]
        assert to_delete == []
        assert to_update == [(candidates[0], references[0])]

    def test_get_insight_update_no_overwrite_automatic_processing(
        self,
    ):
        """Don't overwrite an insight that is going to be applied
        automatically soon."""
        references = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                source_image="/1/1.jpg",
                automatic_processing=True,
            ),
        ]
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                source_image="/1/2.jpg",
                automatic_processing=True,
            ),
        ]
        (
            to_create,
            to_update,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(
            candidates, references
        )
        assert to_create == []
        assert to_delete == []
        assert to_update == []

    def test_get_insight_update_conflicting_reference_different_source_image(
        self,
    ):
        references = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                source_image="/1/1.jpg",
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag3",
                automatic_processing=False,
            ),
        ]
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                source_image="/1/2.jpg",
            ),
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag3",
                automatic_processing=True,
            ),
        ]
        (
            to_create,
            to_update,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(
            candidates, references
        )
        # for both candidate/reference couples with the same value_tag,
        # source_image is different so we create a new insight instead of
        # updating the old one.
        assert to_create == [candidates[0]]
        assert to_delete == [references[0]]
        assert to_update == [(candidates[1], references[1])]

    def test_get_insight_update_annotated_reference(self):
        references = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag1",
                annotation=0,
            ),
        ]
        candidates = [
            ProductInsight(
                barcode=DEFAULT_BARCODE,
                type=InsightType.label,
                value_tag="tag2",
            ),
        ]
        (
            to_create,
            to_update,
            to_delete,
        ) = InsightImporterWithIsConflictingInsight.get_insight_update(
            candidates, references
        )
        assert to_create == candidates
        # Annotated existing insight should not be deleted
        assert to_delete == []
        assert to_update == []

    def test_generate_insights_no_predictions(self, mocker):
        get_existing_insight_mock = mocker.patch(
            "robotoff.insights.importer.get_existing_insight", return_value=[]
        )
        assert CategoryImporter.generate_insights(
            DEFAULT_BARCODE,
            [],
            product_store=FakeProductStore(),
        ) == ([], [], [])
        get_existing_insight_mock.assert_called_once()

    def test_generate_insights_no_predictions_with_existing_insight(self, mocker):
        existing_insight = ProductInsight(
            barcode=DEFAULT_BARCODE,
            type=InsightType.category.name,
            value_tag="en:fishes",
        )
        get_existing_insight_mock = mocker.patch(
            "robotoff.insights.importer.get_existing_insight",
            return_value=[existing_insight],
        )
        assert CategoryImporter.generate_insights(
            DEFAULT_BARCODE,
            [],
            product_store=FakeProductStore(),
        ) == ([], [], [existing_insight])
        get_existing_insight_mock.assert_called_once()

    def test_generate_insights_missing_product_no_references(self, mocker):
        get_existing_insight_mock = mocker.patch(
            "robotoff.insights.importer.get_existing_insight", return_value=[]
        )
        assert InsightImporter.generate_insights(
            DEFAULT_BARCODE,
            [
                Prediction(
                    type=PredictionType.category,
                    barcode=DEFAULT_BARCODE,
                    data={},
                )
            ],
            product_store=FakeProductStore(),
        ) == ([], [], [])
        get_existing_insight_mock.assert_called_once()

    def test_generate_insights_missing_product_with_reference(self, mocker):
        reference = ProductInsight(barcode=DEFAULT_BARCODE, type=InsightType.category)
        get_existing_insight_mock = mocker.patch(
            "robotoff.insights.importer.get_existing_insight",
            return_value=[reference],
        )
        generated = InsightImporter.generate_insights(
            DEFAULT_BARCODE,
            [
                Prediction(
                    type=PredictionType.category,
                    barcode=DEFAULT_BARCODE,
                    data={},
                )
            ],
            product_store=FakeProductStore(),
        )
        assert generated == ([], [], [reference])
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
            def generate_candidates(cls, product, predictions, product_id=None):
                yield from (
                    ProductInsight(**prediction.to_dict()) for prediction in predictions
                )

            @classmethod
            def get_insight_update(cls, candidates, references):
                return candidates, [], references

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
        generated = FakeImporter.generate_insights(
            DEFAULT_BARCODE,
            [prediction],
            product_store=FakeProductStore(
                data={
                    DEFAULT_BARCODE: Product(
                        {
                            "code": DEFAULT_BARCODE,
                            "images": {
                                "8": {
                                    "uploaded_t": (
                                        datetime.datetime.now(datetime.timezone.utc)
                                        - datetime.timedelta(days=600)
                                    ).timestamp()
                                }
                            },
                        }
                    )
                }
            ),
        )
        to_create, to_update, to_delete = generated
        assert len(to_create) == 1
        assert len(to_update) == 0
        created_insight = to_create[0]
        assert isinstance(created_insight, ProductInsight)
        assert created_insight.automatic_processing is True
        assert isinstance(created_insight.timestamp, datetime.datetime)
        assert created_insight.type == "category"
        assert created_insight.value_tag == "tag2"
        assert created_insight.data == {"k": "v"}
        assert created_insight.barcode == DEFAULT_BARCODE
        assert created_insight.server_type == "off"
        assert created_insight.process_after is not None
        uuid.UUID(created_insight.id)
        assert to_delete == [reference]
        get_existing_insight_mock.assert_called_once()

    def test_generate_insights_automatic_processing(self, mocker):
        class FakeImporter(InsightImporter):
            @classmethod
            def generate_candidates(cls, product, predictions, product_id=None):
                yield from (
                    ProductInsight(**prediction.to_dict()) for prediction in predictions
                )

            @classmethod
            def get_insight_update(cls, candidates, references):
                return candidates, [], references

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
        generated = FakeImporter.generate_insights(
            DEFAULT_BARCODE,
            [prediction],
            product_store=FakeProductStore(
                data={DEFAULT_BARCODE: Product({"code": DEFAULT_BARCODE})}
            ),
        )
        to_create, to_update, to_delete = generated
        assert not to_delete
        assert to_update == []
        assert len(to_create) == 1
        created_insight = to_create[0]
        assert isinstance(created_insight.process_after, datetime.datetime)

    def test_import_insights_invalid_types(self):
        class FakeImporter(InsightImporter):
            @staticmethod
            def get_required_prediction_types():
                return {PredictionType.category, PredictionType.image_flag}

        with pytest.raises(
            ValueError, match="unexpected prediction type: 'PredictionType.label'"
        ):
            FakeImporter.import_insights(
                DEFAULT_BARCODE,
                [Prediction(type=PredictionType.label)],
                product_store=FakeProductStore(),
            )

    def test_import_insights(self, mocker):
        class FakeImporter(InsightImporter):
            @staticmethod
            def get_required_prediction_types():
                return {PredictionType.label}

            @classmethod
            def generate_insights(cls, barcode, predictions, product_store):
                return (
                    [
                        ProductInsight(
                            barcode=DEFAULT_BARCODE,
                            type=InsightType.label.name,
                            value_tag="tag1",
                        )
                    ],
                    [],
                    [
                        ProductInsight(
                            barcode=DEFAULT_BARCODE,
                            type=InsightType.label.name,
                            value_tag="tag2",
                        )
                    ],
                )

        product_insight_delete_mock = mocker.patch.object(ProductInsight, "delete")
        batch_insert_mock = mocker.patch(
            "robotoff.insights.importer.batch_insert", return_value=1
        )
        import_result = FakeImporter.import_insights(
            DEFAULT_BARCODE,
            [Prediction(type=PredictionType.label)],
            product_store=FakeProductStore(),
        )
        assert len(import_result.insight_created_ids) == 1
        assert len(import_result.insight_updated_ids) == 0
        assert len(import_result.insight_deleted_ids) == 1
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
                None,
            )
        )
        assert len(selected) == 1
        insight = selected[0]
        assert isinstance(insight, ProductInsight)
        assert insight.value == prediction.value
        assert insight.type == InsightType.packager_code

    def test_generate_asc_candidates(self):
        prediction = Prediction(type=PredictionType.packager_code, value="ASC-C-00026")

        product = Product({"emb_codes_tags": ["ASC-C-00950"]})

        insight_data = list(
            PackagerCodeInsightImporter().generate_candidates(
                product, [prediction], None
            )
        )

        assert len(insight_data) == 1
        insight = insight_data[0]
        assert isinstance(insight, ProductInsight)
        assert insight.value == prediction.value
        assert insight.type == InsightType.packager_code
        assert insight.data == {}


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
    def test_is_parent_label(self, label, to_check_labels, expected, mocker):
        mocker.patch(
            "robotoff.insights.importer.get_taxonomy",
            return_value=get_taxonomy("label", offline=True),
        )
        assert LabelInsightImporter.is_parent_label(label, to_check_labels) is expected

    @pytest.mark.parametrize(
        "predictions,product,expected",
        [
            (
                [
                    Prediction(PredictionType.label, value_tag="en:organic"),
                ],
                Product({"code": DEFAULT_BARCODE, "labels_tags": ["en:organic"]}),
                [],
            ),
            (
                [
                    Prediction(PredictionType.label, value_tag="en:non-existing-tag"),
                ],
                Product({"code": DEFAULT_BARCODE}),
                [],
            ),
            (
                [
                    Prediction(
                        PredictionType.label, value_tag="en:organic", predictor="regex"
                    ),
                ],
                Product({"code": DEFAULT_BARCODE}),
                [("en:organic", True)],
            ),
            (
                # en:organic is a parent of en:ecoveg
                [
                    Prediction(
                        PredictionType.label, value_tag="en:organic", predictor="regex"
                    ),
                    Prediction(
                        PredictionType.label,
                        value_tag="en:ecoveg",
                        predictor="flashtext",
                    ),
                ],
                Product({"code": DEFAULT_BARCODE}),
                [("en:ecoveg", False)],
            ),
            (
                # en:organic and en:vegan are both parents of en:ecoveg
                # we add a non existing tag and an independent label
                [
                    Prediction(
                        PredictionType.label,
                        value_tag="en:vegan",
                        predictor="flashtext",
                    ),
                    Prediction(
                        PredictionType.label,
                        value_tag="en:ecoveg",
                        predictor="flashtext",
                    ),
                    Prediction(
                        PredictionType.label,
                        value_tag="en:non-existing-tag",
                        predictor="flashtext",
                    ),
                    Prediction(
                        PredictionType.label,
                        value_tag="en:max-havelaar",
                        predictor="flashtext",
                    ),
                    Prediction(
                        PredictionType.label,
                        value_tag="en:organic",
                        predictor="flashtext",
                    ),
                ],
                Product({"code": DEFAULT_BARCODE, "labels_tags": ["en:vegan"]}),
                [("en:ecoveg", False), ("en:max-havelaar", True)],
            ),
            (
                # fr:sans-gluten should be normalized into en:no-gluten
                [
                    Prediction(
                        PredictionType.label,
                        value_tag="fr:sans-gluten",
                        automatic_processing=True,
                    ),
                ],
                Product({"code": DEFAULT_BARCODE}),
                [("en:no-gluten", True)],
            ),
        ],
    )
    def test_generate_candidates(self, predictions, product, expected, mocker):
        mocker.patch(
            "robotoff.insights.importer.get_taxonomy",
            return_value=get_taxonomy("label", offline=True),
        )
        candidates = list(
            LabelInsightImporter.generate_candidates(product, predictions, None)
        )
        assert all(isinstance(c, ProductInsight) for c in candidates)
        assert len(candidates) == len(expected)
        candidates.sort(key=lambda c: c.value_tag)
        for candidate, (value_tag, automatic_processing) in zip(candidates, expected):
            assert candidate.value_tag == value_tag
            assert candidate.automatic_processing is automatic_processing


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
    def test_is_parent_category(self, category, to_check_categories, expected, mocker):
        mocker.patch(
            "robotoff.insights.importer.get_taxonomy",
            return_value=get_taxonomy("category", offline=True),
        )
        assert (
            CategoryImporter.is_parent_category(category, to_check_categories)
            is expected
        )

    @pytest.mark.parametrize(
        "predictions,product,expected_value_tags",
        [
            (
                [
                    Prediction(PredictionType.category, value_tag="en:meats"),
                ],
                Product({"code": DEFAULT_BARCODE, "categories_tags": ["en:meats"]}),
                [],
            ),
            (
                [
                    Prediction(
                        PredictionType.category, value_tag="en:non-existing-tag"
                    ),
                ],
                Product({"code": DEFAULT_BARCODE}),
                [],
            ),
            (
                [
                    Prediction(PredictionType.category, value_tag="en:meats"),
                ],
                Product({"code": DEFAULT_BARCODE}),
                ["en:meats"],
            ),
            (
                [
                    Prediction(PredictionType.category, value_tag="en:meats"),
                    Prediction(PredictionType.category, value_tag="en:pork"),
                ],
                Product({"code": DEFAULT_BARCODE}),
                ["en:pork"],
            ),
            (
                [
                    Prediction(PredictionType.category, value_tag="en:miso-soup"),
                    Prediction(PredictionType.category, value_tag="en:meats"),
                    Prediction(PredictionType.category, value_tag="en:soups"),
                    Prediction(PredictionType.category, value_tag="en:apricots"),
                ],
                Product({"code": DEFAULT_BARCODE, "categories_tags": ["en:apricots"]}),
                ["en:miso-soup", "en:meats"],
            ),
        ],
    )
    def test_generate_candidates(
        self, predictions, product, expected_value_tags, mocker, category_taxonomy
    ):
        mocker.patch(
            "robotoff.insights.importer.get_taxonomy",
            return_value=category_taxonomy,
        )
        candidates = list(
            CategoryImporter.generate_candidates(product, predictions, None)
        )
        assert all(isinstance(c, ProductInsight) for c in candidates)
        assert len(candidates) == len(expected_value_tags)

        for candidate, expected_value_tag in zip(candidates, expected_value_tags):
            assert candidate.value_tag == expected_value_tag

    @pytest.mark.parametrize(
        "value_tag,categories_tags,expected_campaign",
        [
            (
                "en:frozen-french-fries-to-deep-fry",
                [],
                ["agribalyse-category", "missing-category"],
            ),
            ("en:breads", ["en:breads"], []),
        ],
    )
    def test_add_campaign(
        self,
        value_tag: str,
        categories_tags: list[str],
        expected_campaign: list[str],
        mocker,
    ):
        mocker.patch(
            "robotoff.insights.importer.get_taxonomy",
            return_value=get_taxonomy("category", offline=True),
        )
        insight = ProductInsight(value_tag=value_tag)
        CategoryImporter.add_optional_fields(
            insight,
            Product({"code": DEFAULT_BARCODE, "categories_tags": categories_tags}),
        )
        assert insight.campaign == expected_campaign


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
        value, data: dict[str, Any], automatic_processing: Optional[bool] = None
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

    def test_generate_candidates_product_with_weight(self):
        value = "30 g"
        insight_data = {"matcher_type": "with_mention", "text": value}
        predictions = [self.generate_prediction(value, insight_data)]
        assert (
            list(
                ProductWeightImporter.generate_candidates(
                    self.get_product(quantity="30 g"), predictions, None
                )
            )
            == []
        )

    def test_generate_candidates_single(self):
        value = "30 g"
        insight_data = {"matcher_type": "with_mention", "text": value}
        predictions = [self.generate_prediction(value, insight_data)]
        candidates = list(
            ProductWeightImporter.generate_candidates(
                self.get_product(), predictions, None
            )
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
            ProductWeightImporter.generate_candidates(
                self.get_product(), predictions, None
            )
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
            ProductWeightImporter.generate_candidates(
                self.get_product(), predictions, None
            )
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
            ProductWeightImporter.generate_candidates(
                self.get_product(), predictions, None
            )
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


class TestPackagingImporter:
    @pytest.mark.parametrize(
        "candidate_element,ref_element,expected,reverse",
        [
            ({"shape": "en:tablespoon"}, {"shape": "en:tube"}, False, False),
            ({"shape": "en:tube"}, {"shape": "en:tube"}, True, False),
            (
                {"shape": "en:tube", "recycling": "en:reuse"},
                {"shape": "en:tube"},
                False,
                True,
            ),
            (
                {"shape": "en:tube", "material": "en:plastic", "recycling": "en:reuse"},
                {"shape": "en:tube", "recycling": "en:reuse"},
                False,
                True,
            ),
            (
                {"shape": "en:tube", "material": "en:plastic"},
                {"shape": "en:tube", "material": "en:ldpe-low-density-polyethylene"},
                True,
                True,
            ),
            (
                {"shape": "en:tube", "material": "en:ldpe-low-density-polyethylene"},
                {"shape": "en:tube", "material": "en:plastic"},
                False,
                True,
            ),
            (
                {"shape": "en:pizza-box", "material": "en:plastic"},
                {"shape": "en:box", "material": "en:ldpe-low-density-polyethylene"},
                False,
                False,
            ),
            (
                {"shape": "en:box", "material": "en:ldpe-low-density-polyethylene"},
                {"shape": "en:pizza-box", "material": "en:plastic"},
                False,
                False,
            ),
            (
                {"shape": "en:box"},
                {"shape": "en:pizza-box"},
                True,
                True,
            ),
        ],
    )
    def test_discard_packaging_element(
        self, candidate_element, ref_element, expected, reverse
    ):
        taxonomies = {
            name: get_taxonomy(name, offline=True)
            for name in (
                TaxonomyType.packaging_shape.name,
                TaxonomyType.packaging_material.name,
                TaxonomyType.packaging_recycling.name,
            )
        }
        assert (
            PackagingImporter.discard_packaging_element(
                candidate_element, ref_element, taxonomies
            )
            is expected
        )
        if reverse:
            # assert we get the opposite result by switching candidate and
            # reference for the test cases where we expect it to be valid
            assert (
                PackagingImporter.discard_packaging_element(
                    ref_element, candidate_element, taxonomies
                )
                is not expected
            )

    @pytest.mark.parametrize(
        "elements,sort_indices",
        [
            (
                [
                    {"shape": None},
                    {"shape": None, "recycling": None},
                ],
                [1, 0],
            ),
            (
                [
                    {"shape": None, "recycling": None},
                    {"shape": None},
                    {"shape": None, "recycling": None, "material": None},
                ],
                [2, 0, 1],
            ),
        ],
    )
    def test_sort_predictions(self, elements, sort_indices):
        predictions = [
            Prediction(type=PredictionType.packaging, data={"element": element})
            for element in elements
        ]
        assert PackagingImporter.sort_predictions(predictions) == [
            predictions[i] for i in sort_indices
        ]


class TestUPCImageImporter:
    def test_get_type(self):
        assert UPCImageImporter.get_type() == InsightType.is_upc_image

    def test_get_required_prediction_types(self):
        assert UPCImageImporter.get_required_prediction_types() == {
            PredictionType.is_upc_image
        }

    def test_is_conflicting_insight(self):
        assert UPCImageImporter.is_conflicting_insight(
            ProductInsight(source_image="source1"),
            ProductInsight(source_image="source1"),
        )
        assert not UPCImageImporter.is_conflicting_insight(
            ProductInsight(source_image="source1"),
            ProductInsight(source_image="source2"),
        )


class TestNutritionImageImporter:
    def test_get_type(self):
        assert NutritionImageImporter.get_type() == InsightType.nutrition_image

    def test_get_required_prediction_types(self):
        assert NutritionImageImporter.get_required_prediction_types() == {
            PredictionType.nutrient_mention,
            PredictionType.image_orientation,
        }

    def test_get_input_prediction_types(self):
        assert NutritionImageImporter.get_input_prediction_types() == {
            PredictionType.nutrient,
            PredictionType.nutrient_mention,
            PredictionType.image_orientation,
        }

    def test_generate_candidates_for_image(self):
        image_orientation_prediction = Prediction(
            id=1,
            type=PredictionType.image_orientation,
            data={"rotation": 90},
            barcode=DEFAULT_BARCODE,
            server_type=DEFAULT_SERVER_TYPE.name,
            source_image=DEFAULT_SOURCE_IMAGE,
        )
        nutrient_mention_prediction = Prediction(
            id=2,
            type=PredictionType.nutrient_mention,
            data={},
            barcode=DEFAULT_BARCODE,
            server_type=DEFAULT_SERVER_TYPE.name,
            source_image=DEFAULT_SOURCE_IMAGE,
        )
        nutrient_mention_prediction.data = {
            "mentions": {"sugar": [{"raw": "sucre", "languages": ["fr"]}]}
        }
        # Only 1 mention is not enough to generate a candidate (at least 5 are
        # required)
        assert (
            list(
                NutritionImageImporter.generate_candidates_for_image(
                    nutrient_mention_prediction, image_orientation_prediction
                )
            )
            == []
        )
        base_mentions_without_nutrient_values = {
            "sugar": [{"raw": "sucre", "languages": ["fr"]}],
            "carbohydrate": [{"raw": "glucides", "languages": ["fr"]}],
            "salt": [{"raw": "sel", "languages": ["fr"]}],
            "protein": [{"raw": "sucre", "languages": ["fr"]}],
            "saturated_fat": [{"raw": "graisses saturées", "languages": ["fr"]}],
        }
        nutrient_mention_prediction.data = {
            "mentions": base_mentions_without_nutrient_values
        }
        # we don't have any nutrient_value, so we don't generate candidate
        assert (
            list(
                NutritionImageImporter.generate_candidates_for_image(
                    nutrient_mention_prediction, image_orientation_prediction
                )
            )
            == []
        )

        # we don't have any enough nutrient_value (3 are required), so we don't
        # generate candidate
        nutrient_mention_prediction.data = {
            "mentions": {
                **base_mentions_without_nutrient_values,
                "nutrient_value": [{"raw": "14 g"}, {"raw": "16 g"}],
            }
        }
        assert (
            list(
                NutritionImageImporter.generate_candidates_for_image(
                    nutrient_mention_prediction, image_orientation_prediction
                )
            )
            == []
        )

        # we have enough nutrient values but we don't have any energy mention
        # (kJ/kcal), so we don't generate candidate
        nutrient_mention_prediction.data = {
            "mentions": {
                **base_mentions_without_nutrient_values,
                "nutrient_value": [
                    {"raw": "14 g"},
                    {"raw": "16 g"},
                    {"raw": "18 g"},
                ],
            }
        }
        assert (
            list(
                NutritionImageImporter.generate_candidates_for_image(
                    nutrient_mention_prediction, image_orientation_prediction
                )
            )
            == []
        )

        nutrient_mention_prediction.data = {
            "mentions": {
                **base_mentions_without_nutrient_values,
                "nutrient_value": [
                    {"raw": "14 g"},
                    {"raw": "16 g"},
                    {"raw": "162 kJ"},
                ],
            }
        }
        bounding_box = [0.1, 0.1, 0.2, 0.2]
        crop_score = 0.9
        nutrition_table_predictions = [
            {"bounding_box": bounding_box, "score": crop_score}
        ]
        # we have 5 nutrient mentions, 3 nutrient values (including 1 energy
        # value): we generate a candidate
        insights = list(
            NutritionImageImporter.generate_candidates_for_image(
                nutrient_mention_prediction,
                image_orientation_prediction,
                nutrition_table_predictions=nutrition_table_predictions,
            )
        )
        assert len(insights) == 1
        insight = insights[0]
        assert insight.barcode == DEFAULT_BARCODE
        assert insight.server_type == DEFAULT_SERVER_TYPE.name
        assert insight.value_tag == "fr"
        assert insight.automatic_processing is True
        assert insight.source_image == DEFAULT_SOURCE_IMAGE
        assert insight.data.get("from_prediction_ids") == {"nutrient_mention": 2}
        assert insight.data.get("rotation") == 90
        assert set(insight.data.get("nutrients", [])) == {
            "salt",
            "sugar",
            "carbohydrate",
            "protein",
            "saturated_fat",
        }
        assert insight.data["crop_score"] == crop_score
        assert insight.data["bounding_box"] == bounding_box

    def test_generate_candidates(self):
        barcode = "000000000000"
        source_image = "/000/000/000/0000/1.jpg"

        nutrient_mention_prediction = Prediction(
            type=PredictionType.nutrient_mention,
            barcode=barcode,
            source_image=source_image,
        )
        image_orientation_prediction = Prediction(
            type=PredictionType.image_orientation,
            barcode=barcode,
            source_image=source_image,
        )

        class FakeNutritionImageImporter(NutritionImageImporter):
            @classmethod
            def get_nutrition_table_predictions(
                cls, product_id: ProductIdentifier, min_score: float
            ):
                return {}

            @classmethod
            def generate_candidates_for_image(
                cls,
                nutrient_mention_prediction: Prediction,
                image_orientation_prediction: Prediction,
                nutrient_prediction: Optional[Prediction] = None,
                nutrition_table_predictions: Optional[list[JSONType]] = None,
            ) -> Iterator[ProductInsight]:
                assert nutrient_mention_prediction.source_image == source_image
                assert image_orientation_prediction.source_image == source_image
                assert nutrient_prediction is None
                assert nutrition_table_predictions is None
                yield ProductInsight(
                    type=InsightType.nutrition_image,
                    value_tag="fr",
                    source_image=source_image,
                )

        # We predict a nutrition image for language 'fr' and it's the main
        # language of the product, so we expect a candidate to be generated
        selected = list(
            FakeNutritionImageImporter.generate_candidates(
                Product({"lang": "fr"}),
                [nutrient_mention_prediction, image_orientation_prediction],
                None,
            )
        )
        assert len(selected) == 1
        insight = selected[0]
        assert isinstance(insight, ProductInsight)
        assert insight.value_tag == "fr"
        assert insight.type == InsightType.nutrition_image
        assert insight.source_image == source_image

        # We predict a nutrition image for language 'fr' but the main language
        # of the product is 'en', so we expect that no candidate is generated
        assert (
            list(
                FakeNutritionImageImporter.generate_candidates(
                    Product({"lang": "en"}),
                    [nutrient_mention_prediction, image_orientation_prediction],
                    None,
                )
            )
            == []
        )


class TestNutrientExtractionImporter:
    def test_generate_candidates_no_nutrient(self):
        product = Product({"code": DEFAULT_BARCODE, "nutriments": {}})
        data = {
            "nutrients": {
                "energy-kj_100g": {
                    "entity": "energy-kj_100g",
                    "value": "100",
                    "unit": "kj",
                    "text": "100 kj",
                    "start": 0,
                    "end": 1,
                    "char_start": 0,
                    "char_end": 6,
                }
            }
        }
        predictions = [
            Prediction(
                type=PredictionType.nutrient_extraction,
                data=data,
                barcode=DEFAULT_BARCODE,
                source_image=DEFAULT_SOURCE_IMAGE,
                predictor="nutrition_extractor",
                predictor_version="nutrition_extractor-1.0",
                automatic_processing=False,
            )
        ]
        candidates = list(
            NutrientExtractionImporter.generate_candidates(
                product, predictions, DEFAULT_PRODUCT_ID
            )
        )
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.type == "nutrient_extraction"
        assert candidate.barcode == DEFAULT_BARCODE
        assert candidate.type == InsightType.nutrient_extraction.name
        assert candidate.value_tag is None
        assert candidate.data == data
        assert candidate.source_image == DEFAULT_SOURCE_IMAGE
        assert candidate.automatic_processing is False
        assert candidate.predictor == "nutrition_extractor"
        assert candidate.predictor_version == "nutrition_extractor-1.0"

    def test_generate_candidates_no_new_nutrient(self):
        product = Product(
            {
                "code": DEFAULT_BARCODE,
                "nutriments": {
                    "energy-kj_100g": "100",
                    "energy-kj_unit": "kJ",
                    "fat_100g": "10",
                    "fat_unit": "g",
                },
            }
        )
        data = {
            "nutrients": {
                "energy-kj_100g": {
                    "entity": "energy-kj_100g",
                    "value": "100",
                    "unit": "kj",
                    "text": "100 kj",
                    "start": 0,
                    "end": 2,
                    "char_start": 0,
                    "char_end": 6,
                }
            }
        }
        predictions = [
            Prediction(
                type=PredictionType.nutrient_extraction,
                data=data,
                barcode=DEFAULT_BARCODE,
                source_image=DEFAULT_SOURCE_IMAGE,
                predictor="nutrition_extractor",
                predictor_version="nutrition_extractor-1.0",
                automatic_processing=False,
            )
        ]
        candidates = list(
            NutrientExtractionImporter.generate_candidates(
                product, predictions, DEFAULT_PRODUCT_ID
            )
        )
        assert len(candidates) == 0

    def test_generate_candidates_new_nutrient(self):
        product = Product(
            {
                "code": DEFAULT_BARCODE,
                "nutriments": {
                    "energy-kj_100g": "100",
                    "energy-kj_unit": "kJ",
                    "fat_100g": "10",
                    "fat_unit": "g",
                },
            }
        )
        data = {
            "nutrients": {
                "energy-kj_100g": {
                    "entity": "energy-kj_100g",
                    "value": "100",
                    "unit": "kj",
                    "text": "100 kj",
                    "start": 0,
                    "end": 2,
                    "char_start": 0,
                    "char_end": 6,
                },
                "saturated-fat_100g": {
                    "entity": "saturated-fat_100g",
                    "value": "5",
                    "unit": "g",
                    "text": "5 g",
                    "start": 3,
                    "end": 4,
                    "char_start": 7,
                    "char_end": 10,
                },
            }
        }
        predictions = [
            Prediction(
                type=PredictionType.nutrient_extraction,
                data=data,
                barcode=DEFAULT_BARCODE,
                source_image=DEFAULT_SOURCE_IMAGE,
                predictor="nutrition_extractor",
                predictor_version="nutrition_extractor-1.0",
                automatic_processing=False,
            )
        ]
        candidates = list(
            NutrientExtractionImporter.generate_candidates(
                product, predictions, DEFAULT_PRODUCT_ID
            )
        )
        assert len(candidates) == 1


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
            product_store=product_store,
            server_type=DEFAULT_SERVER_TYPE,
        )
        get_product_predictions_mock.assert_called_once()
        import_insights_mock.assert_not_called()

    def test_import_insights_single_product(self, mocker):
        prediction_dict = {
            "barcode": DEFAULT_BARCODE,
            "type": PredictionType.category.name,
            "data": {},
            "server_type": DEFAULT_SERVER_TYPE,
        }
        prediction = Prediction(
            barcode=DEFAULT_BARCODE,
            type=PredictionType.category,
            data={},
            server_type=DEFAULT_SERVER_TYPE,
        )
        get_product_predictions_mock = mocker.patch(
            "robotoff.insights.importer.get_product_predictions",
            return_value=[
                prediction_dict,
            ],
        )
        import_insights_mock = mocker.patch(
            "robotoff.insights.importer.InsightImporter.import_insights",
            return_value=ProductInsightImportResult(
                [], [], [], DEFAULT_PRODUCT_ID, InsightType.category
            ),
        )
        product_store = FakeProductStore()
        import_result = import_insights_for_products(
            {DEFAULT_BARCODE: {PredictionType.category}},
            product_store=product_store,
            server_type=DEFAULT_SERVER_TYPE,
        )
        assert len(import_result) == 1
        get_product_predictions_mock.assert_called_once()
        import_insights_mock.assert_called_once_with(
            DEFAULT_PRODUCT_ID, [prediction], product_store
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
            return_value=ProductInsightImportResult(
                [], [], [], DEFAULT_PRODUCT_ID, InsightType.image_orientation
            ),
        )
        product_store = FakeProductStore()
        import_results = import_insights_for_products(
            {DEFAULT_BARCODE: {PredictionType.image_orientation}},
            product_store=product_store,
            server_type=DEFAULT_SERVER_TYPE,
        )
        assert len(import_results) == 0
        assert not get_product_predictions_mock.called
        assert not import_insights_mock.called
