FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Install system dependencies
# Added: libtsk-dev (Sleuthkit), libafflib-dev, libsqlite3-dev as per your guide
RUN apt-get update && apt-get install -y \
    build-essential \
    autoconf automake libtool pkg-config \
    git flex bison \
    libssl-dev \
    libtsk-dev \
    libafflib-dev \
    libsqlite3-dev \
    libre2-dev libabsl-dev \
    libewf-dev libexiv2-dev \
    zlib1g-dev libexpat1-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Build C++ Tools
WORKDIR /mdp/external_programs
RUN git clone https://github.com/userhubsi/bulk_extractor_scanners.git
WORKDIR /mdp/external_programs/bulk_extractor_scanners

# a) Clone bulk_extractor
# b) Patch it with local plugins
# c) Compile and install
RUN make all
RUN cp bulk_extractor/src/bulk_extractor ..
RUN make clean_src

# 3. Setup mdp
WORKDIR /mdp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PATH="/mdp/external_programs/bulk_extractor/src:${PATH}"
ENTRYPOINT ["python", "/mdp/mdp.py"]
CMD ["--help"]
