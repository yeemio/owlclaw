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
});
