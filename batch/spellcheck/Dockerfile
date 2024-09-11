FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app
# Install dependencies before copying the rest of the code to leverage Docker cache
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py /app

# Set the entrypoint to the batch job script
ENTRYPOINT ["python", "main.py"]