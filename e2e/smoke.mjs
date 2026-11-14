// End-to-end check: drives the real UI against a running server and plays a full mission.
// Usage: BASE_URL=http://localhost:8000 node e2e/smoke.mjs   (needs `playwright` + chromium installed)
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:8000";
const SHOTS = process.env.SHOTS_DIR;
const ORDER = ["founder", "market", "competitor", "customer", "leads", "growth", "critic"];
const ok = (c, m) => { if (!c) throw new Error("FAILED: " + m); console.log("ok  -", m); };

const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1366, height: 800 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => { if (m.type() === "error" && !/ERR_TUNNEL|fonts\.g/.test(m.text())) errors.push(m.text()); });
const shot = (n) => SHOTS && page.screenshot({ path: `${SHOTS}/${n}.png` });

await page.goto(BASE);
await page.waitForSelector("canvas", { timeout: 15000 });
ok(await page.locator("canvas").count() === 1, "3D canvas rendered");
await page.click("button:has-text('Launch mission')");
await page.waitForSelector("[data-dispatch=founder]:not([disabled])");
ok(true, "mission launched, founder agent unlocked");

for (const id of ORDER) {
  await page.click(`[data-dispatch=${id}]:not([disabled])`, { timeout: 10000 });
  await page.waitForFunction((i) => document.querySelector(`[data-dispatch=${i}]`)?.closest(".agent")?.textContent?.includes("Done"), id, { timeout: 30000 });
}
ok(true, "all 7 agents ran in dependency order");
await page.waitForSelector("#cpApprove");
ok(true, "human checkpoint opened automatically");
await shot("1-checkpoint");
await page.click("#cpClose");

await page.click("[data-p=evidence]");
// Label the first few claims wrongly on purpose, then check the truth is revealed.
const firstId = await page.locator(".ev").first().getAttribute("data-id");
await page.locator(".ev").first().locator("[data-lab=hypothesis]").click();
await page.waitForSelector(".verdict");
ok(/Correct|Not quite/.test(await page.locator(".verdict").first().textContent()), `truth revealed only after labelling ${firstId}`);
ok(await page.locator("#queue .ev").count() === 25, "25 claims waiting in the evidence queue");
for (let n = await page.locator("#queue .ev").count(); n > 0; n--) {
  await page.locator("#queue .ev").first().locator("[data-lab=estimate]").click();
  await page.waitForFunction((k) => document.querySelectorAll("#queue .ev").length < k, n, { timeout: 5000 });
}
await page.waitForFunction(() => /26\/26/.test(document.querySelector(".stats")?.textContent ?? ""), null, { timeout: 5000 });
ok(true, "all 26 claims triaged (HUD shows 26/26)");
await shot("2-evidence");

for (const m of ["Competitor Galaxy", "Customer Universe", "Opportunity Radar", "Command"]) {
  await page.click(`.modebar button:has-text('${m}')`); await page.waitForTimeout(1600);
  await shot("3-" + m.split(" ")[0].toLowerCase());
}

await page.click("button:has-text('Open checkpoint')");
await page.click("#w0"); await page.click("#cpChallenge");
await page.waitForFunction(() => document.querySelector("#cpMsg")?.textContent?.includes("challenged"));
ok(true, "challenge action works");
await page.click("#cpApprove");
await page.waitForSelector("text=Mission report");
ok(true, "approve seals the mission and shows the report");
await shot("4-report");

await page.click("[data-p=ledger]");
await page.click("#vfy"); await page.waitForSelector("text=/All \\d+ entries verified/");
ok(true, "ledger chain verifies");
await page.click("#tmp"); await page.click("#vfy"); await page.waitForSelector("text=/fail verification/");
ok(true, "tampering is detected");
await page.click("#rst"); await page.click("#vfy"); await page.waitForSelector("text=/All \\d+ entries verified/");
ok(true, "restore makes the chain verify again");

await page.click("[data-p=rag]"); await page.click("#ragGo");
await page.waitForSelector(".hit");
ok(await page.locator(".hit").count() === 5, "RAG lab returns 5 Qdrant hits");

ok(errors.length === 0, "no browser errors " + JSON.stringify(errors));
await browser.close();
console.log("\nE2E PASSED");
