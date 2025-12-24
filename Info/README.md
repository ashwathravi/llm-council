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

## ☁️ Deploying to Render (Database Mode)

The easiest way to deploy with the database is using **Blueprints**.

1. **Push to GitHub**: Make sure your latest code (including `render.yaml`) is pushed to your GitHub repository.
2. **Open Render Dashboard**: Go to [dashboard.render.com](https://dashboard.render.com/).
3. **Create Blueprint**:
    - Click the **New +** button in the top right.
    - Select **Blueprint Instance**.
4. **Connect Repo**:
    - Find your `llm-council` repo in the list and click **Connect**.
5. **Configure**:
    - Render will read the `render.yaml` file.
    - It will show a formatted list of resources it will create (Web Service + Database).
    - **Env Vars**: You will be prompted to enter your `OPENROUTER_API_KEY`. Paste it in.
6. **Deploy**:
    - Click **Apply**.
    - Render will spin up the PostgreSQL database first, then the Web Service.
    - It automatically injects the `DATABASE_URL` from the new DB into your Web Service.
7. **Done**:
    - Once the build finishes, your app will be live and automatically using the database. (The "DB" badge in the sidebar will be active).

## 🛠 Tech Stack

- **Backend**: FastAPI, Async/Await, SQLAlchemy (Async), OpenAI (Client) / OpenRouter
- **Frontend**: React, Vite, Material Design 3 (Custom CSS)
- **Database**: PostgreSQL (Production) / JSON Files (Local/Dev)
- **Design**: "Vibe Coded" aesthetics with focused UX.
