# Use the official Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy all files from the current directory to /app in the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the FastAPI app using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
