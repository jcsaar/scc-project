import { expect, test } from "@playwright/test";

test("chat-first flow shows synchronized thinking and a safe privacy receipt", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "What can I help you protect?" })).toBeVisible();

  await page.getByRole("button", { name: "Review a private architecture" }).click();
  await expect(page.getByText("Reading your request locally…")).toBeVisible();
  await expect(page.getByText("Checking the zero-trust privacy border…")).toBeVisible();
  await expect(page.getByText("Sending approved context to Cloud AI…")).toBeVisible();
  await expect(page.getByText("Verifying the response locally…")).toBeVisible();
  await expect(page.getByText(/Partition write ownership/)).toBeVisible();
  await expect(page.getByText("Border checked")).toBeVisible();
  await expect(page.getByText("Raw facts to cloud")).toBeVisible();

  await expect(page.locator("pre")).toContainText("15k-20k");
  await expect(page.locator("pre")).not.toContainText("Northstar");
  await expect(page.locator("pre")).not.toContainText("18,274");
});

test("blocked requests stay local and show a hard privacy stop", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Try a blocked request" }).click();

  await expect(page.getByText("Transmission blocked")).toBeVisible();
  await expect(page.getByRole("complementary").getByText(/Cloud transmission was blocked/)).toBeVisible();
  await expect(page.getByText("Raw facts to cloud")).toBeVisible();
  await expect(page.locator(".payload-details")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText("synthetic-demo-secret");
});

test("new chat clears the active conversation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Review a private architecture" }).click();
  await expect(page.getByText(/Partition write ownership/)).toBeVisible();

  await page.getByRole("button", { name: "New chat" }).click();
  await expect(page.getByRole("heading", { name: "What can I help you protect?" })).toBeVisible();
  await expect(page.getByText(/Partition write ownership/)).not.toBeVisible();
});
