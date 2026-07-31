(function () {
  const SUPPORTED = ["en", "zh", "ko"];
  const STORAGE_KEY = "weave-lang";

  function detectLang() {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get("lang");
    if (SUPPORTED.includes(fromQuery)) {
      localStorage.setItem(STORAGE_KEY, fromQuery);
      return fromQuery;
    }
    const stored = localStorage.getItem(STORAGE_KEY);
    if (SUPPORTED.includes(stored)) return stored;
    const nav = (navigator.language || "en").toLowerCase();
    if (nav.startsWith("zh")) return "zh";
    if (nav.startsWith("ko")) return "ko";
    return "en";
  }

  function getLang() {
    return document.documentElement.lang && SUPPORTED.includes(document.documentElement.lang)
      ? document.documentElement.lang
      : detectLang();
  }

  function t(path, lang) {
    const L = lang || getLang();
    const parts = path.split(".");
    let cur = window.WEAVE_I18N[L];
    for (const p of parts) {
      if (cur == null) return path;
      cur = cur[p];
    }
    return cur == null ? path : cur;
  }

  function applyStaticI18n(lang) {
    document.documentElement.lang = lang === "zh" ? "zh-Hans" : lang;
    document.documentElement.dataset.lang = lang;
    document.body.classList.remove("lang-en", "lang-zh", "lang-ko");
    document.body.classList.add("lang-" + lang);

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      const val = t(key, lang);
      if (typeof val === "string") el.textContent = val;
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder"), lang));
    });

    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria"), lang));
    });

    const titleEl = document.querySelector("[data-page-title]");
    if (titleEl) {
      const pageKey = titleEl.getAttribute("data-page-title");
      const site = t("meta.siteName", lang);
      const page = t(pageKey, lang);
      document.title = page ? page + " · " + site : site;
    }

    document.querySelectorAll("[data-lang-panel]").forEach((panel) => {
      const panelLang = panel.getAttribute("data-lang-panel");
      panel.hidden = panelLang !== lang;
    });

    document.querySelectorAll(".lang-switch button").forEach((btn) => {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-lang") === lang ? "true" : "false");
    });

    document.querySelectorAll(".brand [data-lang-link], .brand__sail, .brand__qi, .brand__ko").forEach((el) => {
      const linkLang =
        el.classList.contains("brand__sail") ? "en" :
        el.classList.contains("brand__qi") ? "zh" :
        el.classList.contains("brand__ko") ? "ko" : null;
      if (!linkLang) return;
      el.setAttribute("aria-current", linkLang === lang ? "page" : "false");
    });
  }

  function topicLabel(topic, lang) {
    const map = {
      ai: t("nav.ai", lang),
      sus: t("nav.sustainability", lang),
      edu: t("nav.education", lang),
    };
    return map[topic] || topic;
  }

  function topicClass(topic) {
    return topic === "ai" ? "tag--ai" : topic === "sus" ? "tag--sus" : "tag--edu";
  }

  function formatDate(iso, lang) {
    try {
      const locale = lang === "zh" ? "zh-CN" : lang === "ko" ? "ko-KR" : "en-US";
      return new Intl.DateTimeFormat(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
      }).format(new Date(iso + "T12:00:00"));
    } catch {
      return iso;
    }
  }

  function renderArticleList(container, articles, lang, basePrefix) {
    if (!container || !articles) return;
    const prefix = basePrefix || "";
    container.innerHTML = articles
      .map((a) => {
        const tags = a.topics
          .map((tp) => `<span class="tag ${topicClass(tp)}">${topicLabel(tp, lang)}</span>`)
          .join("");
        return `
          <a class="article-item" href="${prefix}${a.href}">
            <span class="article-item__meta">${formatDate(a.date, lang)}</span>
            <span>
              <h3>${a.title[lang]}</h3>
              <p>${a.excerpt[lang]}</p>
              <span class="tags">${tags}</span>
            </span>
            <span class="article-item__arrow" aria-hidden="true">→</span>
          </a>`;
      })
      .join("");
  }

  function filterByTopic(topic) {
    return (window.WEAVE_ARTICLES || []).filter((a) => a.topics.includes(topic));
  }

  function setLang(lang) {
    if (!SUPPORTED.includes(lang)) return;
    localStorage.setItem(STORAGE_KEY, lang);
    applyStaticI18n(lang);

    const latest = document.querySelector("[data-article-list='latest']");
    if (latest) {
      renderArticleList(latest, (window.WEAVE_ARTICLES || []).slice(0, 3), lang, latest.dataset.base || "");
    }

    const all = document.querySelector("[data-article-list='all']");
    if (all) {
      renderArticleList(all, window.WEAVE_ARTICLES || [], lang, all.dataset.base || "");
    }

    const topic = document.querySelector("[data-article-list][data-topic]");
    if (topic) {
      const key = topic.getAttribute("data-topic");
      renderArticleList(topic, filterByTopic(key), lang, topic.dataset.base || "");
    }

    document.dispatchEvent(new CustomEvent("weave:lang", { detail: { lang } }));
  }

  function initNav() {
    const toggle = document.querySelector(".menu-toggle");
    const nav = document.querySelector(".nav");
    if (toggle && nav) {
      toggle.addEventListener("click", () => {
        const open = nav.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    document.querySelectorAll(".lang-switch button").forEach((btn) => {
      btn.addEventListener("click", () => setLang(btn.getAttribute("data-lang")));
    });
  }

  function initReveal() {
    const nodes = document.querySelectorAll(".reveal");
    if (!nodes.length) return;
    if (!("IntersectionObserver" in window)) {
      nodes.forEach((n) => n.classList.add("is-visible"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    nodes.forEach((n) => io.observe(n));
  }

  document.addEventListener("DOMContentLoaded", () => {
    initNav();
    setLang(detectLang());
    initReveal();
  });

  window.Weave = { setLang, t, getLang, topicLabel, formatDate };
})();
