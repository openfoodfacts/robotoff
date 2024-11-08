"Functions to postprocess the database conversion into Parquet."

import json
from typing import Iterator

import pyarrow as pa
import pyarrow.parquet as pq


################
# Schemas
################
## Images field
_size_schema = pa.struct(
    [
        pa.field("h", pa.int32(), nullable=True),
        pa.field("w", pa.int32(), nullable=True),
    ]
)

_dict_schema = pa.struct(
    [
        pa.field("key", pa.string(), nullable=True),
        pa.field("imgid", pa.string(), nullable=True),
        pa.field(
            "sizes",
            pa.struct(
                [
                    pa.field("100", _size_schema, nullable=True),
                    pa.field("200", _size_schema, nullable=True),
                    pa.field("400", _size_schema, nullable=True),
                    pa.field("full", _size_schema, nullable=True),
                ]
            ),
            nullable=True,
        ),
        pa.field("uploaded_t", pa.string(), nullable=True),
        pa.field("uploader", pa.string(), nullable=True),
    ]
)

IMAGES_DATATYPE = pa.list_(_dict_schema)


################
# Functions
################
def sink_to_parquet(path: str, batches: pa.RecordBatchReader):
    schema = batches.schema
    schema = schema.remove(schema.get_field_index("images"))
    schema = schema.append(pa.field("images", IMAGES_DATATYPE))
    with pq.ParquetWriter(path, schema=schema) as writer:
        for batch in batches:
            batch = batches.read_next_batch()
            batch = _postprocess_arrow_batch(batch)
            # batch = _postprocess_arrow_batch(batch)
            writer.write_batch(batch)


def postprocess_arrow_batches(batches: pa.RecordBatchReader) -> pa.RecordBatchReader:

    return pa.RecordBatchReader.from_batches(
        schema=batches.schema,
        batches=[_postprocess_arrow_batch(batch) for batch in batches]
    )


def _postprocess_arrow_batch(batch: pa.RecordBatch) -> pa.RecordBatch:
    batch = _postprocess_images(batch)
    return batch


def _postprocess_images(
        batch: pa.RecordBatch, 
        datatype: pa.DataType = IMAGES_DATATYPE
    ):
    postprocessed_images = []
    images: list[dict | None] = [
        json.loads(image) if image else None for image in batch["images"].to_pylist()
    ]
    for image in images:
        if image:
            postprocessed_images.append(
                [
                    {
                        "key": key,
                        "imgid": str(value.get("imgid", "unknown")),
                        "sizes": {
                            "100": {
                                "h": value.get("sizes", {}).get("100", {}).get("h", 0),
                                "w": value.get("sizes", {}).get("100", {}).get("w", 0),
                            },
                            "200": {
                                "h": value.get("sizes", {}).get("200", {}).get("h", 0),
                                "w": value.get("sizes", {}).get("200", {}).get("w", 0),
                            },
                            "400": {
                                "h": value.get("sizes", {}).get("400", {}).get("h", 0),
                                "w": value.get("sizes", {}).get("400", {}).get("w", 0),
                            },
                            "full": {
                                "h": value.get("sizes", {}).get("full", {}).get("h", 0),
                                "w": value.get("sizes", {}).get("full", {}).get("w", 0),
                            },
                        },
                        "uploaded_t": str(value.get("uploaded_t", "unknown")),
                        "uploader": str(value.get("uploader", "unknown")),
                    }
                    for key, value in image.items()
                ]
            )
        else:
            postprocessed_images.append([])
    images_array = pa.array(postprocessed_images, type=datatype)
    batch = batch.set_column(1, "images", images_array)
    return batch
