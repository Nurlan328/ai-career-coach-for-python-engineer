# AI Career Coach — Frontend

Vite + React 18 + TypeScript SPA for the [AI Career Coach](../README.md) backend.

## Run

```bash
npm install
cp .env.example .env     # optional; defaults to http://127.0.0.1:8000
npm run dev              # http://localhost:5173
```

Make sure the FastAPI backend is running first:

```bash
# from the project root
uvicorn app.main:app --reload
```

## Build

```bash
npm run build           # tsc -b && vite build  ->  dist/
npm run preview         # serve the production build
```

## What's inside

| Page          | Route        | Backend endpoints                                   |
|---------------|--------------|-----------------------------------------------------|
| Login         | `/login`     | `POST /auth/login`                                  |
| Register      | `/register`  | `POST /auth/register`                               |
| Dashboard     | `/`          | `GET /interviews/history`, `GET /auth/me`           |
| Resume        | `/resume`    | `POST /resumes/upload`                              |
| Vacancy       | `/vacancy`   | `POST /vacancies/analyze`, `/compare-with-resume`, `/roadmap` |
| Questions     | `/questions` | `GET /questions/categories`, `POST /questions/generate` |
| Interview     | `/interview` | `POST /interviews/start`, `POST /interviews/{id}/answer` |
| AI Tutor      | `/tutor`     | `POST /coach/ask/stream` (streamed) + `/coach/rag` (KB + sources) |

## Structure

```
src/
├── api/           # typed fetch wrappers (client.ts handles auth + base URL)
├── auth/          # AuthContext: JWT in localStorage, current user
├── components/    # Layout (sidebar) + ProtectedRoute
├── pages/         # one component per screen
├── types.ts       # shared API types (mirror the backend schemas)
└── index.css      # single dark-theme stylesheet (no UI framework)
```

The JWT is stored in `localStorage` and sent as a `Bearer` token. The tutor chat
reads the streaming response via `fetch` + `ReadableStream`, appending tokens as
they arrive.

## End-to-end walkthrough (Playwright)

`walkthrough.mjs` drives a real browser through the whole flow (register →
dashboard → resume → questions → interview → tutor) and saves screenshots to
`.preview/`. With both servers running:

```bash
node walkthrough.mjs        # screenshots land in ./.preview/
```

## Config

| Var             | Default                   | Description           |
|-----------------|---------------------------|-----------------------|
| `VITE_API_BASE` | `http://127.0.0.1:8000`   | FastAPI backend URL   |
