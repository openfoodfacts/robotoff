import abc
from typing import List, Optional
import yaml
import datetime
import re

from google.cloud import batch_v1
from pydantic import BaseModel, Field, ConfigDict

from robotoff import settings
from robotoff.types import BatchJobType
from robotoff.batch.types import BATCH_JOB_TYPE_TO_CONFIG_PATH


class GoogleBatchJobConfig(BaseModel):
    """Batch job configuration class."""
    # By default, extra fields are just ignored. We raise an error in case of extra fields.
    model_config: ConfigDict = {"extra": "forbid"}

    job_name: str = Field(
        description="The name of the job. It needs to be unique amongst exisiting batch job names.",
    )
    location: str = Field(
        pattern=r"^europe-west\d{1,2}$",
        description="The region in which the job will run. Regions that are available for Batch are listed on: https://cloud.google.com/compute/docs/gpus/gpu-regions-zones. We restrict to Europe-West for now.",
    )
    container_image_uri: str = Field(
        description="The URI of the container image to use for the job. SHould be a valid Image URI.",
    )
    entrypoint: Optional[str] = Field(
        default=None,
        description="The entrypoint for the container. If None, use default entrypoint.",
        examples=["python main.py"],
    )
    commands: List[str] = Field(
        default_factory=list,
        description="Commands to run in the container. If None, use default commands. Can be used to add arguments to the job script.",
        examples=[["--max_tokens", "1024"]],
    )
    cpu_milli: int = Field(
        default=1000,
        description="The number of CPU milliseconds to allocate to the job. 1000 corresponds to 1 CPU core.",
        ge=1000,
    )
    memory_mib: int = Field(
        default=8000,  # 8GB
        description="The amount of RAM in MiB to allocate to each CPU core.",
        le=64000,
    )
    boot_disk_mib: Optional[int] = Field(
        default=None,
        description="The size of the boot disk in MiB. It is deleted once the job finished. If None, no bootDisk is added.",
        le=200000,  # 200 GB
    )
    max_retry_count: int = Field(
        default=1,
        ge=1,
        description="The maximum number of times a task should be retried in case of failure.",
    )
    max_run_duration: str = Field(
        pattern=r"^\d{1,5}s$",
        default="3600s",
        description="The maximum duration of the job in seconds.",
    )
    task_count: str = Field(
        pattern=r"^\d+$",
        default="1",
        description="The number of tasks to run in the job.",
    )
    parallelism: str = Field(
        pattern=r"^\d+$",
        default="1",
        description="The number of tasks to run in parallel.",
    )
    machine_type: str = Field(
        description="The machine type to use for the job. Read more about machine types here: https://cloud.google.com/compute/docs/general-purpose-machines",
    )
    accelerators_type: str = Field(
        description="The type of accelerator to use for the job. Depends on the machine type. Read more about accelerators here: https://cloud.google.com/compute/docs/gpus",
    )
    accelerators_count: int = Field(
        ge=1,
        description="The number of accelerators to use for the job.",
    )
    install_gpu_drivers: bool = Field(
        default=True,
        description="Required if GPUs.",
    )

    @classmethod
    def init(cls, job_type: BatchJobType):
        """Initialize the class with the configuration file corresponding to the job type.

        :param job_type: Batch job type.
        :type job_type: BatchJobType
        """
        # Batch job name should respect a specific pattern, or returns an error
        pattern = "^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$"
        if not re.match(pattern, job_type.value):
            raise ValueError(f"Job name should respect the pattern: {pattern}. Current job name: {job_type.value}")
        
        # Generate unique id for the job
        unique_job_name = (
            job_type.value + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        )
        # Load config file from job_type
        config_path = BATCH_JOB_TYPE_TO_CONFIG_PATH[job_type]
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return cls(job_name=unique_job_name, **config)


class BatchJob(abc.ABC):
    """Abstract class to launch and manage batch jobs: Google, AWS, Azure, Triton..."""

    @staticmethod
    @abc.abstractmethod
    def launch_job() -> str:
        """Launch batch job."""
        pass


class GoogleBatchJob(BatchJob):
    """GCP Batch class. It uses the Google Cloud Batch API to launch and manage jobs.

    More information on:
    https://cloud.google.com/batch/docs/get-started
    """

    @staticmethod
    def launch_job(
        batch_job_config: GoogleBatchJobConfig,
    ) -> batch_v1.Job:
        """This method creates a Batch Job on GCP.

        Sources:
        * https://github.com/GoogleCloudPlatform/python-docs-samples/tree/main/batch/create
        * https://cloud.google.com/python/docs/reference/batch/latest/google.cloud.batch_v1.types
        
        :param google_batch_launch_config: Config to run a job on Google Batch.
        :type google_batch_launch_config: GoogleBatchLaunchConfig
        :param batch_job_config: Config to run a specific job on Google Batch.
        :type batch_job_config: BatchJobConfig
        :return: Batch job information.
        :rtype: batch_v1.Job

        Returns:
            Batch job information.
        """

        client = batch_v1.BatchServiceClient()

        # Define what will be done as part of the job.
        runnable = batch_v1.Runnable()
        runnable.container = batch_v1.Runnable.Container()
        runnable.container.image_uri = batch_job_config.container_image_uri
        runnable.container.entrypoint = batch_job_config.entrypoint
        runnable.container.commands = batch_job_config.commands

        # Jobs can be divided into tasks. In this case, we have only one task.
        task = batch_v1.TaskSpec()
        task.runnables = [runnable]

        # We can specify what resources are requested by each task.
        resources = batch_v1.ComputeResource()
        resources.cpu_milli = batch_job_config.cpu_milli
        resources.memory_mib = batch_job_config.memory_mib
        resources.boot_disk_mib = batch_job_config.boot_disk_mib
        task.compute_resource = resources

        task.max_retry_count = batch_job_config.max_retry_count
        task.max_run_duration = batch_job_config.max_run_duration

        # Tasks are grouped inside a job using TaskGroups.
        group = batch_v1.TaskGroup()
        group.task_count = batch_job_config.task_count
        group.task_spec = task

        # Policies are used to define on what kind of virtual machines the tasks will run on.
        policy = batch_v1.AllocationPolicy.InstancePolicy()
        policy.machine_type = batch_job_config.machine_type
        instances = batch_v1.AllocationPolicy.InstancePolicyOrTemplate()
        instances.install_gpu_drivers = batch_job_config.install_gpu_drivers
        instances.policy = policy
        allocation_policy = batch_v1.AllocationPolicy()
        allocation_policy.instances = [instances]

        accelerator = batch_v1.AllocationPolicy.Accelerator()
        accelerator.type_ = batch_job_config.accelerators_type
        accelerator.count = batch_job_config.accelerators_count

        job = batch_v1.Job()
        job.task_groups = [group]
        job.allocation_policy = allocation_policy
        # We use Cloud Logging as it's an out of the box available option
        job.logs_policy = batch_v1.LogsPolicy()
        job.logs_policy.destination = batch_v1.LogsPolicy.Destination.CLOUD_LOGGING

        create_request = batch_v1.CreateJobRequest()
        create_request.job = job
        create_request.job_id = batch_job_config.job_name
        # The job's parent is the region in which the job will run
        create_request.parent = f"projects/{settings.GOOGLE_PROJECT_NAME}/locations/{batch_job_config.location}"

        return client.create_job(create_request)
