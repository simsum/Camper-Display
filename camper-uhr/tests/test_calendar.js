const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "frontend", "js", "screens", "calendar.js"),
  "utf8",
);
const context = vm.createContext({ Date, Intl, Math, String, Number, JSON, console });
vm.runInContext(source, context);

const expectedDates = ["2026-03-20", "2026-06-21", "2026-09-23", "2026-12-21"];
expectedDates.forEach((expected, index) => {
  const actual = context.vacationSeasonTransition(2026, index).toISOString().slice(0, 10);
  assert.equal(actual, expected);
});

const start = context.vacationLocalDate("2026-12-28");
const end = context.vacationLocalDate("2027-01-04");
assert.equal(context.vacationDayDifference(start, end) + 1, 8);
assert.equal(context.vacationFormatRange(start, end), "28. Dezember – 04. Januar 2027");

const manual = { id: "manual", name: "Herbsttour", destination: "Bozen", start_date: "2026-10-03", end_date: "2026-10-12", enabled: true };
const imported = { ...manual, id: "icloud-test" };
assert.equal(context.vacationNormalizeTrips({ vacations: [manual] }, { enabled: true, vacations: [imported] }).length, 1);
assert.equal(context.vacationNormalizeTrips({ vacations: [] }, { enabled: false, vacations: [imported] }).length, 0);
assert.equal(context.vacationNormalizeTrips({ vacations: [] }, { enabled: true, vacations: [imported] })[0].destination, "Bozen");
assert.equal(context.vacationEscape('<img src=x onerror="bad()">').includes("<img"), false);
console.log("calendar tests: ok");
