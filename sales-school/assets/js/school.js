var DG = {

  KEY: "dg_school_v1",

  getData: function () {
    try { return JSON.parse(localStorage.getItem(DG.KEY)) || {profile: null, results: []}; }
    catch (e) { return {profile: null, results: []}; }
  },
  saveData: function (d) { localStorage.setItem(DG.KEY, JSON.stringify(d)); },

  getProfile: function () { return DG.getData().profile; },
  getResults: function () { return DG.getData().results; },

  setProfile: function (p) {
    var d = DG.getData(); d.profile = p; DG.saveData(d);
  },

  addResult: function (r) {
    var d = DG.getData();
    r.ts = Date.now();
    r.date = new Date().toLocaleString("ru-RU");
    if (d.profile) {
      r.name = d.profile.name; r.phone = d.profile.phone;
      r.gender = d.profile.gender; r.email = d.profile.email;
    }
    d.results.push(r);
    DG.saveData(d);
  },

  clearResults: function () { var d = DG.getData(); d.results = []; DG.saveData(d); },

  escapeHtml: function (s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  },

  PROFILE_FIELDS: [
    { key: "name", label: "Имя", type: "text", req: true },
    { key: "phone", label: "Телефон", type: "tel", req: true },
    { key: "gender", label: "Пол", type: "select", req: true, options: ["", "Мужской", "Женский"] },
    { key: "email", label: "Электронная почта", type: "email", req: true }
  ],

  renderProfileForm: function (containerId) {
    var host = document.getElementById(containerId);
    if (!host) return;
    var p = DG.getProfile();

    var html = '<div class="profile card">';
    html += '<h3 style="margin-bottom:14px;">Профиль обучающегося</h3>';
    html += '<div class="profile__grid">';

    DG.PROFILE_FIELDS.forEach(function (f) {
      if (f.type === "select") {
        html += '<label class="field"><span>' + f.label + '</span>';
        html += '<select id="pf_' + f.key + '" data-key="' + f.key + '">';
        f.options.forEach(function (o) {
          var sel = (p && p[f.key] === o) ? " selected" : "";
          html += '<option value="' + DG.escapeHtml(o) + '"' + sel + '>' + (o || "— выберите —") + '</option>';
        });
        html += '</select></label>';
      } else {
        html += '<label class="field"><span>' + f.label + '</span>';
        html += '<input id="pf_' + f.key + '" type="' + f.type + '" data-key="' + f.key + '" placeholder="' + f.label + '" value="' + DG.escapeHtml(p ? p[f.key] : "") + '" /></label>';
      }
    });

    html += '</div>';
    html += '<div class="profile__actions">';
    html += '<button class="btn" type="button" id="profileSave">Сохранить профиль</button>';
    html += '<span class="profile__status" id="profileStatus"></span>';
    html += '</div>';
    html += '</div>';

    host.innerHTML = html;

    var statusEl = document.getElementById("profileStatus");
    if (p && p.name) statusEl.textContent = "✓ профиль заполнен";

    document.getElementById("profileSave").onclick = function () {
      var profile = {}, ok = true, firstBad = null;
      DG.PROFILE_FIELDS.forEach(function (f) {
        var el = document.getElementById("pf_" + f.key);
        var v = (el.value || "").trim();
        var bad = f.req && v === "";
        if (f.key === "email" && v !== "" && !/.+@.+\..+/.test(v)) { bad = true; }
        el.classList.toggle("bad", bad);
        if (bad) { ok = false; if (!firstBad) firstBad = el; }
        profile[f.key] = v;
      });
      if (!ok) {
        statusEl.textContent = "✗ заполните выделенные поля";
        statusEl.className = "profile__status err";
        if (firstBad) firstBad.focus();
        return;
      }
      DG.setProfile(profile);
      statusEl.textContent = "✓ сохранено";
      statusEl.className = "profile__status ok";
    };
  },

  QUIZ_WORDS: { ok: "Ваш ответ верный!", bad: "Ответ неверный", correct: "Правильный ответ" },

  renderQuiz: function (containerId, quiz) {
    var host = document.getElementById(containerId);
    if (!host) return;

    var html = '<div class="quiz">';
    html += '<div class="quiz__head"><h3>' + DG.escapeHtml(quiz.title) + '</h3>';
    html += '<p>' + DG.escapeHtml(quiz.intro || "Выберите один вариант ответа. После проверки увидите разбор каждого вопроса.") + '</p></div>';
    html += '<div class="quiz__list">';

    quiz.questions.forEach(function (q, qi) {
      html += '<div class="quiz__q" id="qq_' + qi + '">';
      html += '<div class="quiz__qtext"><b>Вопрос ' + (qi + 1) + '.</b> ' + DG.escapeHtml(q.q) + '</div>';
      html += '<div class="quiz__opts">';
      q.options.forEach(function (o, oi) {
        html += '<label class="quiz__opt" id="qo_' + qi + '_' + oi + '">';
        html += '<input type="radio" name="qq_' + qi + '" value="' + oi + '" />';
        html += '<span>' + DG.escapeHtml(o) + '</span></label>';
      });
      html += '</div>';
      html += '<div class="quiz__expl" id="qe_' + qi + '" style="display:none;"></div>';
      html += '</div>';
    });

    html += '</div>';
    html += '<div class="quiz__actions">';
    html += '<button class="btn" type="button" id="quizCheck">Проверить тест</button>';
    html += '</div>';
    html += '<div class="quiz__summary" id="quizSummary" style="display:none;"></div>';
    html += '</div>';

    host.innerHTML = html;

    var quizEl = host.querySelector(".quiz");

    document.getElementById("quizCheck").onclick = function () {
      var profile = DG.getProfile();
      if (!profile || !profile.name || !profile.email) {
        alert("Сначала заполните профиль обучающегося выше — без него результат не сохранится в таблицу.");
        var pf = document.querySelector(".profile");
        if (pf) { pf.scrollIntoView({behavior: "smooth"}); pf.classList.add("flash"); setTimeout(function(){pf.classList.remove("flash");}, 1200); }
        return;
      }

      var correct = 0, checked = 0, rows = [];
      quiz.questions.forEach(function (q, qi) {
        var sel = quizEl.querySelector('input[name="qq_' + qi + '"]:checked');
        var chosen = sel ? parseInt(sel.value, 10) : -1;
        if (chosen >= 0) checked++;
        var isRight = chosen === q.correct;
        if (isRight) correct++;

        q.options.forEach(function (o, oi) {
          var el = document.getElementById("qo_" + qi + "_" + oi);
          el.classList.remove("is-right", "is-wrong");
          if (oi === q.correct) el.classList.add("is-right");
          if (oi === chosen && !isRight) el.classList.add("is-wrong");
        });

        var expl = document.getElementById("qe_" + qi);
        expl.style.display = "block";
        expl.className = "quiz__expl " + (isRight ? "good" : "bad");
        expl.innerHTML = (isRight ? "✅ " + DG.QUIZ_WORDS.ok : "❌ " + DG.QUIZ_WORDS.bad +
          (chosen >= 0 ? " («" + DG.escapeHtml(q.options[chosen]) + "»)" : " — ответ не выбран") +
          ". " + DG.QUIZ_WORDS.correct + ": «" + DG.escapeHtml(q.options[q.correct]) + "».") +
          (q.expl ? "<br/>" + DG.escapeHtml(q.expl) : "");

        rows.push({ qi: qi, q: q.q, chosen: chosen, correct: q.correct, right: isRight });
      });

      var total = quiz.questions.length;
      var pct = Math.round(correct * 100 / total);

      var sum = document.getElementById("quizSummary");
      sum.style.display = "block";
      var verdict = pct >= (quiz.pass || 70) ? "Тест пройден" : "Нужно повторить раздел";
      sum.className = "quiz__summary " + (pct >= (quiz.pass || 70) ? "good" : "bad");
      sum.innerHTML =
        "<b>Результат: " + correct + " из " + total + " (" + pct + "%).</b> " + verdict +
        "<br/><small>Ответили на " + checked + " из " + total + " вопросов.</small>";

      document.getElementById("quizCheck").disabled = true;
      document.getElementById("quizCheck").textContent = "Тест проверен";
      quizEl.querySelectorAll(".quiz__opt input").forEach(function (inp) { inp.disabled = true; });

      DG.addResult({
        quiz: quiz.title,
        score: correct,
        total: total,
        pct: pct,
        passed: pct >= (quiz.pass || 70),
        answers: rows
      });
    };
  },

  csvEscape: function (v) {
    v = String(v == null ? "" : v);
    if (/[";\n\r]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
    return v;
  },

  exportCSV: function () {
    var res = DG.getResults();
    var line = function (arr) { return arr.map(DG.csvEscape).join(";") + "\r\n"; };
    var out = "\uFEFF" + line(["Дата", "Тест", "Имя", "Телефон", "Пол", "Email", "Баллы", "Из", "Процент", "Пройден"]);
    res.forEach(function (r) {
      out += line([r.date, r.quiz, r.name, r.phone, r.gender, r.email, r.score, r.total, r.pct + "%", r.passed ? "да" : "нет"]);
    });
    var blob = new Blob([out], {type: "text/csv;charset=utf-8"});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "damir-school-results.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  },

  exportJSON: function () {
    var res = DG.getResults();
    var blob = new Blob([JSON.stringify(res, null, 2)], {type: "application/json"});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "damir-school-results.json";
    a.click();
    URL.revokeObjectURL(a.href);
  },

  profileSummary: function (p) {
    return p && p.name ? (p.name + (p.phone ? ", " + p.phone : "")) : "не заполнен";
  },

  renderResultsTable: function (hostId) {
    var host = document.getElementById(hostId);
    if (!host) return;
    var d = DG.getData();

    var html = '<div class="res__profile card"><b>Текущий профиль:</b> ' +
      DG.escapeHtml(DG.profileSummary(d.profile)) +
      ' — <a href="#" onclick="event.preventDefault();DG.openProfile();return false;">изменить</a></div>';

    html += '<div class="res__tools">';
    html += '<button class="btn" type="button" onclick="DG.exportCSV()">Экспорт в Excel (CSV)</button>';
    html += '<button class="btn btn--light" type="button" onclick="DG.exportJSON()">Экспорт JSON</button>';
    html += '<button class="btn btn--light btn--danger" type="button" id="resClear">Очистить все результаты</button>';
    html += '</div>';

    var res = DG.getResults();
    if (!res.length) {
      html += '<div class="res__empty">Пока нет результатов. Пройдите тест в любом разделе — он появится здесь.</div>';
    } else {
      html += '<div class="res__count">Всего записей: ' + res.length + '</div>';
      html += '<div class="table-wrap res__table"><table>';
      html += '<thead><tr><th>Дата</th><th>Имя</th><th>Телефон</th><th>Пол</th><th>Email</th><th>Тест</th><th>Баллы</th><th>%</th><th>Статус</th></tr></thead><tbody>';

      var byQuiz = {};
      res.forEach(function (r) {
        byQuiz[r.quiz] = (byQuiz[r.quiz] || 0) + 1;
        html += "<tr>";
        html += "<td>" + DG.escapeHtml(r.date) + "</td>";
        html += "<td>" + DG.escapeHtml(r.name) + "</td>";
        html += "<td>" + DG.escapeHtml(r.phone) + "</td>";
        html += "<td>" + DG.escapeHtml(r.gender) + "</td>";
        html += "<td>" + DG.escapeHtml(r.email) + "</td>";
        html += "<td>" + DG.escapeHtml(r.quiz) + "</td>";
        html += "<td>" + r.score + " / " + r.total + "</td>";
        html += "<td>" + r.pct + "%</td>";
        html += "<td>" + (r.passed ? "<span class='pill ok'>сдан</span>" : "<span class='pill bad'>повторить</span>") + "</td>";
        html += "</tr>";
      });
      html += "</tbody></table></div>";

      html += '<div class="res__byquiz"><b>Прогресс по темам:</b><br/>';
      for (var q in byQuiz) {
        html += '<span class="res__chip">' + DG.escapeHtml(q) + " — " + byQuiz[q] + "</span> ";
      }
      html += "</div>";

      html += '<div class="res__allanswers">';
      res.forEach(function (r, ri) {
        if (!r.answers) return;
        html += '<details class="res__detail"><summary><b>#' + (ri + 1) + '</b> ' +
          DG.escapeHtml(r.date) + " · " + DG.escapeHtml(r.quiz) + " · " + r.score + "/" + r.total + " · " + DG.escapeHtml(r.name || "") + "</summary>";
        html += "<ul>";
        r.answers.forEach(function (a) {
          var ok = a.right;
          html += "<li class='" + (ok ? "ok" : "err") + "'>" + DG.escapeHtml(a.q) +
            " — " + (ok ? "верно" : "неверно") + "</li>";
        });
        html += "</ul></details>";
      });
      html += "</div>";
    }

    host.innerHTML = html;

    var clearBtn = document.getElementById("resClear");
    if (clearBtn) clearBtn.onclick = function () {
      if (confirm("Удалить все результаты?")) { DG.clearResults(); DG.renderResultsTable(hostId); }
    };
  },

  openProfile: function () {
    window.location.href = "index.html#profile";
  }
};