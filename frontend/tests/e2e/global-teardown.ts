import { rm } from "node:fs/promises";

export default async function globalTeardown() {
  const databasePath = process.env.PACE_E2E_DB_PATH;
  if (!databasePath) return;
  try {
    await rm(databasePath, { force: true });
  } catch (error) {
    if (
      (error as NodeJS.ErrnoException).code !== "EBUSY" &&
      (error as NodeJS.ErrnoException).code !== "EPERM"
    )
      throw error;
  }
}
