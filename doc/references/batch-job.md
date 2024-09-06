# Google Batch Job

Robotoff primarily provides models to Open Food Facts with real-time inference using Nvidia Triton Inference on CPUs. 

However, this approach presents two major gaps:

* Challenges in processing large volumes of products during extended job runs
* Limited access to larger computing resources, such as GPUs or multi-CPU setups

To fill these gaps, we integrated a batch job feature into Robotoff, leveraging the capabilities of Google Cloud Platform.

## Architecture

![Robotoff Architecture](../assets/batch_job_robotoff.svg)


The batch job pipeline is structured as follow:

### 1. Launch job

The role of this command is to prepare and launch the job in the cloud. The launch depends on the type of job to perform, such as `ingredients-spellcheck`. Therefore, it takes as parameter `job_type`. 

Depending on the job type, the command will be responsible of:

* Generate the google credentials from the production environment variables, 
* Extracting, preparing and storing the data to process,
* Query the config file relative to the job and validate it using [Pydantic](https://docs.pydantic.dev/latest/),
* Launch the google batch job.

The command can be found as a Command `launch_batch_job` in the CLI directory[^launch_batch_job_cli].

### 2. Config files

The configuration file define the resources and setup allocated to the google batch job. Each batch job requires an unique configuration, stored as a YAML file[^config_files]. It contains:

* The resources location,
* The type and number of resources allocated,
* The maximal run duration,
* The number of tasks in parallele,
* The number of retries, ...

When initiating a job, the configuration is validated using the [Pydantic](https://docs.pydantic.dev/latest/) library. This process serves two purposes:

* Prevents errors that could potentially cause the pipeline to fail,
* Safeguards against the allocation of unnecessarily expensive resources.

For more information about Google Batch Job configuration, check the [official documentation](https://cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs).

### 3. The container registry

The container registry represents the core of the batch job. It contains the required dependencies and algorithms.

Docker images are maintained independently of the Robotoff micro-service [^dockerfile]. Each directory contains the files with their `Dockerfile`. Once built, the Docker image is pushed manually using the Make command written in the Makefile, such as `deploy-spellcheck`.

The container needs to be accessible from the batch job once launched. Can be used as registry:

* Google Artifact Registry within the project `Robotoff`,
* Docker hub,
* Public GitHub repository, such as [Robotoff](https://github.com/openfoodfacts/robotoff/tree/main).

### 4. Batch job

Once launched, the batch job goes throught different stages: SCHEDULED, QUEUED, RUNNING, SUCCEEDED, or FAILED. Each batch job is identified as the job type name associated with the launch `datetime`.

During the run, all logs are stored in the Batch Job logs file.

The list of batch jobs are located in the [Robotoff Google Batch Job](https://console.cloud.google.com/batch/jobs?referrer=search&project=robotoff).

### 5. Storage

If the batch job requires to import or export data, we use a storage feature such as Google Storage as an interface between Robotoff and the job running in the cloud.

If Google Storage is used, Google credentials are necessary on the Robotoff side. On the other side, since the Batch Job utilizes the default [service account](https://cloud.google.com/iam/docs/service-account-overview) associated with the project `Robotoff`, no additional setup is required.

### 6. Import processed data

Once the job is successfully finished, the Robotoff API endpoint is queried from the job run through with an HTTP request.

The role of this endpoint is to load the data processed by the batch job and import the new *predictions* to the Robotoff database. Check this [page](../explanations/predictions.md) to understand the process Robotoff used to transform raw *Predictions* into *Insights*.

Since this endpoint has only the vocation of importing the batch job results, it is secured with a `BATCH_JOB_KEY` from external requests. This secured endpoint follows a [Bearer Authentication](https://swagger.io/docs/specification/authentication/bearer-authentication/). The key is set as an environment variable in Robotoff and is defined as batch environment variable during a job launch.

Each batch job has its own method to import, or not, the results of the batch job.

## Roles

To launch a batch job and import its results, the following roles needs to be set up:

* **Artifact Registry Editor**: to push Docker Image to the project image registry
* **Batch Job Editor**
* **Service Account User**
* **Storage Admin**

For production, it is preferable to create a custom *Service account* with these roles.

## Additional notes

### Links

Check the official Google Batch Job documentation:

* [Batch Job](https://cloud.google.com/batch/docs/get-started),
* [Google Batch Job Python API](https://cloud.google.com/python/docs/reference/batch/latest),
* [Batch job with Python examples](https://github.com/GoogleCloudPlatform/python-docs-samples/tree/main/batch),


### Trials and errors notes

* Netherland (europe-west4) has GPUs (A100, L4)
* Add custom storage capacity to host the heavy docker image (~24GB) by adding `BootDisk`
* 1000 products processed: 1:30min (g2-instance-with 8) (overall batch job: 3:25min):
* L4: g2-instance-8 hourly cost: $0.896306 ==> ~ 0.05$ to process batch of 1000
* A100: a2-highgpu-1g: $3.748064
* A100/Cuda doesn't support FP8
* A100 has less availability than L4: need to wait for batch job (can be long) or switch to us-east location
* Don't forget to enable **Batch & Storage API** if used without gcloud ([link](https://cloud.google.com/batch/docs/get-started#project-prerequisites))


[^launch_batch_job_cli]: see `./robotoff/cli/main.py`
[^config_files]: see `./robotoff/batch/configs/job_configs`
[^dockerfile]: see `./batch/`