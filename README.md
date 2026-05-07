# 🖋️ Ghost Writer

**Ghost Writer** is an autonomous, multi-agent AI coding platform designed to revolutionize the development lifecycle. It doesn't just suggest code; it understands your entire codebase, orchestrates complex tasks across multiple specialized agents, and executes high-fidelity modifications with precision.

---

## 🚀 Key Features

*   **🧠 Intelligent Orchestration**: Powered by **LangGraph**, the system manages complex workflows, deciding when to analyze, when to generate, and when to ask for clarification.
*   **🔍 Deep Codebase Understanding**: Utilizing **Tree-sitter** for semantic parsing and advanced indexing, Ghost Writer maintains a high-context "mental model" of your project.
*   **🛠️ Precision Code Generation**: Dedicated agents specialized in writing clean, idiomatic, and bug-free code changes.
*   **🌐 Multi-Interface Interaction**:
    *   **Modern Web Dashboard**: A sleek React/Vite interface for project management and real-time agent monitoring.
    *   **WhatsApp Integration**: Interact with your codebase on the go via a robust WhatsApp client.
*   **⚡ High Performance**: Built with **FastAPI**, **Redis**, and **PostgreSQL**, optimized for low-latency responses and reliable background task execution.
*   **📦 Local-First & Extensible**: Managed with `uv` for seamless Python dependency resolution and designed for easy integration of new agents.

---

## 🏗️ Architecture

Ghost Writer follows a micro-agent architecture, where specialized components collaborate to solve complex problems:

| Component | Responsibility | Technology |
| :--- | :--- | :--- |
| **The Orchestrator** | The "Brain" — handles routing, state, and API gateway. | FastAPI, LangGraph, Redis |
| **Codebase Understander** | The "Memory" — indexes, parses, and searches the code. | Tree-sitter, SQLAlchemy |
| **Code Generator** | The "Hands" — executes file edits and creates new modules. | OpenAI/Groq, Custom Tools |
| **Frontend** | The "Eyes" — User interface and visualization. | React, Vite, Tailwind |
| **WhatsApp Client** | The "Mobile Bridge" — Remote interaction. | WhatsApp-web.js, Node.js |

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.11+, FastAPI, LangChain, SQLAlchemy, Pydantic.
*   **AI/LLM**: Groq (Llama-3), LangGraph.
*   **Frontend**: React, Vite, JavaScript.
*   **Database**: PostgreSQL, Redis (Task Queue & Caching).
*   **Tooling**: `uv` (Python), `npm` (Frontend), Docker Compose.

---

## 🚦 Getting Started

### Prerequisites

*   **Python 3.11+** (Highly recommend using `uv`)
*   **Node.js & npm**
*   **Docker & Docker Compose**
*   **API Keys**: OpenAI and/or Groq.

### Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/MeetGJethva/ghost_writer.git
    cd ghost_writer
    ```

2.  **Environment Configuration**:
    Configure the `.env` files in `the_orchestrator`, `code_base_understander`, and `whatsapp-client`. Use the provided `.env.example` files as templates.

3.  **Start Infrastructure**:
    ```bash
    cd the_orchestrator
    docker compose up -d
    ```

4.  **Install Dependencies & Run Backend**:
    ```bash
    # Root directory
    uv sync
    # Start Orchestrator
    uv run -m the_orchestrator.main
    # Start Worker
    uv run -m the_orchestrator.worker
    ```

5.  **Run Frontend**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

---

## 📂 Project Structure

```text
.
├── code_base_understander/  # Semantic indexing & code analysis
├── code_generator/          # Code generation agents & tools
├── frontend/                # React-based web interface
├── the_orchestrator/        # LangGraph logic & API Gateway
├── whatsapp-client/         # WhatsApp integration layer
├── main.py                  # Root entry point
└── pyproject.toml           # Project-wide dependencies
```

---

## 🤝 Contributing

Contributions are welcome! Whether it's adding new agents, improving indexing logic, or polishing the UI, feel free to open a PR.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by the Ghost Writer Team
</p>
