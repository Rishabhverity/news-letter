FROM python:3.8
WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "news_letter.py"]

# Use a lightweight Python image
# FROM python:3.10-slim

# # Set working directory
# WORKDIR /app

# # Install dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# # Expose the application port
# EXPOSE 5000

# # Start the application using Gunicorn
# CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "news_letter:app"]
