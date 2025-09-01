## Getting Started

### Prerequisites

-   Node.js (v18 or higher)
-   pnpm (or your preferred package manager)

### Installation & Setup

1.  **Clone the repository:**
    ```sh
    git clone <your-repository-url>
    cd <repository-directory>
    ```
2.  **Install dependencies:**
    ```sh
    pnpm install
    ```
3.  **Setup environment variables:**
    Create a `.env.local` file in the root directory. Example:
    ```
    VITE_API_BASE_URL=http://127.0.0.1:3000
    ```
4.  **Run the development server:**
    ```sh
    pnpm dev
    ```
    The application will be available at `http://localhost:5173`.

## Available Scripts

-   `pnpm dev`: Starts the development server.
-   `pnpm build`: Builds the app for production.
-   `pnpm preview`: Serves the production build locally.
-   `pnpm lint`: Runs the ESLint checker.