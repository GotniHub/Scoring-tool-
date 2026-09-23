import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const { SKILL_DIR, TMP_DIR, RUNTIME_PYTHON } = process.env;
if (!path.isAbsolute(SKILL_DIR ?? "") || !path.isAbsolute(TMP_DIR ?? "")) {
  throw new Error("SKILL_DIR and TMP_DIR must be absolute paths");
}

const workspaceDir = path.resolve(TMP_DIR, "..");
const assetDir = path.join(TMP_DIR, "assets");
const outputDir = path.join(workspaceDir, "deliverables");
const finalPath = path.join(outputDir, "Brand_Scorecard_Presentation_EN_2026-09-17.pptx");

const { resolvePresentationFont, makeNativeBulletParagraphs, finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
);

const fontFamily = resolvePresentationFont({ fontFamily: "Arial" });
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

const C = {
  navy: "#182541",
  deep: "#0B234B",
  blue: "#2C4694",
  mid: "#506BB4",
  pale: "#EEF2FF",
  ink: "#152039",
  muted: "#64748B",
  line: "#DDE3ED",
  green: "#16856A",
  amber: "#C47A18",
  red: "#C34343",
  white: "#FFFFFF",
  soft: "#F7F9FC",
};

const assets = {};
for (const name of [
  "overview.png",
  "assessment.png",
  "portfolio.png",
  "comparison.png",
  "framework.png",
  "exports.png",
  "database-browser.png",
]) {
  assets[name] = new Uint8Array(await fs.readFile(path.join(assetDir, name)));
}
const logo = new Uint8Array(await fs.readFile(path.join(workspaceDir, "LOGO.png")));

function addBox(slide, x, y, w, h, fill, radius = 0, lineFill = "none", shadow = undefined) {
  return slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { fill: lineFill, width: lineFill === "none" ? 0 : 1 },
    borderRadius: radius,
    ...(shadow ? { shadow } : {}),
  });
}

function addText(slide, text, x, y, w, h, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: fontFamily,
    fontSize: options.fontSize ?? 24,
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
    autoFit: "none",
    ...(options.italic ? { italic: true } : {}),
  };
  return shape;
}

function addBullets(slide, items, x, y, w, h, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = makeNativeBulletParagraphs(items, {
    marginLeftPoints: 18,
    hangingPoints: 9,
    spaceAfterPoints: options.spaceAfterPoints ?? 12,
  });
  shape.text.style = {
    typeface: fontFamily,
    fontSize: options.fontSize ?? 23,
    color: options.color ?? C.ink,
    autoFit: "none",
  };
  return shape;
}

function addHeader(slide, title, section, slideNumber) {
  slide.background.fill = C.white;
  addBox(slide, 0, 0, 18, 720, C.blue);
  addText(slide, section.toUpperCase(), 64, 34, 500, 24, { fontSize: 15, bold: true, color: C.mid });
  addText(slide, title, 64, 63, 1110, 60, { fontSize: 44, bold: true, color: C.navy });
  addBox(slide, 64, 128, 1152, 2, C.line);
  addText(slide, String(slideNumber).padStart(2, "0"), 1170, 670, 46, 20, { fontSize: 14, color: C.muted });
}

function addScreenshot(slide, assetName, x, y, w, h, alt) {
  addBox(slide, x - 5, y - 5, w + 10, h + 10, C.white, 16, C.line, "2px 7px 19px #182541/14");
  return slide.images.add({
    blob: assets[assetName],
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left: x, top: y, width: w, height: h },
    geometry: "roundRect",
    borderRadius: 12,
  });
}

function addNotes(slide, text) {
  slide.speakerNotes.textFrame.setText(text);
  slide.speakerNotes.setVisible(true);
}

// Slide 1
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addBox(slide, 760, 0, 520, 720, C.navy);
  slide.images.add({ blob: logo, contentType: "image/png", alt: "Advent+ Africa logo", fit: "contain", position: { left: 62, top: 52, width: 300, height: 72 } });
  addText(slide, "Brand Scorecard", 62, 212, 650, 86, { fontSize: 68, bold: true, color: C.navy });
  addText(slide, "A practical tool for brand assessment and portfolio decisions", 64, 317, 610, 100, { fontSize: 30, color: C.muted });
  addText(slide, "Project presentation", 64, 548, 420, 28, { fontSize: 20, bold: true, color: C.blue });
  addText(slide, "September 2026", 64, 588, 300, 28, { fontSize: 18, color: C.muted });
  addText(slide, "ASSESS\nCOMPARE\nDECIDE", 818, 182, 380, 260, { fontSize: 54, bold: true, color: C.white });
  addBox(slide, 818, 478, 230, 4, C.mid);
  addText(slide, "One shared scoring method\nOne persistent data source", 818, 505, 350, 80, { fontSize: 22, color: "#DCE5FF" });
  addNotes(slide, "Today I will present the Brand Scorecard. It gives the commercial team one place to assess brands, compare results, and support portfolio decisions. The tool combines a clear scoring method with a database, dashboards, and export options. I will show the full user journey and explain how the data stays available between sessions.\n\nSource: Brand Scorecard application v2.5.");
}

