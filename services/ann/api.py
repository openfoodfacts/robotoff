import random
import pathlib
from typing import Dict, List, Optional

import annoy
import falcon
from falcon_cors import CORS
from falcon_multipart.middleware import MultipartMiddleware
import sentry_sdk
from sentry_sdk.integrations.falcon import FalconIntegration

from utils import get_logger, text_file_iter
import settings

logger = get_logger()

sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[FalconIntegration()])


def load_index(file_path: pathlib.Path, dimension: int) -> annoy.AnnoyIndex:
    index = annoy.AnnoyIndex(dimension, "euclidean")
    index.load(str(file_path), prefault=True)
    return index


def load_keys(file_path: pathlib.Path) -> List[int]:
    return [int(x) for x in text_file_iter(file_path)]


class ANNIndex:
    def __init__(self, index: annoy.AnnoyIndex, keys: List[int]):
        self.index = index
        self.keys = keys
        self.key_to_ann_id = {x: i for i, x in enumerate(self.keys)}

    @classmethod
    def load(cls, index_dir: pathlib.Path) -> "ANNIndex":
        dimension = settings.INDEX_DIM[index_dir.name]
        index = load_index(index_dir / settings.INDEX_FILE_NAME, dimension)
        keys = load_keys(index_dir / settings.KEYS_FILE_NAME)
        return cls(index, keys)


INDEXES: Dict[str, ANNIndex] = {
    index_dir.name: ANNIndex.load(index_dir)
    for index_dir in settings.DATA_DIR.iterdir()
    if index_dir.is_dir()
}


class ANNResource:
    def on_get(
        self, req: falcon.Request, resp: falcon.Response, logo_id: Optional[int] = None
    ):
        index_name = req.get_param("index", default=settings.DEFAULT_INDEX)

        if index_name not in INDEXES:
            raise falcon.HTTPBadRequest("unknown index: {}".format(index_name))

        ann_index = INDEXES[index_name]

        if logo_id is None:
            logo_id = ann_index.keys[random.randint(0, len(ann_index.keys) - 1)]

        elif logo_id not in ann_index.key_to_ann_id:
            resp.status = falcon.HTTP_404
            return

        count = req.get_param_as_int("count", min_value=1, max_value=500, default=100)
        item_index = ann_index.key_to_ann_id[logo_id]

        indexes, distances = ann_index.index.get_nns_by_item(
            item_index, count, include_distances=True
        )

        logo_ids = [ann_index.keys[index] for index in indexes]
        results = []

        for ann_logo_id, distance in zip(logo_ids, distances):
            results.append({"distance": distance, "logo_id": ann_logo_id})

        resp.media = {"results": results, "count": len(results)}


class ANNEmbeddingResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        index_name = req.get_param("index", default=settings.DEFAULT_INDEX)

        if index_name not in INDEXES:
            raise falcon.HTTPBadRequest("unknown index: {}".format(index_name))

        ann_index = INDEXES[index_name]

        count = req.media.get("count", 1)
        embedding = req.media["embedding"]

        if len(embedding) != settings.INDEX_DIM:
            raise falcon.HTTPBadRequest(
                "invalid dimension",
                "embedding must be of size {}, here: {}".format(
                    settings.INDEX_DIM, len(embedding)
                ),
            )

        indexes, distances = ann_index.index.get_nns_by_vector(
            embedding, count, include_distances=True
        )

        logo_ids = [ann_index.keys[index] for index in indexes]
        results = []

        for ann_logo_id, distance in zip(logo_ids, distances):
            results.append({"distance": distance, "logo_id": ann_logo_id})

        resp.media = {"results": results, "count": len(results)}


cors = CORS(
    allow_all_origins=True,
    allow_all_headers=True,
    allow_all_methods=True,
    allow_credentials_all_origins=True,
    max_age=600,
)

api = falcon.API(middleware=[cors.middleware, MultipartMiddleware()])

# Parse form parameters
api.req_options.auto_parse_form_urlencoded = True
api.req_options.strip_url_path_trailing_slash = True
api.req_options.auto_parse_qs_csv = True
api.add_route("/api/v1/ann/{logo_id:int}", ANNResource())
api.add_route("/api/v1/ann/random", ANNResource())
api.add_route("/api/v1/ann", ANNEmbeddingResource())
