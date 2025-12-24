# LLM Council

![llmcouncil](header.jpg)

**LLM Council** is a "Chain of Thought" and "MoA" (Mixture of Agents) orchestration tool. Instead of relying on a single LLM, you form a "Council" of different models (Gemini, GPT, Claude, Grok, etc.) to deliberate on your queries. They review each other's work, debate, providing a synthesized, highly accurate final response.

## ✨ Features

- **Multiple Council Modes**:
  - **Standard Council**: Models answer individually, rank each other, and a Chairman synthesizes the best answer.
  - **Chain of Debate**: Models answer, then critique each other's arguments to find logical flaws before synthesis.
  - **Six Thinking Hats**: Models are assigned specific cognitive perspectives (Facts, Feelings, Risks, Benefits, Creativity, Process) to ensure holistic coverage.
  - **Ensemble (Fast)**: Parallel execution for quick consensus without the peer-review stage.
- **Dynamic Model Selection**: Choose your specific council members and chairman from all available OpenRouter models.
- **Material Design 3 UI**: A beautiful, modern interface with dark/light mode support (system), sticky headers, and responsive layout.
- **Dual Storage**: Supports both local JSON file storage (default) and PostgreSQL database (production).

--**Standard Council workings**

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## 🚀 Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python management.

```bash
# Backend
uv sync

# Frontend
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/).

## 🏃‍♂️ Running Locally

### All-in-one Script

```bash
./start.sh
```

Opens the app at `http://localhost:5173`.

### Manual Start

**Backend:**

```bash
uv run python -m backend.main
```

**Frontend:**

```bash
cd frontend
npm run dev
```

## ☁️ Deploying to Render (with Database)

This project includes a `render.yaml` Blueprint for easy deployment with a managed PostgreSQL database.

1. **Push to GitHub**: Ensure this code is in a GitHub repository.
2. **Create New Blueprint in Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com/blueprints).
   - Click **"New Blueprint Instance"**.
   - Connect your repository.
3. **Configure**:
   - Render will detect `render.yaml`.
   - You will be prompted to provide `OPENROUTER_API_KEY`.
4. **Deploy**:
   - Render will create a **Web Service** (the app) and a **PostgreSQL Database**.
   - The app will automatically detect the `DATABASE_URL` environment variable and switch from file storage to database storage.

## 🛠 Tech Stack

- **Backend**: FastAPI, Async/Await, SQLAlchemy (Async), OpenAI (Client) / OpenRouter
- **Frontend**: React, Vite, Material Design 3 (Custom CSS)
- **Database**: PostgreSQL (Production) / JSON Files (Local/Dev)
- **Design**: "Vibe Coded" aesthetics with focused UX.
