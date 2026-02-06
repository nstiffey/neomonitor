# 1. Use a lightweight Python image
FROM python:3.11-slim

# 2. Set the directory inside the container
WORKDIR /app

# 3. Copy the requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of the code
COPY . .

# 5. Command to run the service
CMD ["python", "app.py"]