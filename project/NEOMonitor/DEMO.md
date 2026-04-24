
NEO-Sentinel is a microservices-based system for monitoring and analyzing near-Earth objects (NEOs) using NASA's asteroid data. It provides real-time risk assessment, user watchlists, and a web dashboard for visualizing asteroid threats.

This guide explains set up and running 
---

## Prerequisites

Before running NEO-Sentinel, ensure you have the following installed on your system:

- **Docker**: Version 20.10 or later (includes Docker Compose)
  - Download from [docker.com](https://www.docker.com/get-started)
- **Git**: For cloning the repository


## Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd NEOMonitor
   ```

2. **Verify Docker Installation**
   ```bash
   docker --version
   docker-compose --version
   ```

---

## Setup and Running

1. **Start the System**
   ```bash
   docker-compose up --build
   ```
   - First run may take 5-10 minutes
   - Uses NASA's demo API key by default

**Expected Output:**
```
Creating network "neomonitor-network" with driver "bridge"
Creating neomonitor-postgresql-1 ...
Creating neomonitor-redis-1 ...
Creating neomonitor-asteroid-service-1 ...
Creating neomonitor-user-watchlist-1 ...
Creating neomonitor-risk-analysis-service-1 ...
Creating neomonitor-api-gateway-1 ...
Creating neomonitor-ui-dashboard-1 ...

api-gateway        | * Running on http://0.0.0.0:8000
asteroid-service   | * Running on http://0.0.0.0:5001
user-watchlist     | * Running on http://0.0.0.0:5002
risk-analysis-service | * Running on http://0.0.0.0:5003
ui-dashboard       | * Running on http://0.0.0.0:5000
postgresql         | database system is ready to accept connections
redis              | Ready to accept connections
```

---

## Accessing the Application

Once started, the system runs in the background. Services are accessible at:

- **Web Dashboard**: http://localhost:5000
  - Interactive UI for viewing asteroid risks
- **API Gateway**: http://localhost:8000
  - Main API endpoint for all services
- **Individual Services**:
  - Asteroid Service: http://localhost:5001
  - User Watchlist Service: http://localhost:5002
  - Risk Analysis Service: http://localhost:5003

### Using the Dashboard
1. Open http://localhost:5000 in your browser
2. Enter a distance threshold (e.g., 1000000 km)
3. Press Enter or click "Apply"
4. Optionally check "Show only potentially hazardous objects"
5. Click column headers to sort by Distance or Diameter

---

## Verification

Verify all services are running and healthy:

```
 http://localhost:8000/health
```

Expected Response:
```json
{
  "gateway": "healthy",
  "dependencies": {
    "asteroid-service": { "status": "healthy" },
    "user-watchlist": { "status": "healthy" },
    "risk-analysis-service": { "status": "healthy" },
    "ui-dashboard": { "status": "healthy" }
  }
}
```

---

## Stopping the Application

```bash
docker-compose down
```

# Specific service
docker-compose logs -f ui-dashboard


## Troubleshooting

### Services Won't Start
```bash
# Check Docker status
docker ps

# View detailed logs
docker-compose logs

# Clean and restart
docker-compose down --remove-orphans
docker-compose up --build
```
