import operator
import pathlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

import h5py
import numpy as np
from PIL import Image

from efficientnet_pytorch import EfficientNet
import torch

import settings


class EmbeddingStore:
    def __init__(self, hdf5_path: pathlib.Path):
        self.hdf5_path = hdf5_path
        self.logo_id_to_idx: Dict[int, int] = self.load()
        self.offset = (
            max(self.logo_id_to_idx.values()) + 1 if self.logo_id_to_idx else 0
        )

    def __len__(self):
        return len(self.logo_id_to_idx)

    def __contains__(self, logo_id: int) -> bool:
        return self.get_index(logo_id) is not None

    def get_logo_ids(self) -> Iterable[int]:
        return self.logo_id_to_idx.keys()

    def get_index(self, logo_id: int) -> Optional[int]:
        return self.logo_id_to_idx.get(logo_id)

    def get_embedding(self, logo_id: int) -> Optional[np.ndarray]:
        idx = self.get_index(logo_id)

        if idx is None:
            return None

        if self.hdf5_path.is_file():
            with h5py.File(self.hdf5_path, "r") as f:
                embedding_dset = f["embedding"]
                return embedding_dset[idx]

        return None

    def load(self):
        if self.hdf5_path.is_file():
            with h5py.File(self.hdf5_path, "r") as f:
                external_id_dset = f["external_id"]
                array = external_id_dset[:]
                non_zero_indexes = np.flatnonzero(array)
                array = array[: non_zero_indexes[-1] + 1]
                return {int(x): i for i, x in enumerate(array)}

        return {}

    def iter_embeddings(self) -> Iterable[Tuple[int, np.ndarray]]:
        if not self.hdf5_path.is_file():
            return

        idx_logo_id = sorted(
            ((idx, logo_id) for logo_id, idx in self.logo_id_to_idx.items()),
            key=operator.itemgetter(0),
        )

        with h5py.File(self.hdf5_path, "r") as f:
            embedding_dset = f["embedding"]
            for idx, logo_id in idx_logo_id:
                embedding = embedding_dset[idx]
                yield logo_id, embedding

    def save_embeddings(
        self, embeddings: np.ndarray, external_ids: np.ndarray,
    ):
        file_exists = self.hdf5_path.is_file()

        with h5py.File(self.hdf5_path, "a") as f:
            if not file_exists:
                embedding_dset = f.create_dataset(
                    "embedding",
                    (settings.DEFAULT_HDF5_COUNT, embeddings.shape[-1]),
                    dtype="f",
                    chunks=True,
                )
                external_id_dset = f.create_dataset(
                    "external_id",
                    (settings.DEFAULT_HDF5_COUNT,),
                    dtype="i",
                    chunks=True,
                )
            else:
                embedding_dset = f["embedding"]
                external_id_dset = f["external_id"]

            slicing = slice(self.offset, self.offset + len(embeddings))
            embedding_dset[slicing] = embeddings
            external_id_dset[slicing] = external_ids

            for external_id, idx in zip(
                external_ids, range(self.offset, self.offset + len(embeddings))
            ):
                self.logo_id_to_idx[int(external_id)] = idx

            self.offset += len(embeddings)


EMBEDDING_STORE = EmbeddingStore(settings.EMBEDDINGS_HDF5_PATH)


def build_model(model_type: str):
    return EfficientNet.from_pretrained(model_type)


def generate_embeddings(model, images: np.ndarray, device: torch.device) -> np.ndarray:
    images = np.moveaxis(images, -1, 1)  # move channel dim to 1st dim

    with torch.no_grad():
        torch_images = torch.tensor(images, dtype=torch.float32, device=device)
        embeddings = model.extract_features(torch_images).cpu().numpy()

    return np.max(embeddings, (-1, -2))


def crop_image(
    image: Image.Image, bounding_box: Tuple[float, float, float, float]
) -> Image.Image:
    y_min, x_min, y_max, x_max = bounding_box
    (left, right, top, bottom) = (
        x_min * image.width,
        x_max * image.width,
        y_min * image.height,
        y_max * image.height,
    )
    return image.crop((left, top, right, bottom))


def get_embedding(logo_id: int) -> Optional[np.ndarray]:
    return EMBEDDING_STORE.get_embedding(logo_id)


def add_logos(
    image: Image.Image,
    external_ids: List[int],
    bounding_boxes: List[Tuple[float, float, float, float]],
    device: Optional[torch.device] = None,
) -> int:
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = ModelStore.get(settings.DEFAULT_MODEL, device)
    image_dim = settings.IMAGE_INPUT_DIM[settings.DEFAULT_MODEL]

    selected_external_ids = []
    selected_bounding_boxes = []

    for (bounding_box, external_id) in zip(bounding_boxes, external_ids):
        if external_id in EMBEDDING_STORE:
            continue

        selected_external_ids.append(external_id)
        selected_bounding_boxes.append(bounding_box)

    if not selected_bounding_boxes:
        return 0

    images = np.zeros((len(selected_bounding_boxes), image_dim, image_dim, 3))
    for i, bounding_box in enumerate(selected_bounding_boxes):
        cropped_image = crop_image(image, bounding_box)
        cropped_image = cropped_image.resize((image_dim, image_dim))
        images[i] = np.array(cropped_image)

    embeddings = generate_embeddings(model, images, device)
    EMBEDDING_STORE.save_embeddings(
        embeddings, np.array(selected_external_ids, dtype="i")
    )
    return len(embeddings)


class ModelStore:
    store: Dict[str, Any] = {}

    @classmethod
    def get(cls, model_name: str, device: torch.device):
        if model_name not in cls.store:
            model = build_model(model_name)
            model = model.to(device)
            cls.store[model_name] = model

        return cls.store[model_name]
