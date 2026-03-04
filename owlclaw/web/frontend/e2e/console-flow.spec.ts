import { test, expect } from "@playwright/test";

const baseUrl = process.env.CONSOLE_E2E_BASE_URL || "http://127.0.0.1:8000";

test.describe("Console flow", () => {
  test("Overview -> Governance -> Ledger navigation", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByRole("main").getByRole("heading", { name: "Overview" })).toBeVisible();

    await page.getByRole("link", { name: "Governance" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Governance" })).toBeVisible();

    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Ledger", exact: true })).toBeVisible();
  });

  test("Overview -> Agents navigation and empty state", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByRole("main").getByRole("heading", { name: "Overview" })).toBeVisible();

    await page.getByRole("link", { name: "Agents" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Agents", exact: true })).toBeVisible();
    // No-DB: expect friendly empty state (EmptyState "No agents found"), not 500/error
    await expect(page.getByText("No agents found")).toBeVisible({ timeout: 5000 });
  });

  test("Governance page triggers governance API calls", async ({ page }) => {
    const apiCalls: string[] = [];
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/")) apiCalls.push(req.url());
    });

    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Governance" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Governance" })).toBeVisible();
    // Wait for loading to complete (day/week/month buttons or error) so API calls have fired
    await Promise.race([
      page.getByRole("button", { name: /day/i }).waitFor({ state: "visible", timeout: 8000 }),
      page.getByText(/Failed to load/).waitFor({ state: "visible", timeout: 8000 }),
    ]).catch(() => null);
    await page.waitForTimeout(300);

    const govCalls = apiCalls.filter((u) => /governance\/(budget|circuit-breakers|visibility-matrix)/.test(u));
    expect(govCalls.length).toBeGreaterThanOrEqual(1);
  });

  test("Governance granularity switch triggers new API request (F-7)", async ({ page }) => {
    const apiCalls: string[] = [];
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/")) apiCalls.push(req.url());
    });

    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Governance" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Governance" })).toBeVisible();
    await page.getByRole("button", { name: /day/i }).waitFor({ state: "visible", timeout: 8000 });
    const beforeClick = apiCalls.filter((u) => u.includes("granularity=week")).length;

    await page.getByRole("button", { name: "week" }).click();
    await page.waitForTimeout(500);

    const afterClick = apiCalls.filter((u) => u.includes("granularity=week"));
    expect(afterClick.length).toBeGreaterThan(beforeClick);
  });

  test("Ledger Apply filter triggers new API request with params (F-11)", async ({ page }) => {
    const apiCalls: string[] = [];
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/ledger")) apiCalls.push(req.url());
    });

    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Ledger", exact: true })).toBeVisible();
    await expect(page.getByRole("main").getByRole("heading", { name: "Filters" })).toBeVisible({ timeout: 5000 });
    await page.getByPlaceholder("Agent").fill("test-agent-id");
    const beforeApply = apiCalls.length;

    await page.getByRole("button", { name: "Apply" }).click();
    await page.waitForTimeout(500);

    const ledgerCalls = apiCalls.filter((u) => u.includes("agent_id=") || u.includes("agent_id%3D"));
    expect(ledgerCalls.length).toBeGreaterThanOrEqual(1);
  });

  test("Ledger sort change triggers order_by request param (F-14)", async ({ page }) => {
    const apiCalls: string[] = [];
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/ledger")) apiCalls.push(req.url());
    });

    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Ledger", exact: true })).toBeVisible();
    await page.getByLabel("Order By").selectOption("cost_desc");
    await page.getByRole("button", { name: "Apply" }).click();
    await page.waitForTimeout(500);

    const sortedCalls = apiCalls.filter((u) => u.includes("order_by=cost_desc") || u.includes("order_by%3Dcost_desc"));
    expect(sortedCalls.length).toBeGreaterThanOrEqual(1);
  });

  test("Ledger filter panel and empty state", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Ledger", exact: true })).toBeVisible();
    await expect(page.getByRole("main").getByRole("heading", { name: "Filters" })).toBeVisible({ timeout: 5000 });
    await expect(page.getByPlaceholder("Agent")).toBeVisible();
    await expect(page.getByRole("heading", { name: "No ledger records" }).or(page.getByRole("button", { name: "Reset Filters" })).first()).toBeVisible({ timeout: 3000 });
  });

  test("First load under 5s", async ({ page }) => {
    const start = Date.now();
    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByRole("main").getByRole("heading", { name: "Overview" })).toBeVisible();
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(5000);
  });

  test("Capabilities and Settings pages load", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Capabilities" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Capabilities" })).toBeVisible();

    await page.getByRole("link", { name: "Settings" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Settings" })).toBeVisible();
  });

  test("Tab key traverses sidebar", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(["A", "BUTTON", "DIV"]).toContain(focused);
  });

  // --- Deep tests: Overview ---
  test("Overview has System Health and component checks (F-1)", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByRole("main").getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "System Health" })).toBeVisible({ timeout: 5000 });
    // At least one component (runtime, db, hatchet, llm, etc.)
    const healthItems = page.locator('li:has-text("OK"), li:has-text("Down")');
    await expect(healthItems.first()).toBeVisible({ timeout: 3000 });
  });

  test("Overview has First Run Guide with Quick Start link (F-5)", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByRole("heading", { name: "First Run Guide" })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole("link", { name: "Quick Start" })).toBeVisible();
    await expect(page.getByRole("link", { name: "SKILL.md Guide" })).toBeVisible();
  });

  test("Overview attempts WebSocket connection (N-7)", async ({ page }) => {
    const wsUrls: string[] = [];
    page.on("websocket", (ws) => {
      wsUrls.push(ws.url());
    });
    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByRole("main").getByRole("heading", { name: "Overview" })).toBeVisible();
    await page.waitForTimeout(1500);
    const apiWs = wsUrls.filter((u) => u.includes("/api/v1/ws"));
    expect(apiWs.length).toBeGreaterThanOrEqual(1);
  });

  // --- Deep tests: Governance ---
  test("Governance has Circuit Breakers section (F-8)", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Governance" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Governance" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Circuit Breakers" })).toBeVisible({ timeout: 5000 });
  });

  test("Governance has Capability Visibility Matrix (F-9)", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Governance" }).click();
    await expect(page.getByRole("heading", { name: "Capability Visibility Matrix" })).toBeVisible({ timeout: 5000 });
  });

  // --- Deep tests: Ledger with mocked data ---
  test("Ledger with mock data: Table/Timeline toggle and record detail (F-10, F-12)", async ({ page }) => {
    const mockLedger = {
      items: [
        {
          id: "rec-1",
          timestamp: "2026-03-04T12:00:00Z",
          agent: "agent-a",
          capability: "cap-x",
          status: "success",
          cost_usd: 0.01,
          model: "gpt-4",
          latency_ms: 100,
          input: "in",
          output: "out",
          reasoning: "reason",
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    };

    await page.route("**/api/v1/ledger*", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockLedger) });
    });

    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Ledger", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Execution Records" })).toBeVisible({ timeout: 5000 });
    // Table/Timeline toggle
    await expect(page.getByRole("button", { name: "Table" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Timeline" })).toBeVisible();
    // Click record -> detail panel
    await page.getByRole("cell", { name: "agent-a" }).or(page.getByText("agent-a")).first().click();
    await expect(page.getByRole("heading", { name: "Execution Detail" })).toBeVisible();
    await expect(page.getByText("Record: rec-1")).toBeVisible();
    await expect(page.getByText("Agent: agent-a")).toBeVisible();
  });

  test("Ledger with mock data: pagination triggers offset request (F-13)", async ({ page }) => {
    const mockLedgerPage1 = {
      items: Array.from({ length: 20 }, (_, i) => ({
        id: `rec-${i}`,
        timestamp: "2026-03-04T12:00:00Z",
        agent: "agent-a",
        capability: "cap-x",
        status: "success",
        cost_usd: 0.01,
        model: "gpt-4",
        latency_ms: 100,
        input: "",
        output: "",
        reasoning: "",
      })),
      total: 25,
      limit: 20,
      offset: 0,
    };

    const ledgerUrls: string[] = [];
    await page.route("**/api/v1/ledger*", async (route) => {
      ledgerUrls.push(route.request().url());
      const offset = new URL(route.request().url()).searchParams.get("offset") || "0";
      const body =
        offset === "0"
          ? mockLedgerPage1
          : {
              items: mockLedgerPage1.items.slice(0, 5),
              total: 25,
              limit: 20,
              offset: 20,
            };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    });

    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByRole("heading", { name: "Execution Records" })).toBeVisible({ timeout: 5000 });
    const beforeNext = ledgerUrls.length;
    await page.getByRole("button", { name: "Next" }).click();
    await page.waitForTimeout(400);
    const offset20 = ledgerUrls.filter((u) => u.includes("offset=20") || u.includes("offset%3D20"));
    expect(offset20.length).toBeGreaterThan(0);
  });

  // --- Deep tests: Network / no unexpected errors ---
  test("Overview and main nav: no unexpected 4xx/5xx on API calls", async ({ page }) => {
    const failed: { url: string; status: number }[] = [];
    page.on("response", (res) => {
      const u = res.url();
      if (u.includes("/api/v1/") && res.status() >= 400) {
        failed.push({ url: u, status: res.status() });
      }
    });

    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByRole("main").getByRole("heading", { name: "Overview" })).toBeVisible();
    await page.getByRole("link", { name: "Governance" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Governance" })).toBeVisible();
    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Ledger", exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Agents" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Agents", exact: true })).toBeVisible();
    await page.waitForTimeout(500);

    // Known acceptable failures: agents/{id}, triggers (500 when no DB); ws (404 when uvicorn has no websockets)
    const unexpected = failed.filter(
      (f) =>
        !f.url.match(/\/agents\/[^/]+\/?$/) &&
        !f.url.includes("/triggers") &&
        !f.url.includes("/api/v1/ws")
    );
    expect(unexpected).toEqual([]);
  });

  // --- Deep tests: Settings structure ---
  test("Settings shows runtime, database, version sections", async ({ page }) => {
    await page.goto(`${baseUrl}/console/`);
    await page.getByRole("link", { name: "Settings" }).click();
    await expect(page.getByRole("main").getByRole("heading", { name: "Settings" })).toBeVisible();
    // Settings page has key sections
    await expect(page.getByText(/runtime|database|version/i).first()).toBeVisible({ timeout: 5000 });
  });
});
