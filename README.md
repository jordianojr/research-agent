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

## Features

- **Agent Management:** Create, retrieve, and delete agents.
- **Messaging:** Send messages to agents.
- **Updates:** Update agent websites and files.
- **Containerized:** Fully Dockerized for seamless deployment.

## Project Structure


## Installation

1. **Using Docker:**

    Preferably Docker version 27.4.0

   ```bash
    git clone https://github.com/yourusername/research_agent.git
    cd research_agent
    docker-compose up --build
    ```

## Testing

    ```bash
    pytest test/test_agents.py
    ```
## License

This project is licensed under the MIT License.
---

Feel free to adjust the sections, badges, and links (such as the repository URL) to fit your project's specific details. Enjoy building your Research Agent!


