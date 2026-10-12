// One-time seed of the 15 listings into boards/<boardId>/apartments.
// Usage: node seed.mjs <boardId>
// Auth: uses the signed-in gcloud account (bypasses security rules, as the admin SDK would).
// Existing documents are never overwritten (exists:false precondition).
import { execSync } from "node:child_process";

const PROJECT = "agamim-apartments";
const boardId = process.argv[2];
if (!/^[A-Za-z0-9]{20,64}$/.test(boardId || "")) {
  console.error("usage: node seed.mjs <boardId>");
  process.exit(1);
}

const M = "https://www.madlan.co.il";
const Y = "https://www.yad2.co.il";
// [address, rooms, floor, sqm, price, prevPrice, source, publisher, url, listingNote]
const rows = [
  ["עמק האלה 65", 3, "7", 93, 1610000, null, "מדלן", "", `${M}/for-sale/%D7%A9%D7%9B%D7%95%D7%A0%D7%94-%D7%90%D7%92%D7%9E%D7%99%D7%9D-%D7%90%D7%A9%D7%A7%D7%9C%D7%95%D7%9F-%D7%99%D7%A9%D7%A8%D7%90%D7%9C/3-bd`, "3 חדרים בלבד, רק אם הקונה גמיש"],
  ["שקמים ואגמים", 4, "4", 116, 1620000, null, "יד2", "משרד תיווך", `${Y}/realestate/agency/6433714/forsale`, "קישור לעמוד המשרד, לוודא שזה באגמים"],
  ["שקמים ואגמים", 4, "6", 115, 1620000, null, "יד2", "משרד תיווך", `${Y}/realestate/agency/4781314/broker/1111113605/forsale`, "קישור לעמוד המתווך, לוודא שזה באגמים"],
  ["שקמים ואגמים", 4, "5", 110, 1630000, null, "יד2", "משרד תיווך", `${Y}/realestate/agency/2241058/broker/678476/forsale`, "קישור לעמוד המתווך, לוודא שזה באגמים"],
  ["עמק יזרעאל", 4, "2", 111, 1680000, null, "מדלן", "מתווך, בלעדיות", `${M}/listings/SudYtL1zfTH`, "בניין בוטיק של אביסרור, 10 דיירים, הליכה לאגם"],
  ["שדרות עמק חפר", 4, "3 מתוך 6", 118, 1690000, null, "יד2", "", `${Y}/realestate/item/south/yh5ez228`, "מטבח משודרג, מחסן, מושכרת ב-4,200, כניסה גמישה"],
  ["שקמים ואגמים", 4, "3", 118, 1690000, null, "יד2", "משרד תיווך", `${Y}/realestate/agency/6671257/forsale`, "אולי אותה דירה כמו מספר 6"],
  ["בקעת רימון 16", 4, "7", 120, 1720000, 1870000, "מדלן", "תיווך", `${M}/listings/tl9duWwiujH`, "המחיר ירד ב-150 אלף"],
  ["שדרות עמק חפר 47", 4, "2", 117, 1740000, null, "מדלן", "", `${M}/listings/zPdSBkzcEpk`, ""],
  ["עמק יזרעאל 46", 4, "8", 121, 1780000, null, "מדלן", "", `${M}/listings/pmagxeK0Htc`, ""],
  ["עמק האלה 16", 4, "6", 116, 1780000, null, "מדלן", "", `${M}/listings/LATQg3a26cq`, ""],
  ["עמק יזרעאל 36", 4, "3", 106, 1780000, null, "מדלן", "", `${M}/listings/ucaXwXYsXQF`, ""],
  ["עמק האלה 1", 4, "2", 115, 1780000, null, "מדלן", "תיווך", `${M}/listings/7yO8twxxzL0`, ""],
  ["שדרות עמק יזרעאל 26", 4, "7", 107, 1790000, null, "מדלן", "בלעדיות", `${M}/listings/TVzNmFb9xF1`, ""],
  ["עמק חפר 1", 4, "1", 108, 1795000, null, "מדלן", "תיווך", `${M}/listings/Xd7PLRSat7k`, ""],
];

const val = (v) =>
  v === null ? { nullValue: null }
  : typeof v === "number" ? { integerValue: String(v) }
  : { stringValue: v };

const base = `projects/${PROJECT}/databases/(default)/documents`;
const writes = rows.map((r, i) => {
  const id = String(i + 1).padStart(2, "0");
  const [address, rooms, floor, sqm, price, prevPrice, source, publisher, url, listingNote] = r;
  const data = {
    id, address, rooms, floor, sqm, price, prevPrice, source, publisher, url, listingNote,
    status: "לא נבדק", checkedBy: "", contact: "", notes: "",
  };
  return {
    update: {
      name: `${base}/boards/${boardId}/apartments/${id}`,
      fields: Object.fromEntries(Object.entries(data).map(([k, v]) => [k, val(v)])),
    },
    updateTransforms: [{ fieldPath: "updatedAt", setToServerValue: "REQUEST_TIME" }],
    currentDocument: { exists: false },
  };
});

const env = { ...process.env };
delete env.CLOUDSDK_AUTH_ACCESS_TOKEN;
const token = execSync("gcloud auth print-access-token", { env }).toString().trim();
const res = await fetch(`https://firestore.googleapis.com/v1/${base}:commit`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}`, "x-goog-user-project": PROJECT, "Content-Type": "application/json" },
  body: JSON.stringify({ writes }),
});
const body = await res.json();
if (!res.ok) {
  console.error(res.status, JSON.stringify(body.error || body));
  process.exit(1);
}
console.log(`seeded ${body.writeResults.length} apartments`);
