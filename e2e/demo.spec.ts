import { expect, test } from "@playwright/test";

test("legitimate TrustSplit collaboration reveals only the approved payload", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Cloud AI never directly accesses private corporate data.")).toBeVisible();
  await page.getByRole("button", { name: "Run safely" }).click();
  await page.getByRole("button", { name: "Privacy Pipeline" }).click();
  await expect(page.getByRole("heading", { name: "Exact cloud payload" })).toBeVisible();
  await expect(page.locator("pre")).toContainText("15k-20k transactions per second");
  await expect(page.locator("pre")).not.toContainText("Northstar");
});

test("comparison modes truthfully show exposure", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Mode").selectOption("cloud_only");
  await page.getByRole("button", { name: "Run safely" }).click();
  await expect(page.getByText(/18,274 TPS/)).toBeVisible();
  await expect(page.getByText("ALLOW")).toBeVisible();

  await page.getByLabel("Mode").selectOption("basic_redaction");
  await page.getByRole("button", { name: "Run safely" }).click();
  await expect(page.getByText(/18,274 TPS/)).toBeVisible();
  await expect(page.getByText(/Project \[REDACTED\] serves Customer \[REDACTED\]/)).toBeVisible();
  await expect(page.getByText(/Northstar/)).not.toBeVisible();

  await page.getByLabel("Mode").selectOption("local_only");
  await page.getByRole("button", { name: "Run safely" }).click();
  await expect(page.getByText("Nothing left the device in Local Only mode.")).toBeVisible();
});

test("mosaic and malicious scenarios end in cumulative denial", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Collaboration" }).click();
  const runButtons = page.getByRole("button", { name: "Run scenario" });
  await runButtons.nth(1).click();
  await expect(page.getByText("Dana's request was denied using the shared trust-zone ledger.")).toBeVisible();
  await runButtons.nth(2).click();
  await expect(page.getByText("The cumulative-risk threshold stopped the narrowing sequence.")).toBeVisible();
});
