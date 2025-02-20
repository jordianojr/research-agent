# Research Agent

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight FastAPI-based research agent application that provides a set of RESTful endpoints for managing agents, sending messages, and updating agent-related resources.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Docker Setup](#docker-setup)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Research Agent is a simple RESTful API built with FastAPI. It allows you to:
- Create, fetch, and delete agents.
- Send messages to agents.
- Update agent websites and files.

The app is designed with a focus on simplicity and is easily containerized using Docker.

### Multi-Agent Workflow

The system uses a LangGraph-based workflow with multiple specialized agents:

1. **Planner Agent**: Creates high-level outlines and plans for the research task
2. **Research Agent**: 
   - Generates search queries based on the plan
   - Uses Tavily to gather relevant information
   - Processes and extracts key information from search results
3. **Generation Agent**: Creates content based on the research and plan
4. **Reflection Agent**: Reviews and critiques the generated content
5. **Research Critique Agent**: Performs additional targeted research based on the critique

The agents work together in a flexible workflow that can:
- Adapt the research path based on initial findings
- Perform multiple revision cycles
- Conduct additional research when needed
- Generate comprehensive and well-researched content

![Multi-Agent Workflow](docs/images/workflow.png)

*Figure 1: Multi-Agent Research Workflow Architecture*

## Features

- **Agent Management:** Create, retrieve, and delete agents.
- **Messaging:** Send messages to agents.
- **Updates:** Update agent websites and files.
- **Containerized:** Fully Dockerized for seamless deployment.

## Project Structure

```plaintext
research_agent/
│── app/ # Main FastAPI application
│ ├── main.py # FastAPI entry point
│ ├── routes/ # API route handlers
│ ├── models/ # Data models
│ ├── services/ # Business logic and services
│ ├── database.py # Database connection setup (if applicable)
│
│── test/ # Unit and integration tests
│ ├── test_agents.py # Tests for agent-related endpoints
│
│── docker/ # Docker-related files
│ ├── Dockerfile # Docker build configuration
│ ├── requirements.txt # Python dependencies
│
│── .gitignore # Git ignore file
│── README.md # Project documentation
├── docker-compose.yml # Docker Compose setup
```

### Explanation:
- **`app/`**: Contains the core FastAPI application logic, including routes, models, and services.  
- **`test/`**: Holds test files using `pytest`.  
- **`docker/`**: Stores Docker-related configuration files, including `Dockerfile` and dependencies.  
- **`.gitignore`**: Lists files and directories to be ignored by Git.  
- **`README.md`**: Documentation for the project.  

This structure keeps things modular and easy to maintain. 
## Installation

1. **Using Docker:**

    Preferably Docker version **27.4.0**  

    ```bash
    git clone https://github.com/jordianojr/research-agent.git
    cd research_agent
    docker-compose up --build
    brew services start mongodb-community

## Testing
    
    pytest test/test_agents.py

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements, bug fixes, or features.

## License

This project is licensed under the MIT License.

---

Feel free to adjust the sections, badges, and links (such as the repository URL) to fit your project's specific details. Enjoy building your Research Agent!


