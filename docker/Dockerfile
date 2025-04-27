FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the docker folder into the container
COPY ./requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code from the project root
COPY . .

# Expose the port that the application will run on
EXPOSE 8000

# Set environment variable with default port
ENV PORT=8000

# Define the command to run the app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
