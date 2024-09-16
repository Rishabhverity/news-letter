FROM python:3.10-alpine

# Set the working directory
WORKDIR /app

# Copy all application files to the container
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Command to run the application with gunicorn
CMD ["gunicorn --bind 0.0.0.0:5000 wsgi:app"]