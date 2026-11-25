FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends iverilog make g++ && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir cocotb==1.9.2 pytest==8.3.3
RUN useradd -u 10001 -m app
WORKDIR /dv
COPY . /dv
USER 10001
CMD ["python", "dv/regress.py"]