// Slide 2
{
  const slide = presentation.slides.add();
  addHeader(slide, "Why the project was needed", "Business need", 2);
  addText(slide, "The starting point", 70, 165, 500, 38, { fontSize: 28, bold: true, color: C.navy });
  addBullets(slide, [
    "Brand information was spread across files and personal notes.",
    "Teams needed a consistent way to compare very different brands.",
    "Manual updates made follow-up slow and difficult to trace.",
    "Management needed a clear view of priorities and risks.",
  ], 70, 218, 510, 330, { fontSize: 24 });
  addBox(slide, 630, 160, 2, 430, C.line);
  addText(slide, "The project response", 690, 165, 500, 38, { fontSize: 28, bold: true, color: C.navy });
  const responses = [
    ["01", "Structured assessment", "The same questions and scales for every brand."],
    ["02", "Persistent data", "Every saved assessment returns in the next session."],
    ["03", "Decision views", "Scores, recommendations, comparisons, and exports."],
  ];
  responses.forEach(([number, title, body], index) => {
    const y = 225 + index * 118;
    addText(slide, number, 690, y, 70, 42, { fontSize: 32, bold: true, color: C.mid });
    addText(slide, title, 770, y, 390, 34, { fontSize: 25, bold: true, color: C.ink });
    addText(slide, body, 770, y + 38, 390, 56, { fontSize: 20, color: C.muted });
  });
  addNotes(slide, "The project started with a simple business problem. Brand information was stored in different files, and it was hard to compare brands in the same way. The new application creates one structured process. It keeps the data, calculates the scores, and gives management a clear view of each brand. This reduces manual work and makes discussions more consistent.\n\nSource: project workflow and Brand Scorecard application.");
}

// Slide 3
{
  const slide = presentation.slides.add();
  addHeader(slide, "Guided brand assessment", "Data capture", 3);
  addText(slide, "One form covers the full assessment", 64, 156, 420, 70, { fontSize: 31, bold: true, color: C.navy });
  addBullets(slide, [
    "Select one or more strategic categories and brand families.",
    "Assign a commercial owner and an assessment status.",
    "Complete descriptive and strategic criteria in clear sections.",
    "Add comments and evidence before saving the assessment.",
  ], 64, 247, 390, 330, { fontSize: 22 });
  addText(slide, "The same screen supports new brands and later updates.", 64, 596, 410, 54, { fontSize: 20, bold: true, color: C.blue });
  addScreenshot(slide, "assessment.png", 492, 150, 724, 500, "Guided brand assessment screen");
  addNotes(slide, "This is the main assessment screen. The user first selects the categories and brand families. A brand can belong to more than one category or family. The commercial owner and status make responsibility clear. The assessment is divided into sections, so the user can work through the criteria in a logical order. When the user saves, the complete record goes to the database.\n\nSource: Brand Scorecard application v2.5.");
}

// Slide 4
{
  const slide = presentation.slides.add();
  addHeader(slide, "Transparent scoring framework", "Method", 4);
  addScreenshot(slide, "framework.png", 64, 150, 720, 500, "Scoring framework screen");
  addText(slide, "27", 835, 168, 150, 64, { fontSize: 54, bold: true, color: C.blue });
  addText(slide, "criteria in total", 835, 228, 300, 34, { fontSize: 22, color: C.muted });
  addText(slide, "7 descriptive criteria", 835, 300, 340, 38, { fontSize: 26, bold: true, color: C.navy });
  addText(slide, "Scores from 1 to 4", 835, 342, 340, 32, { fontSize: 21, color: C.muted });
  addText(slide, "20 strategic criteria", 835, 414, 340, 38, { fontSize: 26, bold: true, color: C.navy });
  addText(slide, "Scores from -2 to +2", 835, 456, 340, 32, { fontSize: 21, color: C.muted });
  addText(slide, "Missing answers stay blank and do not change the average.", 835, 535, 350, 74, { fontSize: 21, bold: true, color: C.green });
  addNotes(slide, "The scoring method stays visible inside the application. There are seven descriptive criteria and twenty strategic criteria. The descriptive scale runs from one to four. The strategic scale runs from minus two to plus two. Each definition can be reviewed in the Scoring Framework page. If a criterion is not assessed, it remains blank and does not reduce or increase the average.\n\nSource: Brand Scorecard scoring framework.");
}

