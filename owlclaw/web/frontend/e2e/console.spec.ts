import { test, expect } from "@playwright/test";

test("overview-governance-ledger navigation", async ({ page }) => {
  await page.goto("http://localhost:5173/console/");
  await expect(page.getByText("OwlClaw Console")).toBeVisible();
  await page.getByRole("link", { name: "Governance" }).click();
  await expect(page.getByText("Budget Trend")).toBeVisible();
  await page.getByRole("link", { name: "Ledger" }).click();
  await expect(page.getByPlaceholder("Filter by agent/capability/status")).toBeVisible();
});
