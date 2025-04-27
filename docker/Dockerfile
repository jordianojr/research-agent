FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the docker folder into the container
COPY docker/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code from the project root
COPY . .

# Set environment variables
ENV PORT=8080

# Expose the port
EXPOSE ${PORT}

# Define the command to run the app with proper startup configuration
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "75"]
