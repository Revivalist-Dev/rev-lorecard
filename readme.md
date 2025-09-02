## Getting Started with Docker

The only prerequisite is to have Docker and Docker Compose installed.

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/bmen25124/lorebook-creator.git
cd lorebook-creator
```

**2. Configure your API Key**
Copy the example environment file to create your own local configuration.
```bash
# On Linux, macOS, or WSL
cp .env.example .env

# On Windows
copy .env.example .env
```
Now, open the new `.env` file with a text editor and add your `OPENROUTER_API_KEY`.

### Running the Application

*   **To run with SQLite (Default & Simplest):**
    ```bash
    docker-compose up --build
    ```
    This is the easiest way to get started. Your database will be saved in a `data` folder in your project directory.

*   **To run with PostgreSQL (Optional & More Robust):**
    Use the `-f` flag to include the PostgreSQL configuration.
    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
    ```

The first time you run this, Docker will build the application, which may take a few minutes.

### Accessing the App

Once the containers are running, the application will be available at:
**[http://localhost:3000](http://localhost:3000)**
