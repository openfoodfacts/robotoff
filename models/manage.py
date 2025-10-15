"""This script is used to manage models for Triton Inference Server.

It acts as a standalone CLI tool, independent of Robotoff.

Currently, it can:
- download models from Hugging Face Hub according to a configuration file
- copy Triton configuration files for the models
- enable/disable models by moving their directory to a `triton-disabled/` directory
- load/unload models in/from Triton Inference Server
- list models loaded in Triton Inference Server
"""

# /// script
# dependencies = [
#  "openfoodfacts==3.1.0",
#  "typer==0.19.2",
#  "huggingface-hub==0.35.3",
#  "tritonclient[http]==2.61.0",
# ]
# ///

import json
import logging
import shutil
import tempfile
import tomllib
import typing
from pathlib import Path
from typing import Annotated, Literal, Optional

import typer
from huggingface_hub import snapshot_download
from openfoodfacts.types import JSONType
from pydantic import BaseModel, model_validator
from tritonclient.http import InferenceServerClient

app = typer.Typer()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.absolute()
TRITON_MODELS_DIR = BASE_DIR / "triton"
TRITON_CONFIG_DIR = BASE_DIR / "triton-config"
TRITON_DISABLED_MODELS_DIR = BASE_DIR / "triton-disabled"

TRITON_URL_PARAM = Annotated[
    str,
    typer.Option(
        help="URL of the Triton server (HTTP)",
    ),
]
TRITON_URL_DEFAULT = "localhost:5503"


class HuggingFaceModel(BaseModel):
    # Name of the model, used as the Triton model name
    # By default, this is the key in the `models` field of the `models.toml` file,
    # but it can be overridden with the `name` field as well.
    name: str
    # Triton model version, used to store the model in a subdirectory named after the
    # version
    triton_version: int
    # Hugging Face repository ID, ex: "openfoodfacts/keras-image-embeddings-3.0"
    repo_id: str
    # We currently support two type of download:
    # - "single_file": the model is a single file in the repository
    # - "directory": the model is a directory in the repository
    type: Literal["single_file", "directory"] = "single_file"
    # The subfolder in the repo where the model is located
    # This is ignored if type is not "directory"
    subfolder: str | None = None
    # Path to the model file if type is "single_file"
    # It is ignored if type is "directory"
    model_path: str | None = None
    # Name if the directory containing the model when type is "directory"
    # or of the file when type is "single_file"
    # By default, we assume the model file/directory is named "model.onnx"
    # For Tensorflow SavedModel, it should be "model.savedmodel"
    local_name: str = "model.onnx"
    # Git revision (branch, tag, commit hash), defaults to "main"
    # It's recommended to use a tag or a commit hash to ensure reproducibility
    revision: str = "main"

    # Add a validation that checks that model_path is set if type is "single_file"
    # and that subfolder is set if type is "directory"
    @model_validator(mode="after")
    def check_type_constraints(self):
        if self.type == "single_file" and not self.model_path:
            raise ValueError("model_path must be set if type is 'single_file'")
        if self.type == "directory" and not self.subfolder:
            raise ValueError("subfolder must be set if type is 'directory'")
        return self


def _list_models(client: InferenceServerClient) -> list[JSONType]:
    return client.get_model_repository_index()


@app.command()
def list_models(
    triton_url: TRITON_URL_PARAM = TRITON_URL_DEFAULT,
):
    """List all models loaded in Triton Inference Server."""
    client = InferenceServerClient(url=triton_url)
    models = _list_models(client)

    for model in models:
        typer.echo(
            f"{model['name']} (version: {model['version']}), state: {model['state']}"
        )


def model_metadata_has_changed(
    model_to_download: HuggingFaceModel, metadata_path: Path
) -> bool:
    if not metadata_path.exists():
        logger.warning(f"Model metadata file {metadata_path} does not exist")
        return True

    with metadata_path.open("r") as f:
        current_model = HuggingFaceModel.model_validate(json.load(f))

    if current_model != model_to_download:
        logger.info(
            f"Model metadata has changed: {current_model} != {model_to_download}"
        )
        return True

    return False


def load_model_config(
    model_config_path: Path, include: Optional[list[str]]
) -> list[HuggingFaceModel]:
    models = []
    with model_config_path.open("rb") as f:
        toml_models = tomllib.load(f)["models"]

    for model_name, model_download_configs in toml_models.items():
        for version_config in model_download_configs:
            if "name" not in version_config:
                version_config["name"] = model_name
            model = HuggingFaceModel(**version_config)
            if include and model.name not in include:
                logger.info(f"Skipping model {model.name} (not in include list)")
                continue
            models.append(model)
    return models


