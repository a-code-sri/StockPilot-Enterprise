# Setting up the AI assistant

StockPilot's **AI Assistant** page and the **Summarize** buttons on analytics pages use
[Ollama](https://ollama.com), which runs a small open model on your own machine. Nothing is
sent to an outside service. Without it the rest of the app works normally and the AI buttons
show as unavailable.

There are two ways to run Ollama. **Option A (Docker) is recommended**, because nothing has
to be installed on Windows and it avoids almost every installation problem.

| | Option A: Ollama in Docker | Option B: Ollama installed on Windows/macOS |
|---|---|---|
| Install | nothing extra | Ollama installer |
| GPU | NVIDIA only, needs a compose edit | used automatically if supported |
| Speed on CPU | ~10–30 s per answer with `qwen2.5:3b` | same |
| `OLLAMA_URL` in `.env` | `http://ollama:11434` (default) | `http://host.docker.internal:11434` |

## Option A: Ollama in Docker (recommended)

1. Make sure `.env` has the defaults:

   ```ini
   AI_ENABLED=true
   OLLAMA_URL=http://ollama:11434
   OLLAMA_MODEL=qwen2.5:3b
   ```

2. Start the stack with the `ai` profile:

   ```bash
   docker compose --profile ai up -d
   ```

   This starts an `ollama` container and a one-off `ollama-pull` container that downloads the
   model once (about 2 GB, kept in the `ollama` Docker volume).

3. Watch the download and wait for `success`:

   ```bash
   docker compose logs -f ollama-pull
   ```

4. Check it:

   ```bash
   docker compose exec ollama ollama list                 # qwen2.5:3b should be listed
   docker compose exec ollama ollama run qwen2.5:3b "Say hi"
   ```

5. Open **AI Assistant** in StockPilot. The subtitle should read *"Answers come from your live
   data via a local model (qwen2.5:3b)"*. Ask *"Which items are running low?"*.

Use `--profile ai` every time you start the stack, or the `ollama` container stays stopped.
To make that the default, add `COMPOSE_PROFILES=ai` to `.env`.

Give Docker Desktop enough memory: **Settings → Resources**, at least 6 GB for the whole stack
with the 3B model.

## Option B: Ollama installed on the computer

1. Install from <https://ollama.com/download>, then open a **new** terminal:

   ```powershell
   ollama --version
   ollama pull qwen2.5:3b
   ollama run qwen2.5:3b "Say hi"
   ```

2. In `.env` point StockPilot at the host:

   ```ini
   OLLAMA_URL=http://host.docker.internal:11434
   ```

3. Restart the API without the `ai` profile (the Docker Ollama isn't needed):

   ```bash
   docker compose up -d api
   ```

When running the backend outside Docker (`uvicorn` directly), use `OLLAMA_URL=http://localhost:11434`.

## Troubleshooting

Check what StockPilot sees first. Sign in to the web app, then open
`http://localhost:8000/docs`, authorize, and call **GET /ai/status**:

| `/ai/status` shows | Meaning | Fix |
|---|---|---|
| `"enabled": false` | `AI_ENABLED=false` | set it to `true`, `docker compose up -d api` |
| `"reachable": false` | the API can't reach Ollama at `OLLAMA_URL` | see *Cannot reach Ollama* below |
| `"model_available": false` | Ollama runs but the model isn't downloaded | `ollama pull <OLLAMA_MODEL>` (Option A: `docker compose exec ollama ollama pull qwen2.5:3b`) |
| `"can_use": false` | your role lacks `ai.use` | grant it on **Users & Roles** |

### Installation problems on Windows (Option B)

| Symptom | Fix |
|---|---|
| Installer blocked or deleted | SmartScreen: *More info → Run anyway*. Antivirus: allow `OllamaSetup.exe`, or use Option A. |
| `ollama` is not recognized | Close and reopen the terminal (the installer updates `PATH`). Otherwise run `"$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version`. |
| `bind: Only one usage of each socket address` / port 11434 in use | Ollama is already running from the tray icon, so use that one. Or quit it (tray → *Quit Ollama*) and run `ollama serve` again. The Docker `ollama` container doesn't publish port 11434, so it never conflicts. |
| `model requires more system memory` | Close other apps, or use a smaller model: `ollama pull qwen2.5:1.5b` and set `OLLAMA_MODEL=qwen2.5:1.5b`. |
| Download stalls or fails | Re-run `ollama pull qwen2.5:3b`; it resumes. On office or college networks a proxy may block it, so try another network. |
| C: drive is full | Set a user environment variable `OLLAMA_MODELS=D:\ollama\models`, restart Ollama, pull again. |
| Ollama crashes on start (older CPUs or GPU drivers) | Update GPU drivers, or use Option A, which runs on the CPU in Docker. |

### Cannot reach Ollama

- **Option A:** is the container running? `docker compose --profile ai ps` should show `ollama` as *Up*.
  Test from the API container:

  ```bash
  docker compose exec api python -c "import httpx; print(httpx.get('http://ollama:11434/api/tags').json())"
  ```

- **Option B:** `OLLAMA_URL` must be `http://host.docker.internal:11434`, not `localhost`. Inside a
  container, `localhost` means the container itself. If it still fails, make Ollama listen on all
  interfaces: set the user environment variable `OLLAMA_HOST=0.0.0.0`, restart Ollama, and
  `docker compose up -d api`.

- After editing `.env`, always run `docker compose up -d api` so the API picks up the change.

### Answers are slow or time out

The first question after a start loads the model into memory, so it takes longest (up to a
minute on CPU). If you see *"The AI model took longer than 180s"*, raise
`OLLAMA_TIMEOUT_SECONDS` in `.env`, use a smaller model, or use a GPU. For an NVIDIA GPU with
Option A, uncomment the `deploy:` block under `ollama` in `docker-compose.yml`.

### Answers look wrong

Small models make mistakes. The assistant tells the model to use only the data its tools
return, and every answer lists the data it looked at (*"Looked at: …"*). For better answers on
8 GB+ RAM or a GPU, use `OLLAMA_MODEL=qwen2.5:7b`, pull it, then restart the API.

## Which models work

The assistant uses tool calling to look up data. Models that support it in Ollama:
`qwen2.5:3b` (default), `qwen2.5:1.5b` (low memory), `qwen2.5:7b` (better), `llama3.2:3b`.
If a model has no tool support, StockPilot falls back to answering from a pre-fetched summary
of your data. It does the same when a small model returns an empty reply, which `qwen2.5:3b`
sometimes does on two-part questions.
