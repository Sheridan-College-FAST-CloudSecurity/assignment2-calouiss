# Installation and Setup

## Prerequisites

- Python 3.10+
- AWS CLI configured with access to Bedrock in `us-east-1`
- Docker Desktop (for bonus AgentCore deployment)

## Setup

1. Clone the repository and navigate to the project directory:

   ```bash
   cd scheduling-agent
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set AWS credentials as environment variables:

   ```bash
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_SESSION_TOKEN=your_token
   export AWS_DEFAULT_REGION=us-east-1
   ```

## Running the Notebook

1. Upload `experimentation.ipynb` and the `data/` folder to Google Colab
2. Add your AWS credentials to Colab Secrets
3. Run cells sequentially

## Running the FastAPI Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for the Swagger UI.

## Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Start a scheduling session
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{"student_profile": {...}, "thread_id": "test-001"}'

# Approve a semester
curl -X POST http://localhost:8000/approve \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "test-001", "decision": "approved"}'

# View history
curl http://localhost:8000/history/test-001
```

## Bonus: Docker and AgentCore

```bash
# Build the container
docker build -t scheduling-agent:latest .

# Run locally
docker run --rm -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  -e AWS_DEFAULT_REGION=us-east-1 \
  scheduling-agent:latest
```
