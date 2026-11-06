import { expect, test } from "@playwright/test";

test("register, manage activity, log training, export, and sign out", async ({
  page,
}) => {
  const email = `pace-${Date.now()}@example.com`;
  const password = "E2E-pace-account-2026!";

  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E Athlete");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByText("0", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "Log activity" }).first().click();
  await page.getByLabel("Title").fill("Audit run");
  await page.getByLabel("Duration (minutes)").fill("30");
  await page.getByLabel("Distance (km)").fill("5");
  await page.getByRole("button", { name: "Save activity" }).click();
  await expect(page.getByRole("heading", { name: "Audit run" })).toBeVisible();
  const activityPath = new URL(page.url()).pathname;

  await page.getByRole("link", { name: "Edit" }).click();
  await page.getByLabel("Title").fill("Updated audit run");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("heading", { name: "Updated audit run" }),
  ).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete activity" }).click();
  await expect(page).toHaveURL(/activities$/);

  await page.getByRole("link", { name: "Log activity" }).first().click();
  await page.getByLabel("Title").fill("Analytics run");
  await page.getByLabel("Duration (minutes)").fill("32");
  await page.getByLabel("Distance (km)").fill("5.4");
  await page.getByRole("button", { name: "Save activity" }).click();
  await expect(
    page.getByRole("heading", { name: "Analytics run" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Strength" }).click();
  await page.getByLabel("Workout name").fill("E2E strength");
  await page.getByLabel("Exercise name").fill("Squat");
  await page.getByLabel("Set 1 · reps").fill("5");
  await page.getByLabel("Weight (kg)").fill("60");
  await page.getByRole("button", { name: "Add set" }).click();
  await page.getByLabel("Set 2 · reps").fill("8");
  await page.getByLabel("Weight (kg)").nth(1).fill("40");
  await page.getByRole("button", { name: "Add exercise" }).click();
  await page.getByLabel("Exercise name").nth(1).fill("Push-up");
  await page.getByRole("button", { name: "Save workout" }).click();
  await expect(page.getByText("E2E strength")).toBeVisible();
  await expect(page.getByText("620 kg")).toBeVisible();

  await page.getByRole("link", { name: "Training", exact: true }).click();
  await page.getByLabel("Plan name").fill("E2E base plan");
  await page.getByRole("button", { name: "Create plan" }).click();
  await expect(page.getByLabel("Plan", { exact: true })).toHaveValue(/.+/);
  await page.getByLabel("Session").fill("Planned recovery run");
  await page
    .getByLabel("Date", { exact: true })
    .fill(new Date(Date.now() + 86_400_000).toISOString().slice(0, 10));
  await page.getByRole("button", { name: "Schedule" }).click();
  await expect(page.getByText("Planned recovery run")).toBeVisible();
  await page.getByRole("button", { name: "Mark done" }).click();
  await expect(page.getByText("Completed")).toBeVisible();

  await page.getByRole("link", { name: "Health" }).click();
  await page.getByLabel("Value (kg)").fill("72.5");
  await page.getByRole("button", { name: "Add measurement" }).click();
  await expect(page.getByText("72.500 kg")).toBeVisible();

  await page.getByRole("link", { name: "Analytics" }).click();
  await expect(
    page.getByRole("heading", { name: "Distance trend" }),
  ).toBeVisible();
  await expect(page.getByText("5.4 km")).toBeVisible();

  await page.getByRole("link", { name: "Settings" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  expect((await downloadPromise).suggestedFilename()).toBe(
    "pace-activities.csv",
  );

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/login/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/login/);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/dashboard/);
  expect(activityPath).toMatch(/^\/activities\//);
});

test("another account cannot read another user's activity", async ({
  page,
}) => {
  const firstEmail = `owner-${Date.now()}@example.com`;
  const password = "E2E-pace-account-2026!";
  await page.goto("/register");
  await page.getByLabel("Name").fill("Owner");
  await page.getByLabel("Email").fill(firstEmail);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: "Log activity" }).first().click();
  await page.getByLabel("Title").fill("Private run");
  await page.getByLabel("Duration (minutes)").fill("20");
  await page.getByRole("button", { name: "Save activity" }).click();
  await page.waitForURL(/\/activities\/[0-9a-f-]+$/);
  const activityId = new URL(page.url()).pathname.split("/").at(-1);

  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/register");
  await page.getByLabel("Name").fill("Other user");
  await page.getByLabel("Email").fill(`other-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/dashboard/);

  const status = await page.evaluate(async (id) => {
    const response = await fetch(
      `http://127.0.0.1:8010/api/v1/activities/${id}`,
      { credentials: "include" },
    );
    return response.status;
  }, activityId);
  expect(status).toBe(404);
  await page.goto(`/activities/${activityId}`);
  await expect(
    page.getByText("Activity not found", { exact: true }),
  ).toBeVisible();
});
