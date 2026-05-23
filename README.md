# HyperBlog - Extreme Performance Blog Platform

Welcome to **HyperBlog**, a state-of-the-art blog writing and reader web application built as an **educational & portfolio showcase project** to explore high-throughput scaling architectures capable of supporting up to **100,000 requests per second** (100k req/s).

> [!NOTE]
> **🎓 Learning & Showcase Project:**
> This repository was created as a hands-on learning project to master and demonstrate modern full-stack development, cloud-native architecture, and DevOps practices. It provides a practical exploration of asynchronous programming, distributed caching, database pooling, custom middlewares, Docker containerization, and Kubernetes orchestration.

This project features a **stunning, glassmorphic cyberpunk frontend** and a **highly optimized asynchronous FastAPI backend** backed by connection-pooled PostgreSQL and transparent Redis caching. It includes pre-configured **Docker** and **Kubernetes** manifests for complete containerization and horizontal scaling.

---

## 🧠 System Architecture & Engineering Concepts Learned

This project was built specifically to study, implement, and experiment with production-grade system architecture patterns. By analyzing and running this codebase, you can learn and practice:

*   **Asynchronous & Event-Driven I/O**: How to use Python's event loop via **FastAPI**, `async/await`, and asynchronous database/caching drivers to handle thousands of concurrent requests without blocking.
*   **Cache-Aside Pattern & Caching Strategies**: Utilizing an in-memory database (**Redis**) to reduce read latency to sub-millisecond levels (~1ms), and learning when and how to invalidate caches on new write events to prevent dirty reads.
*   **Database Connection Pooling**: How to warm up, manage, and scale active database connection sockets dynamically via SQLAlchemy to protect PostgreSQL from connection starvation during traffic surges.
*   **Sliding-Window Rate Limiting**: The design of high-throughput API rate limiters using atomic Redis scripts to prevent abuse and distribute throttling logic across horizontal pods.
*   **Containerization & DevOps Workflows**: Packaging applications into multi-stage, secure **Docker** containers and coordinating multi-container systems locally with **Docker Compose**.
*   **Orchestration & Horizontal Scaling**: Harnessing **Kubernetes** to deploy scalable systems, configuring load-balancing services, and implementing **Horizontal Pod Autoscalers (HPA)** to scale pods from 3 to 30 replicas automatically under heavy traffic.

---

## ⚡ High-Throughput System Architecture (100k req/s Design)

To handle extreme levels of concurrency, the application implements standard modern system design patterns:

```
                            [ Web Clients / Users ]
                                       │
                                       ▼
                       [ Nginx Ingress / Load Balancer ]
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
     [ Pod Replica: FastAPI ]                      [ Pod Replica: FastAPI ]
      ├─ Custom Async Rate Limiter                  ├─ Custom Async Rate Limiter
      ├─ In-Memory / Redis limit checking           ├─ In-Memory / Redis limit checking
      │                                             │
      ├─ (Read-Heavy Path: 99% hit)                 ├─ (Read-Heavy Path: 99% hit)
      │  [ Redis Cache ] ◄── < 1ms Latency ──►      │  [ Redis Cache ] ◄── < 1ms Latency ─
      │                                             │
      └─ (Write-Heavy Path: 1% hit)                 └─ (Write-Heavy Path: 1% hit)
         [ PostgreSQL Async DB Pool ]                  [ PostgreSQL Async DB Pool ]
```

### 1. Asynchronous, Non-Blocking Execution Flow
Python's default synchronous web servers block thread execution whenever a database query or I/O request is made. HyperBlog eliminates this by using **FastAPI** coupled with `async/await` syntax.
*   **Asynchronous Database Driver (`asyncpg`)**: Communication with PostgreSQL is completely non-blocking.
*   **Asynchronous Caching (`redis-py` async support)**: Interaction with Redis uses event-loop-driven connections.

### 2. High-Performance Multi-Tier Caching
Read requests (fetching blogs) constitute over 99% of typical blog traffic. Instead of hitting the database for every single read, HyperBlog implements a **Cache-Aside Pattern**:
1.  When a user fetches posts, the backend checks **Redis** first.
2.  If the cache hits (**Cache HIT**), the pre-serialized JSON is returned in under **1 millisecond** without hitting the database.
3.  If it misses (**Cache MISS**), PostgreSQL is queried, and the result is stored in Redis with a Time-To-Live (TTL) of 60 seconds.
4.  When a new blog post is written, the **cache is immediately invalidated** to ensure readers see fresh posts instantly.

### 3. Asynchronous Database Connection Pooling
Establishing database connections takes considerable CPU and network resources. HyperBlog uses SQLAlchemy's async engine configured with a connection pool:
*   `pool_size=50`: Keeps 50 connections warmed up and ready.
*   `max_overflow=100`: Allows the pool to temporarily burst to 150 connections during massive traffic spikes.
*   `pool_pre_ping=True`: Verifies connection health automatically before using it to prevent stale socket errors.

### 4. Sliding-Window Token Bucket Rate Throttling
To protect the backend from denial-of-service surges or client misbehavior, a custom **Asynchronous Rate Limiter** middleware is integrated.
*   Limits each IP address to **100 requests per second**.
*   Utilizes atomic Redis pipeline commands (`INCR` + `EXPIRE`) to enforce limits in distributed environments.
*   Automatically falls back to in-memory sliding-window tracking if Redis is offline.
*   Gracefully returns **HTTP 429 Too Many Requests** to throttled clients, protecting core system integrity.

