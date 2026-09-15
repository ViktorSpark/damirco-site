/**
 * Школа продаж ДАМИР ГРУПП — сервер результатов (Google Apps Script).
 *
 * Что это: веб-приложение Apps Script, которое
 *   - GET  — отдаёт все результаты в формате JSON (для админ-страницы admin.html)
 *   - POST — принимает результат теста и пишет его в таблицу Google Sheets.
 *
 * Как запустить (один раз):
 *   1. Откройте https://script.google.com  → «Новый проект».
 *   2. Вставьте этот код в Code.gs.
 *   3. Создайте таблицу в Google Sheets (любую) и получите её URL.
 *   4. Нажмите «Развернуть» → «Новое развёртывание» → тип «Веб-приложение».
 *   5. Доступ: «Любой пользователь Интернета» (без логина — как договорились).
 *   6. Скопируйте URL веб-приложения вида
 *        https://script.google.com/macros/s/XXXX/exec
 *      и вставьте его в файл config.js на сайте:
 *        DG.ENDPOINT = "https://script.google.com/macros/s/XXXX/exec";
 *   7. Первый POST обычно даёт ошибку 302/404 в браузере — это нормально,
 *      повторное открытие работает. Тест сработает сразу.
 *
 * Таблица «Results» создаётся автоматически при первом POST.
 */

var SHEET_NAME = "Results";
var SPREADSHEET_ID = ""; // можно оставить пустым — используется активная таблица проекта

function getSheet_() {
  var ss = SPREADSHEET_ID ? SpreadsheetApp.openById(SPREADSHEET_ID) : SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["date", "name", "phone", "gender", "email", "quiz", "score", "total", "pct", "passed", "wrong", "answers_json"]);
  }
  sheet.setFrozenRows(1);
  return sheet;
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = getSheet_();
    var answers = data.answers || [];
    sheet.appendRow([
      data.date || "",
      data.name || "",
      data.phone || "",
      data.gender || "",
      data.email || "",
      data.quiz || "",
      data.score || "",
      data.total || "",
      data.pct || "",
      data.passed === true ? "сдан" : "не сдан",
      data.wrong || "",
      JSON.stringify(answers)
    ]);
    return json_({ ok: true, ts: data.ts });
  } catch (err) {
    return json_({ ok: false, error: String(err) }, 500);
  }
}

function doGet(e) {
  try {
    var sheet = getSheet_();
    var lastRow = sheet.getLastRow();
    var lastCol = sheet.getLastColumn();
    if (lastRow < 2) return json_({ rows: 0 });
    var values = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
    var rows = values.map(function (r) {
      var answers = [];
      try { answers = JSON.parse(r[11] || "[]"); } catch (err) {}
      return {
        date: r[0], name: r[1], phone: r[2], gender: r[3], email: r[4],
        quiz: r[5], score: r[6], total: r[7], pct: r[8], passed: (r[9] === "сдан"),
        wrong: r[10], answers: answers
      };
    });
    return json_({ rows: rows.length, data: rows });
  } catch (err) {
    return json_({ error: String(err) }, 500);
  }
}

function json_(obj, code) {
  var out = ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
  if (code && code !== 200) out = ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
  return out;
}