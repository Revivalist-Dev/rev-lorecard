## 1. Technical Architecture & Stack

The platform's frontend is a modern single-page application (SPA), leveraging a curated stack of industry-leading technologies to ensure performance, type safety, and maintainability.

### 1.1. Core Frontend Framework
*   **Framework:** **React 18** with **TypeScript** for robust, type-safe component development.
*   **Build Tool:** **Vite** for optimized and rapid development builds and production bundling.
*   **Routing:** **React Router DOM** for declarative, client-side routing.

### 1.2. UI & Design System
*   **Component Library:** **Mantine UI**, a comprehensive React component library, is used for all UI elements, providing a cohesive and customizable design system.
*   **Icons:** **Tabler Icons** are integrated for consistent iconography.

### 1.3. State Management & Data Fetching
*   **Server State:** **TanStack React Query** is the designated library for managing all asynchronous operations, including data fetching, caching, mutations, and real-time updates.
*   **Client State:** **Zustand** is employed for lightweight, global client-side state, primarily for managing the Server-Sent Events (SSE) connection status.
*   **HTTP Client:** **Axios** serves as the primary HTTP client for all RESTful API communications.

### 1.4. Forms & Data Validation
*   **Form Management:** **@mantine/form**, Mantine's integrated form management solution, is used for its seamless integration with the component library.

---

## 2. Project & Code Structure

The project follows a feature-driven, modular structure that promotes scalability and ease of maintenance. The implemented structure aligns with modern React best practices.

*   `src/pages/`: Top-level components corresponding to application routes (`HomePage`, `ProjectsPage`, `ProjectDetailsPage`, etc.).
*   `src/components/`: Reusable UI components, categorized by feature (e.g., `projects`, `common`, `layout`).
*   `src/hooks/`: Custom React hooks that abstract all API interactions and business logic (e.g., `useProjects`, `useTranslateEntry`, `useBulkUpdateEntries`). This is the primary data layer for the UI.
*   `src/services/`: Contains the core `apiClient` (Axios instance) configuration.
*   `src/stores/`: Zustand store definitions for global client state (e.g., `sseStore`).
*   `src/types/`: Centralized TypeScript definitions for all data entities (e.g., `Project`, `Term`).
*   `src/utils/`: General-purpose helper functions (e.g., `formatDate`).
