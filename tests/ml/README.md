# Machine Learning integration tests

This directory contains tests that check that the machine learning models are working as expected.

As these tests rely on Triton server, they are not run by default.
It requires the Triton server to be running and the models to be loaded.

First, make sure that every Triton model is downloaded and is stored in the correct location in the `models` directory.

Then, run the tests:

```bash
make ml-tests
```

This command will start the Triton server and run the tests.
Outputs (predictions, pre-processing or post-processing outputs) are compared to reference outputs stored in the
[https://github.com/openfoodfacts/test-data/](https://github.com/openfoodfacts/test-data/) repository.

We use a distinct repository to store the reference outputs to avoid bloating the main repository with large files.
We use the Github raw URL of these files to download the reference outputs.

To update the reference outputs, run the tests with the `--update-results` flag and specify the output directory:

```bash
make ml-tests args='--update-results --output-dir /opt/robotoff/data/ml_tests'
```

This will store the outputs locally in `data/ml_tests`. You can then copy the files contained in the directory to the `test-data` repository and commit the changes.