"# NEO-Sentinel" 


# NEO-Sentinel: Microservice Asteroid Risk Tracker

## System Overview
NEO-Sentinel is a distributed system designed to monitor Near-Earth Objects (NEOs) and assess potential risks based on individual user profiles. It demonstrates core microservice principles, including service isolation, RESTful communication, and containerization.

### Architecture Diagram


1. **Asteroid Data Service (Port 5001):** Consumes the NASA NeoWS API, filters the raw data, and normalizes it into a standard JSON format.
2. **User Watchlist Service (Port 5002):** Manages user records and their specific risk thresholds (e.g., alert me if an asteroid is > 0.5km).
3. **Risk Analysis Service (Port 5003):** The "Orchestrator." It fetches data from the other two services, applies the user's logic, and generates a final risk report.

## Setup & Installation
### Prerequisites
* Docker Desktop installed and running.
* A NASA API Key (obtained from api.nasa.gov).

### Running the System
1. Clone the repository.
2. Set your API key as an environment variable:
   `$env:NASA_API_KEY="YOUR_KEY_HERE"`
3. Run the orchestration command:
   `docker-compose up --build`

## Example API Calls
* **Generate Report:** `GET http://localhost:5003/report/1`
* **Health Check:** `GET http://localhost:5001/health`