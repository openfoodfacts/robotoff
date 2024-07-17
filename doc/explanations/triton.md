## Triton inference server

We use the [Triton Inference Server](https://github.com/triton-inference-server/) to serve ML models.

Models are exported in ONNX format (or SavedModel for some specific models trained with Tensorflow), and added in the `models/triton` directory.

Triton expects the models to be in a specific directory structure, with the model files in a subdirectory named after the model. For example, the model `my_model` should be in a directory named `my_model` in the `models/triton` directory.
Each model version should be in a subdirectory named after the version number, for example `1`.

Triton offers APIs in HTTP and gRPC. Robotoff uses the gRPC API to communicate with the server.

Triton possesses several model management mode, we use the 'explicit' mode. In this mode, the server does not load any model by default, and models must be explicitly loaded and unloaded by the client.
We ask Triton to load all the models in the `models/triton` directory at startup.

Using this mode, we don't have to restart the server when we add or remove models.

Once a new model directory is added, you can load it with the following command (within the triton container):
```bash
curl -X POST localhost:8000/v2/repository/models/${MODEL_NAME}/load
```