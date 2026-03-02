import { test, expect } from "@playwright/test";

test.describe("Console flow", () => {
  test("Overview -> Governance -> Ledger", async ({ page }) => {
    test.skip(!process.env.CONSOLE_E2E_BASE_URL, "Set CONSOLE_E2E_BASE_URL to run e2e.");
    const baseUrl = process.env.CONSOLE_E2E_BASE_URL as string;

    await page.goto(`${baseUrl}/console/`);
    await expect(page.getByText("Overview")).toBeVisible();

    await page.getByRole("link", { name: "Governance" }).click();
    await expect(page.getByText("Governance")).toBeVisible();

    await page.getByRole("link", { name: "Ledger" }).click();
    await expect(page.getByText("Ledger")).toBeVisible();
  });
});
