# Docker Instructions

This project includes Docker configuration for running the Streamlit application in a container.

## Prerequisites

- [Docker](https://www.docker.com/get-started) installed on your system

## Environment Variables Configuration

1. Copy the example environment file to create your own:
   ```
   copy .env.example .env
   ```

2. Edit the `.env` file with your specific configuration values:
   - Set your OpenAI API key
   - Configure device hostname, type, and port
   - Add any other environment variables needed by the application

## Running the Application

Build and start the container:

```cmd
docker-compose up -d
```

If you've made changes to the code that need to be included in the container:

```cmd
docker-compose up --build -d
```

## Stopping the Container

```cmd
docker-compose down
```

## Mounted Volumes

The following directories are mounted from the host into the container:

- **./workbench:/app/workbench**: For persistent data storage
- **./configuration:/app/configuration**: For device inventories and settings files

Any changes made to these directories on the host will be immediately reflected in the container.

## What's Running in the Container

- **Streamlit Application**: Runs on port 8501
- The container also exposes port 8001 for the Alert Queue service, which can be started through the Streamlit interface when needed
