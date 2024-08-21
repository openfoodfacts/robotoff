FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

COPY job.py /app
COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

# Set the entrypoint to the batch job script
ENTRYPOINT ["python", "main.py"]