

# FROM python:3.10-alpine

# RUN apk add --no-cache \
#     build-base \
#     libffi-dev \
#     musl-dev \
#     gcc \
#     g++ \
#     # make \
#     postgresql-dev \
#     tiff-dev \
#     tk-dev \
#     tcl-dev \
#     harfbuzz-dev \
#     fribidi-dev
# # Set the working directory
# WORKDIR /app

# # Copy all application files to the container
# COPY . .

# # Install dependencies
# # RUN pip install -r requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt
# # Command to run the application with gunicorn
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]


# FROM python:3.8-alpine

# # Set the working directory
# WORKDIR /app

# # Install system dependencies and required libraries
# RUN apk add --no-cache --virtual .build-deps \
#     build-base \
#     gcc \
#     musl-dev \
#     mariadb-dev \
#     python3-dev \
#     libffi-dev \
#     openssl-dev \
#     cargo \
#     make \
#     && apk add --no-cache libjpeg-turbo-dev zlib-dev

# # Copy all application files to the container
# COPY . .

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Remove build dependencies to keep the image small
# RUN apk del .build-deps

# # Expose the application port
# EXPOSE 5000

# # Command to run the application with gunicorn
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]


FROM python:3.10-alpine

# Set the working directory
WORKDIR /app

# Copy all application files to the container
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Command to run the application with gunicorn
CMD ["gunicorn --bind 0.0.0.0:5000 wsgi:app"]