@app.command()
def download_models(
    include: Annotated[
        Optional[list[str]],
        typer.Option(help="Only download models whose name are in this list."),
    ] = None,
    model_config_path: Path = TRITON_MODELS_DIR.parent / "models.toml",
    overwrite: Annotated[
        bool,
        typer.Option(help="Overwrite existing models.", is_flag=True),
    ] = False,
):
    """Downloading all models from Hugging Face Hub.

    The models are downloaded in the Triton models directory. If the model
    already exists, it is not downloaded.
    """
    from openfoodfacts.utils import get_logger

    get_logger()

    models = load_model_config(model_config_path, include)
    for model in models:
        logger.info(f"Processing model {model.name} version {model.triton_version}")
        base_model_dir = TRITON_MODELS_DIR / model.name
        base_model_dir.mkdir(parents=True, exist_ok=True)

        model_with_version_dir = base_model_dir / str(model.triton_version)

        if model.type == "directory":
            model_with_version_dir = model_with_version_dir / model.local_name

        if model_with_version_dir.exists() and bool(
            next(model_with_version_dir.iterdir(), None)
        ):
            logger.info(
                f"Model {model.name} version {model.triton_version} already exists"
            )
            metadata_path = model_with_version_dir / "model_meta.json"
            if model_metadata_has_changed(model, metadata_path):
                logger.info("Model metadata is different than on disk!")

                if not overwrite:
                    logger.info("Skipping download (use --overwrite to force it)")
                    continue
                else:
                    logger.info("Overwriting current model on disk")
                    shutil.rmtree(model_with_version_dir)
            else:
                continue

        with tempfile.TemporaryDirectory() as temp_dir_str:
            logger.info(f"Temporary cache directory: {temp_dir_str}")
            temp_dir = Path(temp_dir_str)

            if model.type == "single_file":
                model_path = Path(typing.cast(str, model.model_path))
                dst_filename = model.local_name
                snapshot_download(
                    repo_id=model.repo_id,
                    allow_patterns=[str(model_path)],
                    revision=model.revision,
                    local_dir=temp_dir,
                )
                model_with_version_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Copying model file to {model_with_version_dir}")
                shutil.move(
                    temp_dir / model_path, model_with_version_dir / dst_filename
                )

            elif model.type == "directory":
                model_subfolder = typing.cast(str, model.subfolder)
                snapshot_download(
                    repo_id=model.repo_id,
                    allow_patterns=[f"{model_subfolder}/*"],
                    revision=model.revision,
                    local_dir=temp_dir,
                )
                model_with_version_dir.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Copying model files to {model_with_version_dir}")
                shutil.move(temp_dir / model_subfolder, model_with_version_dir)

            metadata_path = model_with_version_dir / "model_meta.json"
            logger.info(f"Writing model metadata to {metadata_path}")
            with metadata_path.open("w") as f:
                json.dump(model.model_dump(), f, indent=2)


@app.command()
def copy_config(
    include: Annotated[
        Optional[list[str]],
        typer.Option(help="Only download models whose name are in this list."),
    ] = None,
    cpu: Annotated[
        bool,
        typer.Option(help="Use CPU configuration instead of GPU.", is_flag=True),
    ] = False,
    model_config_path: Path = TRITON_MODELS_DIR.parent / "models.toml",
    config_dir: Path = TRITON_CONFIG_DIR,
    overwrite: Annotated[
        bool,
        typer.Option(help="Overwrite existing config files.", is_flag=True),
    ] = False,
):
    """Copy the configuration files for the models.

    Triton configuration files are necessary for Triton to load the models.
    See the Triton documentation for more information:
    https://github.com/triton-inference-server/server/blob/main/docs/user_guide/model_configuration.md

    By default, we fetch the configuration from the `triton-config` directory, which is
    in the same location than this script.

    If the `--cpu` option is provided, we copy the CPU configuration files instead
    of the GPU ones.
    """

    from openfoodfacts.utils import get_logger

    src_config_name = "cpu.pbtxt" if cpu else "gpu.pbtxt"
    config_name = "config.pbtxt"

    get_logger()
    models = load_model_config(model_config_path, include)

    for model in models:
        model_dir = TRITON_MODELS_DIR / model.name
        if not model_dir.exists():
            logger.warning(f"Model directory {model_dir} does not exist, skipping")
            continue

        config_dst = model_dir / config_name
        if config_dst.exists():
            if overwrite:
                logger.info(f"Config file {config_dst} already exists, overwriting")
            else:
                logger.info(
                    f"Config file {config_dst} already exists, skipping. Use --overwrite to force it."
                )
                continue

        config_src = config_dir / model.name / src_config_name

        if not config_src.exists():
            logger.error(f"Config source file {config_src} does not exist, skipping")
            continue

        logger.info(f"Copying config file from {config_src} to {config_dst}")
        shutil.copy(config_src, config_dst)


