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


Overall File Structure as of 7.1.25 (Pre-PROD Push)

pos-ingestion/
├── .github/                       # Directory for GitHub Actions workflows (CI/CD)
│   └── workflows/
│       ├── deploy.yml             # Deploys application to Cloud Run on push to main
│       └── test.yml               # Runs tests automatically on pull requests
├── docs/                          # Project documentation and assets
│   └── images/
│       └── system-architecture.png # Visual diagram of the pipeline architecture
├── pos-poller/                    # Service to poll the POS API and publish events
│   ├── tests/
│   │   └── test_poller.py         # Unit and integration tests for the poller
│   ├── config.py                  # Configuration for poller endpoints and fields
│   ├── Dockerfile                 # Instructions to build the poller's container image
│   ├── main.py                    # Web server entry point (Flask) for the poller
│   ├── poller.py                  # Core logic for fetching and publishing data
│   ├── requirements.txt           # Python libraries required by the poller
│   └── utils.py                   # Helper functions (e.g., snake_case conversion)
├── pos-processor/                 # Service to consume events, validate, and load to BigQuery
│   ├── tests/
│   │   └── test_processor.py      # Unit and integration tests for the processor
│   ├── Dockerfile                 # Instructions to build the processor's container image
│   ├── main.py                    # Web server entry point (Flask) that receives Pub/Sub messages
│   ├── requirements.txt           # Python libraries required by the processor
│   └── schema_validator.py        # Core logic for loading schemas and validating data
├── schemas/                       # Single Source of Truth: All JSON Schema data contracts
│   ├── base_event.json           # Defines the common message envelope for all events
│   ├── checks.json                # Schema for the 'Checks' endpoint
│   ├── customers.json             # Schema for the 'Customers' endpoint
│   ├── item_sale_adjustments.json # Schema for the 'ItemSaleAdjustments' endpoint
│   ├── item_sale_components.json  # Schema for the 'ItemSaleComponents' endpoint
│   ├── item_sale_taxes.json       # Schema for the 'ItemSaleTaxes' endpoint
│   ├── item_sales.json            # Schema for the 'ItemSales' endpoint
│   ├── paidouts.json              # Schema for the 'Paidouts' endpoint
│   ├── payments.json              # Schema for the 'Payments' endpoint
│   └── time_records.json          # Schema for the 'TimeRecords' endpoint
├── terraform/                     # Infrastructure as Code (IaC) for all GCP resources
│   ├── backend.tf                 # Configures the GCS bucket for remote state storage
│   ├── bigquery.tf                # Defines the BigQuery dataset and all 9 tables
│   ├── iam.tf                     # Defines service accounts and their permissions
│   ├── pubsub.tf                  # Defines Pub/Sub topics, subscriptions, and the DLQ
│   ├── terraform.tfvars           # File to provide values for variables (e.g., project_id)
│   └── variables.tf               # Declares input variables for the Terraform configuration
├── .gitignore                     # Specifies files and folders for Git to ignore
├── capture_api_data.py            # Utility script for capturing raw API data during development
├── cloudbuild.yaml                # Defines the build process for Google Cloud Build
├── docker-compose.yml             # Orchestrates the entire local development environment
├── README.md                      # Main documentation for the project
└── setup_local_pubsub.sh          # Helper script to initialize the local Pub/Sub emulator

9 directories, 36 files