// Slide 5
{
  const slide = presentation.slides.add();
  addHeader(slide, "Brand level overview", "Dashboard", 5);
  addScreenshot(slide, "overview.png", 64, 148, 1152, 500, "Overview with brand selector and brand indicators");
  addText(slide, "The selector controls the indicators, decision matrix, recommendations, and table.", 118, 660, 1040, 32, { fontSize: 21, bold: true, color: C.blue });
  addNotes(slide, "The Overview now works at brand level. The user can select one or several brands. Each selected brand has its own expandable section with descriptive score, strategic score, completeness, recommendation, and status. The same filter also updates the charts and the recommendation table. This makes the page useful for both a focused brand review and a wider portfolio discussion.\n\nSource: Brand Scorecard Overview.");
}

// Slide 6
{
  const slide = presentation.slides.add();
  addHeader(slide, "Portfolio register", "Portfolio control", 6);
  addText(slide, "A shared view of all active brands", 64, 158, 390, 72, { fontSize: 31, bold: true, color: C.navy });
  addBullets(slide, [
    "Filter by category, family, commercial owner, recommendation, or status.",
    "Compare completeness before a review meeting.",
    "See the main scores and comments in one table.",
    "Open the assessment page to update a record.",
  ], 64, 248, 390, 310, { fontSize: 22 });
  addText(slide, "This screen creates a simple operating list for the commercial team.", 64, 584, 390, 64, { fontSize: 20, bold: true, color: C.green });
  addScreenshot(slide, "portfolio.png", 492, 150, 724, 500, "Portfolio register with filters and brand records");
  addNotes(slide, "The Portfolio page gives the team one operating list. Users can filter by category, brand family, commercial owner, recommendation, and status. This helps the team prepare review meetings and focus on the records that need action. The table also shows completeness, which makes missing work easy to see. Users return to the assessment page when they need to update a brand.\n\nSource: Brand Scorecard Portfolio page.");
}

// Slide 7
{
  const slide = presentation.slides.add();
  addHeader(slide, "Multi-brand comparison", "Analysis", 7);
  addScreenshot(slide, "comparison.png", 64, 150, 760, 500, "Multi-brand strategic radar comparison");
  addText(slide, "One chart, several brands", 866, 165, 330, 54, { fontSize: 30, bold: true, color: C.navy });
  addBullets(slide, [
    "Select up to eight brands.",
    "Each brand uses a different color.",
    "Compare five strategic pillars on one radar.",
    "Use the other tabs for ranking and heatmaps.",
  ], 866, 244, 320, 270, { fontSize: 22 });
  addText(slide, "The legend and hover details make each profile easy to identify.", 866, 548, 320, 78, { fontSize: 20, bold: true, color: C.blue });
  addNotes(slide, "The Comparative Analysis page supports several views. This example shows the strategic profile radar. The user can select several brands, and each brand receives a different color. The chart compares attractiveness, operations, relationships, solvability, and execution fit. The other tabs provide a ranking, detailed descriptive scores, and strategic pillar heatmaps.\n\nSource: Brand Scorecard Comparative Analysis page.");
}

// Slide 8
{
  const slide = presentation.slides.add();
  addHeader(slide, "Persistent SQLite database", "Data storage", 8);
  addText(slide, "The database starts automatically with the app", 64, 156, 430, 82, { fontSize: 31, bold: true, color: C.navy });
  addBullets(slide, [
    "Every save or update writes the complete assessment.",
    "Brand names stay unique in the database.",
    "The app stores scoring settings as well as brand records.",
    "DB Browser for SQLite provides a direct read-only view.",
  ], 64, 255, 420, 290, { fontSize: 22 });
  addText(slide, "Default file", 64, 568, 150, 28, { fontSize: 18, bold: true, color: C.mid });
  addText(slide, "data/brand_scorecard.db", 64, 602, 390, 34, { fontSize: 22, bold: true, color: C.ink });
  addScreenshot(slide, "database-browser.png", 515, 150, 701, 500, "DB Browser for SQLite showing the Brand Scorecard database structure");
  addNotes(slide, "The application uses SQLite for persistent storage. There is no separate database server to start. The database file opens automatically when the app starts. Each save writes the full brand assessment, and the settings are stored in a separate table. DB Browser can open the file for inspection. Normal changes should still be made through the application, because the app protects the expected data structure.\n\nSource: database.py and local DB Browser view.");
}

