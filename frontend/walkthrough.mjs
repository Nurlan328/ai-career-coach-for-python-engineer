// Drives the running app (http://127.0.0.1:5173) through the full MVP flow and
// saves screenshots to ./.preview. Backend must be on :8000.
//   node walkthrough.mjs
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = "http://127.0.0.1:5173";
const OUT = "./.preview";
mkdirSync(OUT, { recursive: true });

const email = `demo+${Date.now()}@example.com`;
const password = "secret123";
const shots = [];

async function shot(page, name) {
  const path = `${OUT}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  shots.push(path);
  console.log("shot:", name);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
page.on("console", (m) => {
  if (m.type() === "error") console.log("PAGE-ERR:", m.text());
});

try {
  // 1. Login
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[type="email"]');
  await shot(page, "01-login");

  // 2. Register
  await page.click('a[href="/register"]');
  await page.waitForSelector('input[type="text"]');
  await page.fill('input[type="text"]', "Demo User");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await shot(page, "02-register");
  await page.click("button.primary");

  // 3. Dashboard
  await page.waitForSelector(".app-shell", { timeout: 15000 });
  await page.waitForTimeout(600);
  await shot(page, "03-dashboard");

  // 4. Resume upload + analysis
  await page.click('.nav-link:has-text("Резюме")');
  await page.waitForSelector('input[type="file"]');
  await page.setInputFiles('input[type="file"]', {
    name: "cv.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "Senior Python backend developer. FastAPI, Django, SQLAlchemy, PostgreSQL, " +
        "Redis, Celery, Docker, asyncio/await. REST API, microservices, pytest. " +
        "Led a team, mentored juniors.",
    ),
  });
  await page.click("button.primary");
  await page.waitForSelector(".resume-head", { timeout: 20000 });
  await page.waitForTimeout(500);
  await shot(page, "04-resume");

  // 4b. Vacancy gap-analysis + roadmap
  await page.click('.nav-link:has-text("Вакансия")');
  await page.waitForSelector("textarea");
  await page.fill(
    "textarea",
    "Ищем Senior Python backend инженера: FastAPI, PostgreSQL, Redis, " +
      "Kubernetes, Docker, gRPC. Опыт highload, микросервисов и CI/CD.",
  );
  await page.click('button.primary:has-text("Анализировать")');
  await page.waitForSelector(".chips", { timeout: 20000 });
  await page.click('button.primary:has-text("Сравнить")');
  await page.waitForSelector(".score", { timeout: 20000 });
  await page.click('button.primary:has-text("Построить")');
  await page.waitForSelector(".week", { timeout: 20000 });
  await page.waitForTimeout(400);
  await shot(page, "04b-vacancy");

  // 5. Question generation
  await page.click('.nav-link:has-text("Вопросы")');
  await page.waitForSelector("select");
  await page.click("button.primary");
  await page.waitForSelector(".questions li", { timeout: 20000 });
  await shot(page, "05-questions");

  // 6. Interview — start + first question
  await page.click('.nav-link:has-text("Интервью")');
  await page.waitForSelector("button.primary");
  await page.click("button.primary");
  await page.waitForSelector("textarea", { timeout: 20000 });
  await shot(page, "06-interview-question");

  // 6b. Answer + feedback
  await page.fill(
    "textarea",
    "Depends injects dependencies per request, enabling reuse, testing via " +
      "overrides, and sharing resources like a DB session through a generator.",
  );
  await page.click("button.primary");
  await page.waitForSelector(".feedback", { timeout: 20000 });
  await page.waitForTimeout(500);
  await shot(page, "07-interview-feedback");

  // 7. AI tutor (streaming chat)
  await page.click('.nav-link:has-text("AI-тьютор")');
  await page.waitForSelector(".chat-input input");
  await page.fill(
    ".chat-input input",
    "Чем asyncio.gather отличается от asyncio.create_task?",
  );
  await page.click(".chat-input button.primary");
  await page.waitForSelector(".bubble.assistant", { timeout: 20000 });
  await page.waitForTimeout(1500);
  await shot(page, "08-tutor");

  // 7b. RAG mode (knowledge base + sources). First call builds the index.
  await page.check(".rag-toggle input");
  await page.fill(".chat-input input", "Как избежать N+1 в SQLAlchemy?");
  await page.click(".chat-input button.primary");
  await page.waitForSelector(".sources", { timeout: 60000 });
  await page.click(".sources summary");
  await page.waitForTimeout(400);
  await shot(page, "09-tutor-rag");

  console.log("OK", JSON.stringify(shots));
} catch (e) {
  console.error("ERROR:", e.message);
  await shot(page, "99-error");
  process.exitCode = 1;
} finally {
  await browser.close();
}
