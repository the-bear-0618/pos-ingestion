# POS Ingestion Pipeline

![Build Status](https://github.com/your-org/pos-ingestion/actions/workflows/test.yml/badge.svg)

This repository contains the complete data pipeline for ingesting Point of Sale (POS) data, validating it against formal data contracts, and loading it into Google BigQuery.

## 🏛️ Architecture Overview

The system is designed as a resilient, event-driven pipeline composed of two main microservices and managed Google Cloud infrastructure.

* **`pos-poller`**: A Python service that polls the third-party POS OData API on a schedule, performs minimal transformation (PascalCase to snake_case), and publishes each record as a distinct event to a Pub/Sub topic.
* **`pos-processor`**: A Python service that subscribes to the Pub/Sub topic. It validates each incoming event against a corresponding JSON Schema, and upon successful validation, inserts the clean data into the appropriate BigQuery table. Failed messages are routed to a Dead-Letter Queue (DLQ).

*(This is a great place to embed the `Comprehensive System Architecture` diagram you created!)*
```
![Comprehensive System Architecture Diagram] (/docs/images/Editor _ Mermaid Chart-2025-06-30-184011.png)
![Comprehensive System Architecture Diagram] (docs/images/Editor _ Mermaid Chart-2025-06-30-220559.png)
```

### Project Structure
```
pos-ingestion/
├── .github/              # GitHub Actions CI/CD Workflows
├── pos-poller/           # The data polling service
├── pos-processor/        # The schema validation and BigQuery insertion service
├── schemas/              # The Single Source of Truth: JSON Schema data contracts
├── terraform/            # Infrastructure as Code for all GCP resources
├── .gitignore            # Files and directories to ignore in version control
├── cloudbuild.yaml       # Secure container build definitions for GCP
├── docker-compose.yml    # Local development and testing environment
└── README.md             # This file
```

---

## 🚀 Getting Started

### Prerequisites

Ensure you have the following tools installed on your local machine:
* Git
* Docker & Docker Compose
* Google Cloud SDK (`gcloud`)
* Terraform

### Local Development Setup

This setup uses Docker Compose to run the entire pipeline locally, including a Pub/Sub emulator.

**1. Clone the Repository**
```bash
git clone [https://github.com/your-org/pos-ingestion.git](https://github.com/your-org/pos-ingestion.git)
cd pos-ingestion
```

**2. Configure Local Environment**
Create a `.env` file for local configuration. A template is provided.
```bash
cp .env.example .env
```
Now, **edit the `.env` file** with your local settings and POS API credentials.

**3. Run the Local Environment**
This single command will build the Docker images for the services and start the entire local pipeline.
```bash
docker-compose up --build
```
The services will be available:
* **Pub/Sub Emulator**: `localhost:8085`
* **pos-poller**: `localhost:8080`
* **pos-processor**: `localhost:8081`

**4. Set up Local Pub/Sub Topics**
The Pub/Sub emulator starts up empty. You need to create the topic, subscription, and DLQ. Run this script in a **new terminal window** after `docker-compose up` is running.

```bash
./setup_local_pubsub.sh
```

**5. Trigger a Data Sync**
You can now trigger the poller to fetch data by sending a POST request to its `/sync` endpoint.

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "days_back": 1,
    "endpoints": ["Checks", "ItemSales"]
  }' \
  http://localhost:8080/sync
```
You should see logs from both the `pos-poller` and `pos-processor` in your `docker-compose` terminal window.

---

## 🧪 Testing

This project uses `pytest`. To run all unit and integration tests for both services, execute the following command from the root directory:

```bash
pytest
```

---

## ☁️ Infrastructure Deployment

All GCP resources (BigQuery, Pub/Sub, IAM, etc.) are managed via Terraform.

1.  **Initialize Terraform**
    ```bash
    cd terraform
    terraform init
    ```

2.  **Plan the Deployment**
    Create a `terraform.tfvars` file to specify your project ID.
    ```
    gcp_project_id = "your-gcp-project-id"
    ```
    Then run the plan to see what resources will be created.
    ```bash
    terraform plan -var-file="terraform.tfvars"
    ```

3.  **Apply the Configuration**
    ```bash
    terraform apply -var-file="terraform.tfvars"
    ```

---

## CI/CD

This repository is configured with GitHub Actions for Continuous Integration and Deployment.

* **On Pull Request:** The `test.yml` workflow is triggered to run all `pytest` tests.
* **On Merge to `main`:** The `deploy.yml` workflow is triggered. It orchestrates the process of building the service images using Google Cloud Build and deploying them to Cloud Run.