// Slide 9
{
  const slide = presentation.slides.add();
  addHeader(slide, "Import and export", "Data exchange", 9);
  addScreenshot(slide, "exports.png", 64, 150, 740, 500, "Export page with CSV and Excel options");
  addText(slide, "A flexible daily workflow", 846, 164, 340, 50, { fontSize: 30, bold: true, color: C.navy });
  const workflow = [
    ["1", "Import", "Load historical or batch data from CSV or Excel."],
    ["2", "Work", "Review and update brands in the application."],
    ["3", "Export", "Create a CSV extract or a complete Excel review pack."],
  ];
  workflow.forEach(([number, title, body], index) => {
    const y = 244 + index * 112;
    addText(slide, number, 846, y, 42, 40, { fontSize: 29, bold: true, color: C.blue });
    addText(slide, title, 902, y, 260, 34, { fontSize: 25, bold: true, color: C.ink });
    addText(slide, body, 902, y + 36, 270, 56, { fontSize: 19, color: C.muted });
  });
  addText(slide, "The database remains the main source between imports and exports.", 846, 596, 330, 58, { fontSize: 20, bold: true, color: C.green });
  addNotes(slide, "Import and export remain available around the database. Import is useful for historical data or larger updates. The application then becomes the main place for daily work. Export creates a simple CSV file or a complete Excel review pack with scores, rankings, settings, and methodology. This gives the team flexibility without losing the persistent database.\n\nSource: Brand Scorecard Exports page and import workflow.");
}

// Slide 10
{
  const slide = presentation.slides.add();
  addHeader(slide, "Controls and data safety", "Governance", 10);
  const items = [
    ["SAVE", "Automatic persistence", "Saved assessments remain available after the application closes."],
    ["UPDATE", "Controlled changes", "Existing brands can be edited without creating duplicate records."],
    ["DELETE", "Explicit confirmation", "The delete button stays disabled until the user confirms the action."],
    ["BACKUP", "Portable outputs", "CSV and Excel exports support reviews and backup routines."],
  ];
  items.forEach(([tag, title, body], index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const x = 78 + col * 570;
    const y = 175 + row * 215;
    addText(slide, tag, x, y, 130, 26, { fontSize: 16, bold: true, color: index === 2 ? C.red : C.mid });
    addText(slide, title, x, y + 38, 480, 40, { fontSize: 29, bold: true, color: C.navy });
    addText(slide, body, x, y + 90, 470, 76, { fontSize: 21, color: C.muted });
    if (col === 0) addBox(slide, 615, y, 2, 150, C.line);
  });
  addText(slide, "Recommended rule: use the application for changes and DB Browser for inspection.", 160, 632, 960, 36, { fontSize: 22, bold: true, color: C.green });
  addNotes(slide, "The project includes basic controls for safe daily use. Saving is automatic, and updates reuse the same brand record. Deleting a brand requires an explicit confirmation. Export files can support review meetings and backup routines. The recommended rule is simple: users should make changes in the application and use DB Browser only to inspect the database.\n\nSource: Brand Scorecard database and delete workflow.");
}

// Slide 11
{
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  addText(slide, "Business value and next steps", 70, 58, 950, 64, { fontSize: 48, bold: true, color: C.white });
  addBox(slide, 70, 140, 1140, 2, "#41547C");
  addText(slide, "Business value", 70, 188, 470, 46, { fontSize: 30, bold: true, color: "#AFC3FF" });
  addBullets(slide, [
    "Faster preparation for brand review meetings.",
    "Comparable scores across the full portfolio.",
    "Clear ownership and visible assessment status.",
    "Reusable data for analysis and reporting.",
  ], 70, 252, 500, 300, { fontSize: 23, color: C.white });
  addBox(slide, 624, 180, 2, 390, "#41547C");
  addText(slide, "Suggested next steps", 680, 188, 470, 46, { fontSize: 30, bold: true, color: "#AFC3FF" });
  addBullets(slide, [
    "Confirm the users and their access needs.",
    "Choose a shared deployment for the commercial team.",
    "Agree on a regular review and backup cycle.",
    "Train users with a small set of real brands.",
  ], 680, 252, 500, 300, { fontSize: 23, color: C.white });
  addText(slide, "The result is one consistent process from assessment to decision.", 70, 615, 1100, 42, { fontSize: 28, bold: true, color: C.white });
  addNotes(slide, "The main value is a faster and more consistent review process. The team can compare brands using the same method, see who owns each assessment, and reuse the data for reporting. The next step is to agree on the users, choose the shared deployment, define a review and backup cycle, and train the team with a small group of real brands. This will turn the tool into a regular commercial process.\n\nSource: project scope and recommended implementation steps.");
}

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });
const stagingDir = path.join(TMP_DIR, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "brand-scorecard-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 11,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
};

const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  requiredNativeTableOwnerSlides: [],
  fontPolicy: { basis: "design", families: [fontFamily] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "Brand_Scorecard_Presentation_EN_2026-09-17.validation.json"),
});

console.log(JSON.stringify({ finalPath, result }, null, 2));
