# Use the official Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /webapp

# Copy the local code to the container
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r packages.txt

# Streamlit runs on port 8501 by default, but Cloud Run expects applications to listen on port 8080.
# So we need to tell Streamlit to use port 8080.
ENV PORT 8081

# Use streamlit run command to run your app, adjusting the file name as necessary.
CMD ["streamlit", "run", "streamlit-client.py", "--server.port=8080", "--server.address=0.0.0.0"]
