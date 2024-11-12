"Functions to postprocess the database conversion into Parquet."

import json

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


IMAGES_DATATYPE = pa.list_(
    pa.struct(
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
)

SCHEMAS = {"images": IMAGES_DATATYPE}


################
# Functions
################
def sink_to_parquet(parquet_path: str, output_path: str):
    parquet_file = pq.ParquetFile(parquet_path)
    updated_schema = update_schema(parquet_file.schema.to_arrow_schema())
    with pq.ParquetWriter(output_path, schema=updated_schema) as writer:
        for batch in parquet_file.iter_batches(batch_size=1000):
            batch = _postprocess_arrow_batch(batch)
            writer.write_batch(batch)


# def postprocess_arrow_batches(batches: pa.RecordBatchReader) -> pa.RecordBatchReader:
#     schema = _udpate_schema_by_field(
#         schema=batches.schema,
#         field_name="images",
#         field_datatype=IMAGES_DATATYPE,
#     )
#     batches = [_postprocess_arrow_batch(batch) for batch in batches]
#     return pa.RecordBatchReader.from_batches(
#         schema=schema,
#         batches=batches,
#     )


def _postprocess_arrow_batch(batch: pa.RecordBatch) -> pa.RecordBatch:
    batch = _postprocess_images(batch)
    return batch


def _postprocess_images(batch: pa.RecordBatch, datatype: pa.DataType = IMAGES_DATATYPE):
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
    images_col_index = batch.schema.get_field_index("images")
    batch = batch.set_column(
        images_col_index,
        pa.field("images", datatype),
        pa.array(postprocessed_images, type=datatype)
    )
    return batch


def update_schema(schema: pa.Schema) -> pa.Schema:
    for field_name, field_datatype in SCHEMAS.items():
        schema = _udpate_schema_by_field(
            schema=schema, field_name=field_name, field_datatype=field_datatype
        )
    return schema


def _udpate_schema_by_field(
    schema: pa.Schema, field_name: str, field_datatype: pa.DataType
) -> pa.schema:
    field_index = schema.get_field_index(field_name)
    schema = schema.remove(field_index)
    schema = schema.insert(field_index, pa.field(field_name, field_datatype))
    return schema
