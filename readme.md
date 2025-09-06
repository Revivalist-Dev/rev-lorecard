# Lorebook Creator

Create lorebooks from URLs using LLMs.

## Screenshots & Videos

<details>
  <summary>Main Workflow</summary>
  
  *A video demonstrating the main workflow of creating a lorebook from a URL*

https://github.com/user-attachments/assets/38f6dbd7-4975-47f1-8e4f-3e9319cce083

</details>

<details>
  <summary>Manage Sources</summary>
  
  ![Manage Sources](showcase/manage-sources.png)

  ![Manage Sources](showcase/edit-source.png)
  
</details>

<details>
  <summary>Confirming Links</summary>
  
  ![Confirming Links](showcase/confirm-links.png)
  
</details>

<details>
  <summary>Generate Entries</summary>
  
  ![Generate Entries](showcase/generate-entries.png)
  
</details>

<details>
  <summary>Completed Lorebook</summary>
  
  *The final generated lorebook, structured and ready for use.*
  
  ![Completed Lorebook](showcase/complete.png)
</details>

<details>
  <summary>Project Analytics</summary>
  
  ![Project Analytics](showcase/project-analytics.png)
  
</details>

<details>
  <summary>API Request Logs</summary>
  
  ![API Request Logs](showcase/api-request-logs.png)
  
</details>

## Some notes
- This is not deep research; it doesn't involve a web search. You need to give a URL that has multiple links. _Fandom:category_ pages are perfect for the app. For example, you can give [Oblivion Skill Books](https://elderscrolls.fandom.com/wiki/Category:Oblivion:_Skill_Books). So this is going to extract all books and navigate one by one, and create a lorebook for each book.
- You can see all API request logs on the API Requests modal. You can also see the project analytics on the Project Analytics modal.
- Currently, I'm only supporting openrouter and gemini because it is enough for me. However, if I see a need to add another API, I will add it.
- You can edit all prompts.

### Input token usage by steps
1. **Search Params:** Single LLM request. This is a very simple operation. Input token is very low.
2. **Manage Sources & Crawl** _Generate_ button making a single LLM request. But if `Max Crawl Depth` is more than 1, it would navigate the links. This is a bit more complex because we giving [cleaned html](https://github.com/bmen25124/lorebook-creator/blob/4ee1c3335cdece08b25795020ceca4f8a37bdcc4/server/src/services/scraper.py#L8) to LLM. Since it is a HTML, token usage is high compared to others. However if you already _crawled_ the URL, you can always use _Rescan Selected_ to confirm new links.
3. **Generate Entries:** Request count = link count. We are giving [cleaned html -> markdown](https://github.com/bmen25124/lorebook-creator/blob/4ee1c3335cdece08b25795020ceca4f8a37bdcc4/server/src/services/scraper.py#L111) to LLM. So token usage shouldn't be too high unless the page is very long. But if there are many links, token usage will be high.

## How to Install and Run the Application

Choose the option that best fits your needs.

### Option 1: Quick Start with Docker (Recommended for Users)

**1. Create a directory and `.env` file**
First, create a folder on your computer for the application's data. Inside that folder, create a file named `.env` and add your API key.

```env
# .env file
OPENROUTER_API_KEY=your_secret_key_here
GOOGLE_GEMINI_KEY=your_secret_key_here
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com/v1
OPENAI_COMPATIBLE_API_KEY=your_secret_key_here
PORT=3000
```

**2. Run the application**
Open your terminal in that same folder and choose one of the commands below.

*   **To run with SQLite (Simple & Recommended):**
    A `data` folder will be created in your current directory to store the database.

    *   **For Linux, macOS, or WSL:**
        ```bash
        docker run -d --name lorebook-app --restart unless-stopped -p 3000:3000 \
          --env-file .env \
          -e APP_ENV=production \
          -e DATABASE_TYPE=sqlite \
          -e DATABASE_URL=/app/server/data/lorebook_creator.db \
          -v "$(pwd)/data:/app/server/data" \
          ghcr.io/bmen25124/lorebook-creator:v1.8
        ```

    *   **For Windows (Command Prompt):**
        ```cmd
        docker run -d --name lorebook-app --restart unless-stopped -p 3000:3000 ^
          --env-file .env ^
          -e APP_ENV=production ^
          -e DATABASE_TYPE=sqlite ^
          -e DATABASE_URL=/app/server/data/lorebook_creator.db ^
          -v "%cd%/data:/app/server/data" ^
          ghcr.io/bmen25124/lorebook-creator:v1.8
        ```
        
    *   **For Windows (PowerShell):**
        ```powershell
        docker run -d --name lorebook-app --restart unless-stopped -p 3000:3000 `
          --env-file .env `
          -e APP_ENV=production `
          -e DATABASE_TYPE=sqlite `
          -e DATABASE_URL=/app/server/data/lorebook_creator.db `
          -v "${pwd}/data:/app/server/data" `
          ghcr.io/bmen25124/lorebook-creator:v1.8
        ```

*   **To run with PostgreSQL (Advanced):**
    This requires starting a separate database container first. These commands work on all platforms.

    ```bash
    # 1. Create a network
    docker network create lorebook-net

    # 2. Start the database container
    docker run -d --name lorebook-db --restart unless-stopped --network lorebook-net \
      -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=lorebook_creator \
      -v lorebook_creator_postgres_data:/var/lib/postgresql/data \
      postgres:13

    # 3. Start the application container
    docker run -d --name lorebook-app --restart unless-stopped --network lorebook-net -p 3000:3000 \
      --env-file .env \
      -e APP_ENV=production \
      -e DATABASE_TYPE=postgres \
      -e DATABASE_URL=postgresql://user:password@lorebook-db:5432/lorebook_creator \
      ghcr.io/bmen25124/lorebook-creator:v1.8
    ```

---

### Option 2: Run from Source on Windows (`start.bat`)

Use this method if you are on Windows and prefer not to use Docker. This script automates the entire setup process.

**Prerequisites:**
You must have the following software installed and available in your PATH:
-   [Git](https://git-scm.com/downloads)
-   [Python](https://www.python.org/downloads/) (version 3.10 or higher)
-   [Node.js](https://nodejs.org/) (version 18 or higher)
-   [uv](https://github.com/astral-sh/uv) (run `pip install uv`)
-   [pnpm](https://pnpm.io/installation) (run `npm install -g pnpm`)

**1. Clone the repository**
```bash
git clone https://github.com/bmen25124/lorebook-creator.git
cd lorebook-creator
```

**2. Run the script**
Simply double-click the `start.bat` file or run it from your terminal:
```bash
.\start.bat
```
The first time you run it, the script will guide you through setting up your configuration (`.env` file), installing all dependencies, build the client, and start the server.

---

### Option 3: Run from Source with Docker Compose (For Developers)

Use this method if you have cloned the source code and want to build and run the application in a containerized environment. This is ideal for development.

**1. Clone the repository**
```bash
git clone https://github.com/bmen25124/lorebook-creator.git
cd lorebook-creator
```

**2. Configure your API Key**
Copy the example environment file.
```bash
# On Linux, macOS, or WSL
cp .env.example .env

# On Windows
copy .env.example .env
```
Now, open the new `.env` file and add your `OPENROUTER_API_KEY` or `GOOGLE_GEMINI_KEY`.

**3. Build and run the application**

*   **To run with SQLite (Default):**
    ```bash
    docker-compose up --build
    ```

*   **To run with PostgreSQL (Optional):**
    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
    ```

---

### Accessing the App

Once running, the application will be available at:
**[http://127.0.0.1:3000/](http://127.0.0.1:3000/)**