### 5. Horizontal Pod Autoscaling (HPA) in Kubernetes
When traffic surges globally:
*   The Kubernetes **HorizontalPodAutoscaler (HPA)** monitors aggregate CPU load.
*   Once CPU utilization exceeds **70%**, K8s automatically scales the FastAPI application pods from a baseline of **3 replicas up to 30 replicas**.
*   Traffic is load-balanced across all active pods by the Kubernetes `Service` layer.

---

## 🎨 Premium Glassmorphic UI Dashboard

The frontend is a cyberpunk-themed Single Page Application (SPA) designed to feel responsive and alive:
*   **Operations & Telemetry Panel**: A visual control center showing live system stats (global throughput, active database connections, CPU/RAM levels, and replica counts).
*   **Interactive Simulation controls**:
    *   **Simulate Load Spike**: Artificially floods the system to demonstrate how Kubernetes scales and activates the rate limiter (physically trips the rate-limiter, returning live HTTP 429s).
    *   **Run Stress Test**: Performs parallel async requests in-browser, generating live latency metrics showing **Cache-driven read performance**.
*   **Modern CSS Styling**: Built with Outfit/Inter typography, deep dark-mode gradients, vibrant HSL variables, and GPU-accelerated micro-animations.

---

## 🚀 Quickstart & Setup Guide

### Option 1: Run Locally (Quickest Setup)

HyperBlog is designed with graceful fallbacks. If Redis and PostgreSQL are not running, it automatically uses **Async SQLite (`aiosqlite`)** and an **in-memory rate limiter/cache**.

1.  **Navigate to the project folder**:
    ```bash
    cd Apibuild
    ```
2.  **Create and activate a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r backend/requirements.txt
    ```
4.  **Launch the application**:
    ```bash
    uvicorn backend.main:app --reload
    ```
5.  **Access the Application**:
    *   Open your browser and navigate to: **`http://127.0.0.1:8000`**
    *   Access the interactive API documentation (Swagger) at: **`http://127.0.0.1:8000/docs`**

---

### Option 2: Run with Docker Compose (Full Stack)

This option spins up the entire production-grade stack including the FastAPI app container, a PostgreSQL database, and a Redis cluster cache.

1.  **Ensure your Docker Daemon is active**.
2.  **Run Docker Compose**:
    ```bash
    docker compose -f docker/docker-compose.yml up --build
    ```
3.  Docker will download Alpine base images, compile dependencies in a multi-stage container, set up volumes, run healthchecks, and expose the app at **`http://localhost:8000`**.
4.  To tear down:
    ```bash
    docker compose -f docker/docker-compose.yml down -v
    ```

---

### Option 3: Deploy to Kubernetes

Deploy the entire high-performance architecture into a local Kubernetes cluster (e.g. Docker Desktop, Minikube, or Kind).

1.  **Apply stateful database and caching layers**:
    ```bash
    kubectl apply -f kubernetes/postgres-deployment.yaml
    kubectl apply -f kubernetes/redis-deployment.yaml
    ```
2.  **Build your local docker image for the app**:
    ```bash
    docker build -t hyperblog:latest -f docker/Dockerfile .
    ```
    *(If using Minikube, point your terminal env to the minikube daemon first with `eval $(minikube docker-env)` before building).*
3.  **Deploy the application and auto-scalers**:
    ```bash
    kubectl apply -f kubernetes/app-deployment.yaml
    kubectl apply -f kubernetes/ingress.yaml
    ```
4.  **Verify that pods are scaling and healthy**:
    ```bash
    kubectl get pods -w
    kubectl get hpa
    ```

---

## 📊 Stress-Testing & Verification

1.  Open the dashboard in your browser.
2.  Click **"Run Stress Test"**: This sends 50 parallel asynchronous reads to the backend. The dashboard will print direct benchmark logs showing:
    *   *Average round-trip latency*: **< 2ms** (due to Redis caching).
    *   *Throughput performance*: Demonstrates single-threaded client speed.
3.  Click **"Simulate Load Spike (120k req/s)"**:
    *   Toggles the UI into surge mode.
    *   Triggers real-time HPA scaling and logging simulators showing cluster reactions.
    *   **Real rate limiting**: The browser fires 115 rapid-fire async calls in one second, immediately exceeding the 100 req/s IP threshold. The browser catches real **HTTP 429** responses and logs them directly!

---

## 🛠️ Tech Stack & Dependencies

*   **Backend framework**: FastAPI (ASGI asynchronous server)
*   **ASGI Web Server**: Uvicorn
*   **Database layer**: PostgreSQL (supported asynchronously via SQLAlchemy & `asyncpg` driver)
*   **Local Fallback**: SQLite (via `aiosqlite`)
*   **Caching & Throttling**: Redis (via `redis-py` async API)
*   **Validation**: Pydantic v2
*   **Frontend**: Vanilla HTML5, CSS3 Grid/Flexbox, dynamic Javascript ES6.
# scalable-api-architecture
