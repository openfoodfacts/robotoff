import random
import pathlib
from typing import List, Optional

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


def load_index(file_path: pathlib.Path) -> annoy.AnnoyIndex:
    index = annoy.AnnoyIndex(settings.INDEX_DIM, "euclidean")
    index.load(str(file_path), prefault=True)
    return index


def load_keys(file_path: pathlib.Path) -> List[int]:
    return [int(x) for x in text_file_iter(file_path)]


INDEX = load_index(settings.INDEX_PATH)
KEYS = load_keys(settings.KEYS_PATH)
KEY_TO_ANN_ID = {x: i for i, x in enumerate(KEYS)}


class ANNResource:
    def on_get(
        self, req: falcon.Request, resp: falcon.Response, logo_id: Optional[int] = None
    ):
        if logo_id is None:
            logo_id = KEYS[random.randint(0, len(KEYS) - 1)]

        elif logo_id not in KEY_TO_ANN_ID:
            resp.status = falcon.HTTP_404
            return

        count = req.get_param_as_int("count", min_value=1, max_value=500, default=100)
        item_index = KEY_TO_ANN_ID[logo_id]

        indexes, distances = INDEX.get_nns_by_item(
            item_index, count, include_distances=True
        )

        logo_ids = [KEYS[index] for index in indexes]
        results = []

        for ann_logo_id, distance in zip(logo_ids, distances):
            results.append({"distance": distance, "logo_id": ann_logo_id})

        resp.media = {"results": results, "count": len(results)}


class ANNEmbeddingResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        count = req.media.get("count", 1)
        embedding = req.media["embedding"]

        if len(embedding) != settings.INDEX_DIM:
            raise falcon.HTTPBadRequest(
                "invalid dimension",
                "embedding must be of size {}, here: {}".format(
                    settings.INDEX_DIM, len(embedding)
                ),
            )

        indexes, distances = INDEX.get_nns_by_vector(
            embedding, count, include_distances=True
        )

        logo_ids = [KEYS[index] for index in indexes]
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