def _load_model(
    client: InferenceServerClient,
    model_name: str,
    model_version: str | None = None,
) -> None:
    """Load a model in Triton Inference Server, by sending a load request to Triton.

    If the model was never loaded, it will be loaded with the default
    configuration generated by Triton.

    Otherwise, the behavior will depend on whether the `--model-version` option is
    provided:

    - If the option is provided, only the specified version will be loaded, the other
        versions will be unloaded.
    - If the option is not provided, the two latest versions will be loaded.

    :param triton_stub: gRPC stub for Triton Inference Server
    :param model_name: name of the model to load
    :param model_version: version of the model to load, defaults to None
    """
    current_models = _list_models(client)
    first_load = not any(
        model["name"] == model_name and model["state"] == "READY"
        for model in current_models
    )

    config = None
    if first_load:
        logger.info("First load of model")
    else:
        logger.info("Previous model already loaded")
        model_config = client.get_model_config(model_name, model_version=model_version)
        if model_version:
            logger.info(
                f"Model version specified, only loading that version ({model_version})"
            )
            version_policy: JSONType = {"specific": {"versions": [model_version]}}
        else:
            logger.info("No model version specified, loading 2 latest version")
            version_policy = {"latest": {"num_versions": 2}}

        config = json.dumps(
            {
                "input": model_config["input"],
                "output": model_config["output"],
                "versionPolicy": version_policy,
                "max_batch_size": model_config["maxBatchSize"],
                "backend": model_config["backend"],
                "platform": model_config["platform"],
            }
        )

    client.load_model(model_name, config=config)


@app.command()
def load_model(
    model_name: Annotated[str, typer.Argument(help="Name of the model to load.")],
    model_version: Annotated[
        str | None, typer.Option(help="Version of the model to load.")
    ] = None,
    triton_url: TRITON_URL_PARAM = TRITON_URL_DEFAULT,
):
    """Load a model in Triton Inference Server, by sending a load request to Triton.

    If the model was never loaded, it will be loaded with the default
    configuration generated by Triton.

    Otherwise, the behavior will depend on whether the `--model-version` option is
    provided:

    - If the option is provided, only the specified version will be loaded, the other
        versions will be unloaded.
    - If the option is not provided, the two latest versions will be loaded.
    """
    from openfoodfacts.utils import get_logger

    get_logger()

    typer.echo(f"Loading model {model_name}")
    typer.echo("** Current models (before) **")
    list_models()
    client = InferenceServerClient(url=triton_url)
    _load_model(client, model_name, model_version=model_version)
    typer.echo("Done.")
    typer.echo("**Current models (after) **")
    list_models()


@app.command()
def unload_model(
    model_name: Annotated[str, typer.Argument(help="Name of the model to unload.")],
    triton_url: TRITON_URL_PARAM = TRITON_URL_DEFAULT,
):
    """Unload all versions of a model from Triton Inference Server."""
    typer.echo(f"Unloading model {model_name}")
    client = InferenceServerClient(url=triton_url)
    client.unload_model(model_name=model_name)
    typer.echo("Done.")
    typer.echo("**Current models (after) **")
    list_models()


@app.command()
def get_model_config(
    model_name: Annotated[str, typer.Argument(help="Name of the model.")],
    model_version: Annotated[
        Optional[str],
        typer.Option(
            help="Version of the model to choose. "
            "If not specified, the Triton server will choose a model based "
            "on the model and internal policy."
        ),
    ] = None,
    triton_url: TRITON_URL_PARAM = TRITON_URL_DEFAULT,
    pretty: Annotated[
        bool,
        typer.Option(help="Pretty print the JSON output.", is_flag=True),
    ] = False,
):
    """Display the configuration of a model in Triton Inference Server."""
    typer.echo(f"Getting config for model {model_name}")
    client = InferenceServerClient(url=triton_url)
    config = client.get_model_config(model_name, model_version=model_version or "")

    if pretty:
        config = json.dumps(config, indent=2)
    typer.echo(config)


@app.command()
def disable_model(
    model_name: Annotated[str, typer.Argument(help="Name of the model to disable.")],
):
    """Disable a model by moving its directory from `triton/` to `triton-disabled/`.

    Triton will not load models in the `triton-disabled/` directory.
    This is useful to temporarily disable a model without deleting its files.

    To revert the operation, use the `enable-model` command.
    """
    disabled_model_dir = TRITON_DISABLED_MODELS_DIR / model_name
    if disabled_model_dir.exists():
        logger.error(f"Disabled model directory {disabled_model_dir} already exists")
        raise typer.Exit(code=1)

    model_dir = TRITON_MODELS_DIR / model_name
    if not model_dir.exists():
        logger.error(f"Model directory {model_dir} does not exist")
        raise typer.Exit(code=1)

    disabled_model_dir.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Moving model directory {model_dir} to {disabled_model_dir}")
    shutil.move(model_dir, disabled_model_dir)


@app.command()
def enable_model(
    model_name: Annotated[str, typer.Argument(help="Name of the model to enable.")],
):
    """Enable a model by moving its directory from `triton-disabled/` to `triton/`.

    This is the reverse operation of the `disable-model` command.
    """
    model_dir = TRITON_MODELS_DIR / model_name
    if model_dir.exists():
        logger.error(f"Model directory {model_dir} already exists")
        raise typer.Exit(code=1)

    disabled_model_dir = TRITON_DISABLED_MODELS_DIR / model_name
    if not disabled_model_dir.exists():
        logger.error(f"Disabled model directory {disabled_model_dir} does not exist")
        raise typer.Exit(code=1)

    model_dir.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Moving disabled model directory {disabled_model_dir} to {model_dir}")
    shutil.move(disabled_model_dir, model_dir)


if __name__ == "__main__":
    app()
