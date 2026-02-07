# PharmGuard AI Setup Guide

This guide will help you set up and run the PharmGuard AI project on windows.

## Prerequisites

- **Python 3.10+**: Ensure Python is installed and added to your PATH.
- **Git**: For version control.
- **PowerShell**: Recommended for running scripts on Windows.

## Installation

1.  **Clone the repository** (if you haven't already):
    ```powershell
    git clone <repository-url>
    cd pharmguard-ai
    ```

2.  **Run the Setup Script**:
    The included `run_local.ps1` script handles virtual environment creation and backend dependency installation.
    ```powershell
    .\run_local.ps1
    ```
    *Note: If you see execution policy errors, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.*

3.  **Install Frontend Dependencies**:
    Open a new terminal configuration for the frontend.
    ```powershell
    cd frontend
    pip install -r requirements.txt
    ```

## Configuration

1.  **Backend Environment Variables**:
    Create a `.env` file in the `backend` directory (optional, but recommended for API keys).
    ```env
    OPENAI_API_KEY=sk-...
    OPENAI_MODEL=gpt-3.5-turbo  # Optional, defaults to gpt-3.5-turbo
    ```

2.  **Frontend Environment Variables**:
    The frontend reads from OS environment variables. You can set them in your terminal before running.
    ```powershell
    $env:BACKEND_URL="http://localhost:8000"
    $env:ADMIN_TOKEN="demo-admin-token"
    ```

## Running the Application

You need two terminal windows running simultaneously.

### Terminal 1: Backend
The `run_local.ps1` script starts the backend automatically.
```powershell
.\run_local.ps1
```
The backend will run at `http://localhost:8000`.
- Swagger docs: `http://localhost:8000/docs`

### Terminal 2: Frontend
Navigate to the frontend directory and run Streamlit.
```powershell
cd frontend
streamlit run app.py
```
The frontend will open in your browser at `http://localhost:8501`.

## Troubleshooting

- **Database Issues**: If you encounter database errors, delete the `data/pharmguard.db` file to reset the database (it will be recreated on startup).
- **Module Not Found**: Ensure you have activated the virtual environment (`.venv\Scripts\Activate.ps1`) before running commands manually.
