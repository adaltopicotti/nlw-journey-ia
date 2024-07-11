# Use the AWS base image for Python 3.12
FROM public.ecr.aws/lambda/python:3.12

# Install build-essential complier tools
RUN microdnf update -y && microdnf install -y gcc-c++ make

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install packages
RUN pip install -r requirements.txt

# Copy function node
COPY travel_agent.py ${LAMBDA_TASK_ROOT}

# Set the permissions to make the file executable
RUN chmod +x travel_agent.py

# Set the CMD
CMD ["travel_agent.lambda_handler"]
