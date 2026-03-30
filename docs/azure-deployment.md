# Deploying To Azure App Service

This guide shows the first cloud deployment step for this project: hosting the current FastAPI app in Azure App Service.
-
## What This Step Does

- moves the API and dashboard off your local machine
- gives the project a public URL
- keeps the core app logic unchanged for the first deployment

This guide does **not** yet replace SQLite with Azure SQL. That comes after the app is running successfully in Azure.

## Architecture For The First Deployment

- Azure Resource Group: groups all Azure resources for the project
- Azure App Service Plan: compute/pricing tier
- Azure Web App: hosts the FastAPI app

## Files Added For Azure

- `startup.sh`
  - tells Azure how to start the FastAPI app with Gunicorn + Uvicorn workers
- `requirements.txt`
  - includes `gunicorn`, which is needed for the App Service startup command used here

## Before You Start

Make sure you have:

- an Azure account
- an Azure subscription
- this repo pushed to GitHub, or the repo available locally for zip deployment

## Recommended First Deployment Path

### 1. Create a Resource Group

In Azure Portal:

- search for `Resource groups`
- select `Create`
- choose your subscription
- name it something like `avalanche-risk-rg`
- pick a region close to you

### 2. Create an App Service Plan

In Azure Portal:

- search for `App Service Plan`
- select `Create`
- choose the same resource group
- select `Linux`
- pick a low-cost tier to start

This is the compute layer behind the web app.

### 3. Create a Web App

In Azure Portal:

- search for `Web App`
- select `Create`
- choose the same resource group
- choose a globally unique app name
- publish as `Code`
- runtime stack: `Python`
- operating system: `Linux`
- region: same as the app service plan
- select the App Service Plan you created

This is the actual hosted application.

### 4. Deploy the Code

You have two simple choices:

- Deployment Center with GitHub
- Zip deploy from your local machine

GitHub deployment is the easiest ongoing workflow if your project is already in a GitHub repo.

### 5. Set the Startup Command

In the Azure Portal, open your Web App and go to:

- `Configuration`
- `General settings`
- `Startup Command`

Set the startup command to:

```sh
startup.sh
```

This uses the startup file committed in the repo.

## Why `startup.sh` Is Needed

This project uses:

- a `src/` layout
- FastAPI rather than a root-level Flask app

Azure App Service for Python needs a custom startup command for this project layout, so we use:

```sh
gunicorn \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8000} \
  --chdir src \
  avalanche_risk_monitoring.services.api.app:app
```

That command:

- starts Gunicorn as the process manager
- uses Uvicorn workers for ASGI/FastAPI
- binds to the port Azure provides
- changes directory into `src`
- loads the FastAPI app object from `services/api/app.py`

### 6. Set App Settings

In the Azure Portal, open your Web App and go to `Environment variables` and add:

- `SCM_DO_BUILD_DURING_DEPLOYMENT = true`
- `APP_BOOTSTRAP_HISTORY_RUNS = 0`

These help App Service install dependencies during deployment and keep startup lightweight on the free tier.

## First Checks After Deployment

Once the deployment completes, test:

- `/health`
- `/docs`
- `/`

Examples:

- `https://<your-app-name>.azurewebsites.net/health`
- `https://<your-app-name>.azurewebsites.net/docs`
- `https://<your-app-name>.azurewebsites.net/`

## Expected Limitation In This First Version

The app currently uses SQLite:

- `data/processed/avalanche_monitoring.db`

For Azure App Service, this project now automatically switches to:

- `/home/site/data/processed/avalanche_monitoring.db`

when App Service environment variables are present, so the database is created in a writable location.

That is acceptable for a first cloud-hosting exercise, but it is not the long-term cloud database choice. The next upgrade after successful hosting is:

- move SQLite to Azure SQL Database

## Next Cloud Steps After Hosting Works

1. Replace SQLite with Azure SQL Database
2. Move local staged exports to Azure Blob Storage
3. Move secrets to Azure Key Vault or App Settings
4. Add monitoring with Application Insights
5. Revisit Fabric integration once the hosted app is stable
