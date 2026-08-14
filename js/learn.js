(function () {
  const STORAGE = "sail-learn-progress";
  const SUPPORTED = ["en", "zh", "ko"];

  function t(path, lang) {
    return window.Weave ? window.Weave.t(path, lang) : path;
  }

  function normalizeLang(lang) {
    const raw = String(lang || "").toLowerCase();
    if (raw.startsWith("zh")) return "zh";
    if (raw.startsWith("ko")) return "ko";
    if (SUPPORTED.includes(raw)) return raw;
    if (window.Weave) return window.Weave.getLang();
    return "en";
  }

  function getLang() {
    return normalizeLang(window.Weave ? window.Weave.getLang() : "en");
  }

  function loadProgress() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE) || "{}");
    } catch {
      return {};
    }
  }

  function saveProgress(data) {
    try {
      localStorage.setItem(STORAGE, JSON.stringify(data));
    } catch (_) {
      /* private mode */
    }
  }

  function moduleProgress(id) {
    return loadProgress()[id] || {};
  }

  function setModuleProgress(id, patch) {
    const all = loadProgress();
    all[id] = Object.assign({}, all[id] || {}, patch, { updated: new Date().toISOString() });
    saveProgress(all);
    return all[id];
  }

  function skillLabel(skill, lang) {
    const map = {
      en: {
        "classroom-use": "Classroom use",
        evaluate: "Evaluate claims",
        "energy-society": "Energy & society",
        understand: "Understand AI",
        create-with-care: "Create with care",
      },
      zh: {
        "classroom-use": "课堂使用",
        evaluate: "评估主张",
        "energy-society": "能源与社会",
        understand: "理解 AI",
        create-with-care: "审慎创造",
      },
      ko: {
        "classroom-use": "수업 활용",
        evaluate: "주장 평가",
        "energy-society": "에너지와 사회",
        understand: "AI 이해",
        create-with-care: "신중한 창작",
      },
    };
    return (map[lang] && map[lang][skill]) || skill;
  }

  function textOf(obj, lang) {
    if (!obj) return "";
    if (typeof obj === "string") return obj;
    return obj[lang] || obj.en || obj.zh || obj.ko || "";
  }

  function renderList(lang) {
    const root = document.querySelector("[data-learn-list]");
    if (!root) return;
    lang = normalizeLang(lang);
    const modules = window.WEAVE_LEARN_MODULES || [];
    if (!modules.length) {
      root.innerHTML = `<p class="learn-empty">${t("learn.empty", lang)}</p>`;
      return;
    }
    root.innerHTML = modules
      .map((m) => {
        const p = moduleProgress(m.id);
        const status = p.completed
          ? t("learn.completed", lang)
          : p.score != null
            ? t("learn.continue", lang)
            : t("learn.start", lang);
        const skills = (m.skills || [])
          .map((s) => `<span class="tag tag--edu">${skillLabel(s, lang)}</span>`)
          .join("");
        const sdgs = (m.sdgs || []).map((s) => `<span class="tag tag--sus">SDG ${s}</span>`).join("");
        const date = window.Weave ? window.Weave.formatDate(m.date, lang) : m.date;
        const title = textOf(m.title, lang);
        const excerpt = textOf(m.excerpt, lang);
        return `
          <a class="article-item" href="module.html?id=${encodeURIComponent(m.id)}">
            <span class="article-item__meta">${date} · ${m.minutes || 8} ${t("learn.minutes", lang)}</span>
            <span>
              <h3>${title}</h3>
              <p>${excerpt}</p>
              <span class="tags">${skills}${sdgs}<span class="tag tag--ai">${status}</span></span>
            </span>
            <span class="article-item__arrow" aria-hidden="true">→</span>
          </a>`;
      })
      .join("");
  }

  function findModule(id) {
    return (window.WEAVE_LEARN_MODULES || []).find((m) => m.id === id);
  }

  function renderModule(lang) {
    const mount = document.querySelector("[data-learn-module]");
    if (!mount) return;
    lang = normalizeLang(lang);
    const id = new URLSearchParams(location.search).get("id");
    const mod = findModule(id);
    if (!mod) {
      mount.innerHTML = `<p class="learn-empty">${t("learn.empty", lang)}</p>`;
      return;
    }

    const progress = moduleProgress(mod.id);
    const insights = (mod.insights || [])
      .map((ins, i) => `<li><strong>${i + 1}.</strong> ${textOf(ins, lang)}</li>`)
      .join("");
    const skills = (mod.skills || [])
      .map((s) => `<span class="tag tag--edu">${skillLabel(s, lang)}</span>`)
      .join("");
    const sdgs = (mod.sdgs || []).map((s) => `<span class="tag tag--sus">SDG ${s}</span>`).join("");

    const questions = (mod.questions || [])
      .map((q, qi) => {
        const choices = q.choices
          .map((c, ci) => {
            const checked = progress.answers && progress.answers[qi] === ci ? "checked" : "";
            return `<label class="learn-choice"><input type="radio" name="q${qi}" value="${ci}" ${checked} /> <span>${textOf(c, lang)}</span></label>`;
          })
          .join("");
        return `
          <fieldset class="learn-q" data-q="${qi}">
            <legend>${qi + 1}. ${textOf(q.prompt, lang)}</legend>
            ${choices}
            <p class="learn-explain" hidden></p>
          </fieldset>`;
      })
      .join("");

    const savedReflect = progress.reflection || "";
    const date = window.Weave ? window.Weave.formatDate(mod.date, lang) : mod.date;

    mount.innerHTML = `
      <p class="eyebrow"><a href="index.html">${t("learn.back", lang)}</a></p>
      <h1 class="display learn-title">${textOf(mod.title, lang)}</h1>
      <p class="dek">${textOf(mod.excerpt, lang)}</p>
      <p class="learn-meta">${date} · ${mod.minutes || 8} ${t("learn.minutes", lang)}</p>
      <p class="tags">${skills}${sdgs}</p>
      <p class="learn-digest"><a href="${mod.digestHref}">${t("learn.digestLink", lang)}</a></p>

      <section class="learn-block">
        <h2>${t("learn.insights", lang)}</h2>
        <ol class="learn-insights">${insights}</ol>
      </section>

      <section class="learn-block">
        <h2>${t("learn.quiz", lang)}</h2>
        <form class="learn-quiz" data-learn-quiz>
          ${questions}
          <button class="btn btn--solid" type="submit">${t("learn.submit", lang)}</button>
          <p class="learn-score" data-learn-score hidden></p>
        </form>
      </section>

      <section class="learn-block">
        <h2>${t("learn.ethics", lang)}</h2>
        <p>${textOf(mod.ethics, lang)}</p>
        <label class="learn-reflect-label" for="learn-reflect">${t("learn.reflect", lang)}</label>
        <textarea id="learn-reflect" class="learn-reflect" rows="5"></textarea>
        <button type="button" class="btn btn--outline" data-learn-save-reflect>${t("learn.reflectSave", lang)}</button>
        <p class="learn-reflect-status" data-learn-reflect-status hidden>${t("learn.reflectSaved", lang)}</p>
      </section>
    `;

    const reflectEl = mount.querySelector("#learn-reflect");
    if (reflectEl) reflectEl.value = savedReflect;

    const form = mount.querySelector("[data-learn-quiz]");
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      let correct = 0;
      const answers = [];
      (mod.questions || []).forEach((q, qi) => {
        const selected = form.querySelector(`input[name="q${qi}"]:checked`);
        const val = selected ? Number(selected.value) : -1;
        answers[qi] = val;
        const field = form.querySelector(`[data-q="${qi}"]`);
        const explain = field.querySelector(".learn-explain");
        const ok = val === q.answer;
        if (ok) correct += 1;
        field.classList.toggle("is-correct", ok);
        field.classList.toggle("is-wrong", !ok);
        explain.hidden = false;
        explain.textContent = textOf(q.explain, lang);
      });
      const scoreEl = form.querySelector("[data-learn-score]");
      scoreEl.hidden = false;
      scoreEl.textContent = `${t("learn.score", lang)}: ${correct} / ${mod.questions.length}`;
      setModuleProgress(mod.id, {
        answers,
        score: correct,
        completed: correct === mod.questions.length,
      });
    });

    const saveBtn = mount.querySelector("[data-learn-save-reflect]");
    saveBtn.addEventListener("click", () => {
      const text = mount.querySelector("#learn-reflect").value.trim();
      setModuleProgress(mod.id, { reflection: text });
      const status = mount.querySelector("[data-learn-reflect-status]");
      status.hidden = false;
    });
  }

  function refresh(lang) {
    try {
      const L = normalizeLang(lang || getLang());
      renderList(L);
      renderModule(L);
    } catch (err) {
      console.error("SAIL learn refresh failed", err);
    }
  }

  function boot() {
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  document.addEventListener("weave:lang", (e) => refresh(e.detail && e.detail.lang));
  setTimeout(boot, 0);
})();
