# Triton inference server

We use the [Triton Inference Server](https://github.com/triton-inference-server/) to serve ML models.
A CLI is available to easily manage models (add new model, load/unload, enable/disable). For further information on how Triton manages model we refer the reader to the [last section](#reference-on-triton-model-management--configuration).


## Triton deployment

Triton can be run directly on the same server as Robotoff, but in production it runs on a distinct server with GPUs (server `gpu-01`, deployed on Google Cloud). 

To deploy Triton on a distinct server, go to `models`, where you will find a `docker-compose.yml` file to run the Triton server in a Docker container:

```bash
cd models
docker-compose up -d
```

For local development, you can also run Triton on your local machine with Docker. Simply make sure that you `docker/ml.yml` is part of your COMPOSE_FILE envvar in your `.env` (ex: `COMPOSE_FILE=docker-compose.yml;docker/dev.yml;docker/ml.yml`).


## Triton model management

A script `manage.py` can be found in the `models` directory to help manage models on the Triton server. It can be used to download, list, load, and unload models.

The easiest way to launch the script is using [uv](https://docs.astral.sh/uv/).

### Downloading models

To download all models, run:

```bash
uv run manage.py download-models
```

It downloads all models defined in the `models/models.toml` file and store them in the `models/triton` directory.

If you need to download a specific model (and ignore the remaining models defined in the toml file), you can provide its name with the `--include` option:

```bash
uv run manage.py download-models --include MODEL_NAME
```

### Copying configuration files

Triton can generate automatically a configuration file for ONNX model, but we have custom configuration files as it allows us to have more control over the model behavior.

Configuration files are stored in the `models/triton-config` directory. To copy them to the `models/triton` directory, run:

```bash
uv run manage.py copy-config
```

By default, it copies the GPU configuration files. If you're running on CPU, use the `--cpu` option.

Once the configuration files are copied, you can restart the Triton server:

```bash
docker compose restart triton
```

Make sure to check the logs to ensure that the models are loaded correctly:

```bash
docker compose logs -f triton
```

### Listing models

To list the models currently loaded on the Triton server, run:

```bash
uv run manage.py list-models
```

Make sure that the Triton server is running before executing this command.


### Loading and unloading models

All models present in the `models/triton` directory are loaded at Triton startup. If you add a new model, you don't need to restart the server, you can load it dynamically.

Use the following command to load a model:

```bash
uv run manage.py load-model --model MODEL_NAME
```

You can unload a model with the following command:
```bash
uv run manage.py unload-model --model MODEL_NAME
```

### Disabling models

When you work locally, you don't always want to load all models, as it can take a lot of RAM. You can disable a model by using the following command:

```bash
uv run manage.py disable-model --model MODEL_NAME
```

This command moves the model directory from `models/triton` to `models/triton-disabled`.

You can re-enable a model by moving it back:

```bash
uv run manage.py enable-model --model MODEL_NAME
```

### Get a model configuration from Triton

You can get the configuration of a model currently loaded in Triton with the following command:

```bash
uv run manage.py get-model-config --model MODEL_NAME
```

This command retrieves the model configuration from the Triton server and displays it in the console.


## Reference on Triton model management & configuration

Models are exported in ONNX format and added in the `models/triton` directory.

Triton expects the models to be in a specific directory structure, with the model files in a subdirectory named after the model. For example, the model `my_model` should be in a directory named `my_model` in the `models/triton` directory.
Each model version should be in a subdirectory named after the version number, for example `1`.

Triton offers APIs in HTTP and gRPC. Robotoff uses the gRPC API to communicate with the server.

Triton possesses several model management mode, we use the 'explicit' mode. In this mode, the server does not load any model by default, and models must be explicitly loaded and unloaded by the client.
We ask Triton to load all the models in the `models/triton` directory at startup.

Using this mode, we don't have to restart the server when we add or remove models.
