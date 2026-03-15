# Predictive Maintenance AI System

An enterprise-style **AI-powered predictive maintenance platform** for connected vehicles/fleets.  
It ingests telemetry, evaluates health in real time, predicts failures, estimates cost, auto-schedules service, analyzes driver behavior, and monitors security events.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Architecture Diagrams](#architecture-diagrams)
- [Data Flow](#data-flow)
- [AI/ML Flow](#aiml-flow)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Backend Modules](#backend-modules)
- [Frontend Modules](#frontend-modules)
- [How It Works](#how-it-works)
- [Database Design](#database-design)
- [Kafka / Redis / PostgreSQL Flow](#kafka--redis--postgresql-flow)
- [Authentication](#authentication)
- [Machine Learning Model](#machine-learning-model)
- [LangChain Agent Orchestration](#langchain-agent-orchestration)
- [Setup Instructions](#setup-instructions)
- [Run Locally](#run-locally)
- [Docker Infrastructure](#docker-infrastructure)
- [API Overview](#api-overview)
- [Real-Time Data Modes](#real-time-data-modes)
- [Screens / Demo Flow](#screens--demo-flow)
- [Future Enterprise Enhancements](#future-enterprise-enhancements)
- [License](#license)

---

## Overview

This project is a **fleet-scale predictive maintenance platform** that combines:

- **real-time vehicle telemetry**
- **machine learning failure prediction**
- **agentic orchestration**
- **cost estimation**
- **automatic appointment scheduling**
- **driver behavior intelligence**
- **security monitoring (UEBA)**

It supports both:
1. **historical seeded fleet data**
2. **real-time telemetry streaming** via API / simulator / dataset replay

---

## Key Features

- Real-time telemetry ingestion
- Predictive failure scoring with ML
- Diagnosis generation
- AI-based workflow orchestration
- Auto cost estimation
- Auto scheduling
- Driver behavior analytics
- RCA / CAPA feedback loop
- Kafka-based event stream
- Redis caching
- PostgreSQL persistence
- Clerk-based authentication
- Dashboard for fleet/OEM monitoring

---

## System Architecture

The platform is built around a **layered event-driven architecture**:

1. **Telemetry comes in**
2. **Gateway/API receives it**
3. **Kafka buffers it**
4. **Telemetry processor reads it**
5. **ML model assigns risk**
6. **Master Agent decides what to do**
7. **Workers do diagnosis, cost, scheduling, behavior**
8. **Frontend shows the result**

---

## Architecture Diagrams

### 1. High-Level System Architecture

```mermaid
flowchart TD
    A[Vehicle / Dataset / Simulator] --> B[Telemetry Gateway API]
    B --> C[Kafka Topic: vehicle-telemetry]
    C --> D[Kafka Consumer]
    D --> E[Telemetry Processor]
    E --> F[ML Risk Analyzer]
    F --> G[PostgreSQL]
    F --> H[Master Agent]

    H --> I[Diagnosis Agent]
    H --> J[Cost Agent]
    H --> K[Scheduling Agent]
    H --> L[Behavior Agent]
    H --> M[Feedback Agent]
    H --> N[UEBA Security Agent]

    G --> O[Dashboard API]
    O --> P[React Frontend Dashboard]

    E --> Q[Redis Cache]
    O --> Q
```

### 2. Agentic Workflow Architecture
```mermaid
flowchart LR
    A[Telemetry Event] --> B[Master Agent]
    B --> C[Diagnosis Agent]
    C --> D{Risk Level?}
    D -->|Low| E[Monitor Only]
    D -->|Medium| F[Create Diagnosis]
    D -->|High / Critical| G[Cost Agent]
    G --> H[Scheduling Agent]
    B --> I[Behavior Agent]
    B --> J[UEBA Agent]
    H --> K[Service Appointment]
    F --> L[Dashboard Update]
    I --> L
    J --> L
    K --> L
```

### 3. Event-Driven Pipeline
```mermaid
sequenceDiagram
    participant V as Vehicle/Source
    participant API as FastAPI Gateway
    participant K as Kafka
    participant C as Consumer
    participant P as Processor
    participant ML as ML Model
    participant DB as PostgreSQL
    participant FE as Frontend

    V->>API: POST /telemetry/ingest
    API->>K: Publish telemetry event
    K->>C: Consume message
    C->>P: Process telemetry
    P->>ML: Predict risk/failure
    ML-->>P: Risk score
    P->>DB: Store telemetry + health
    DB-->>FE: Dashboard data
```

### 4. Dashboard Data Flow
```mermaid
flowchart TD
    A[Frontend Dashboard] --> B[Dashboard API]
    B --> C[Vehicles Table]
    B --> D[Diagnoses Table]
    B --> E[Appointments Table]
    B --> F[Security Logs]
    B --> G[Telemetry Snapshots]
    C --> H[PostgreSQL]
    D --> H
    E --> H
    F --> H
    G --> H
    B --> I[Redis Cache]
```

### 5. Telemetry Risk Analysis Flow
```mermaid
flowchart TD
    A[Raw Telemetry] --> B[Validation]
    B --> C[Feature Extraction]
    C --> D[XGBoost / ML Model]
    C --> E[Rule-Based Threshold Checks]
    D --> F[Predicted Risk]
    E --> G[Detailed Risk Indicators]
    F --> H[Health Score]
    G --> H
    H --> I[Recommendations]
    I --> J[Alerts / Diagnosis / Scheduling]
```

### 6. Cost Estimation Flow
```mermaid
flowchart TD
    A[Diagnosis] --> B[Affected Components]
    B --> C[Parts Catalog Lookup]
    B --> D[Labor Rule Engine]
    C --> E[Parts Cost]
    D --> F[Labor Cost]
    E --> G[Warranty Coverage]
    F --> H[Tax + Misc]
    G --> I[Total Estimate]
    H --> I
    I --> J[Cost Estimate Record]
```

### 7. Security / UEBA Monitoring Flow
```mermaid
flowchart TD
    A[User Action / Agent Action] --> B[Security Log]
    B --> C[UEBA Agent]
    C --> D{Anomaly?}
    D -->|No| E[Allow]
    D -->|Yes| F[Create Alert]
    F --> G[Dashboard Security Panel]
    F --> H[Audit Trail]
```

### 8. Full Fleet Operational Flow
```mermaid
flowchart TD
    A[1000+ Fleet Vehicles] --> B[Real-Time Telemetry]
    B --> C[Kafka Stream]
    C --> D[Telemetry Consumer]
    D --> E[Telemetry Processor]
    E --> F[ML Risk Model]
    F --> G[Master Agent]
    G --> H[Diagnosis]
    G --> I[Cost Estimate]
    G --> J[Service Schedule]
    G --> K[Driver Behavior]
    G --> L[Security/UEBA]
    H --> M[Dashboard]
    I --> M
    J --> M
    K --> M
    L --> M
```

# Data Flow

Operational flow:

- Telemetry data arrives
- API validates payload
- Payload is pushed to Kafka
- Consumer reads from Kafka
- Telemetry processor stores and evaluates it
- ML model predicts health risk
- Master Agent triggers downstream workers
- Dashboard updates from DB/cache

---

# AI/ML Flow

### ML Layer

Model classifies telemetry into:

- Healthy
- Warning
- Critical

Algorithms used:

- **XGBoost**
- **Random Forest**

### Agent Layer

Master agent interprets ML results and dispatches tasks to:

- Diagnosis Agent
- Cost Agent
- Scheduling Agent
- Behavior Agent
- Security / UEBA Agent

---

# Tech Stack

## Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- AsyncPG
- PostgreSQL
- Redis
- Apache Kafka
- aiokafka

## AI / ML

- scikit-learn
- XGBoost
- Pandas
- NumPy
- LangChain
- OpenAI (optional)

## Frontend

- React
- Vite
- TailwindCSS
- Recharts
- Clerk Authentication
- Axios

## Infrastructure

- Docker
- Docker Compose

---

# Project Structure

```text
predictive-maintenance-system/

backend/
 ├ agents/
 ├ config/
 ├ data/
 ├ ml_models/
 ├ models/
 ├ routes/
 ├ services/
 ├ telemetry/
 ├ utils/
 ├ train_ml.py
 ├ train_gpu.py
 ├ seed_history.py
 ├ main.py
 └ requirements.txt

frontend/
 ├ src/
 ├ public/
 ├ package.json
 └ vite.config.js

docker-compose.yml
fleet_simulator.py
README.md
```

---

# How It Works

### Example Scenario

Vehicle telemetry:

```
engine temp = 121°C
oil level = 18%
brake wear = 82%
```

System actions:

1. Telemetry stored
2. ML predicts **critical failure risk**
3. Diagnosis agent detects **engine/oil issue**
4. Cost agent estimates service price
5. Scheduling agent books service slot
6. Dashboard updates automatically

---

# Database Design

Core tables:

- vehicles
- telemetry_data
- telemetry_snapshots
- diagnoses
- failure_predictions
- cost_estimates
- service_appointments
- driver_behaviors
- feedbacks
- security_logs
- ueba_alerts
- agent_audit_logs

---

# Setup Instructions

## Clone Repository

```bash
git clone https://github.com/samudragupto/predictive-maintenance-system.git
cd predictive-maintenance-system
```

---

## Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Frontend Setup

```bash
cd frontend
npm install
```

---

# Run Locally

### Start Backend

```bash
python -m backend.main
```

### Start Frontend

```bash
npm run dev
```

### Seed Historical Data

```bash
python backend/seed_history.py
```

### Train ML Model

```bash
python backend/train_ml.py
```

### Run Simulator

```bash
python fleet_simulator.py
```

---

# Docker Infrastructure

Start all services:

```bash
docker-compose up -d
```

Services started:

- PostgreSQL
- Redis
- Kafka
- Zookeeper
- Kafka UI

Kafka UI:

```
http://localhost:8081
```

---

# API Overview

Main endpoints:

```
/api/v1/vehicles
/api/v1/telemetry
/api/v1/diagnoses
/api/v1/cost-estimates
/api/v1/appointments
/api/v1/driver-behavior
/api/v1/feedback
/api/v1/agents
/api/v1/security
/api/v1/dashboard
```

API docs:

```
http://localhost:8000/docs
```

---

# Real-Time Data Modes

### Mode 1 — Historical Seeded Data

```
seed_history.py
```

### Mode 2 — Internal Real-Time Simulation

Background simulator tasks.

### Mode 3 — External Replay / IoT Feed

Sources:

- `fleet_simulator.py`
- dataset replay
- real IoT telemetry

---

# Future Enterprise Enhancements

- TimescaleDB telemetry hypertables
- Elasticsearch analytics
- Kubernetes deployment
- Alembic migrations
- RBAC / SSO
- WebSocket streaming
- Real OBD-II integration
- LSTM/Transformer failure forecasting
- Multi-region deployment
- Observability (Prometheus + Grafana)

---

# License

Specify your preferred license.

Example:

```
MIT License
```
