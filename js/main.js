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

  function renderCollectedList(container, items, lang) {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML = `<p class="collected-empty">${t("collected.empty", lang)}</p>`;
      return;
    }
    container.innerHTML = items
      .map((a) => {
        const tags = (a.topics || [])
          .map((tp) => `<span class="tag ${topicClass(tp)}">${topicLabel(tp, lang)}</span>`)
          .join("");
        const safeTitle = String(a.title || "").replace(/</g, "&lt;");
        const safeExcerpt = String(a.excerpt || "").replace(/</g, "&lt;");
        const safeSource = String(a.source || "").replace(/</g, "&lt;");
        const safeUrl = String(a.url || "#").replace(/"/g, "&quot;");
        return `
          <a class="article-item article-item--external" href="${safeUrl}" target="_blank" rel="noopener noreferrer">
            <span class="article-item__meta">${formatDate(a.date, lang)}</span>
            <span>
              <h3>${safeTitle}</h3>
              <p>${safeExcerpt}</p>
              <span class="tags">${tags}<span class="tag">${t("collected.source", lang)}: ${safeSource}</span></span>
            </span>
            <span class="article-item__arrow" aria-hidden="true">↗</span>
          </a>`;
      })
      .join("");
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

    const collectedLatest = document.querySelector("[data-collected-list='latest']");
    if (collectedLatest) {
      const items = ((window.SAIL_COLLECTED && window.SAIL_COLLECTED.items) || []).slice(0, 5);
      renderCollectedList(collectedLatest, items, lang);
    }

    const collectedAll = document.querySelector("[data-collected-list='all']");
    if (collectedAll) {
      renderCollectedList(collectedAll, (window.SAIL_COLLECTED && window.SAIL_COLLECTED.items) || [], lang);
    }

    const updatedEl = document.querySelector("[data-collected-updated]");
    if (updatedEl && window.SAIL_COLLECTED && window.SAIL_COLLECTED.updated) {
      const day = String(window.SAIL_COLLECTED.updated).slice(0, 10);
      updatedEl.textContent = t("collected.updated", lang) + " " + formatDate(day, lang);
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
      { threshold: 0.05, rootMargin: "0px 0px -20px 0px" }
    );
    nodes.forEach((n) => {
      const rect = n.getBoundingClientRect();
      if (rect.top < window.innerHeight && rect.bottom > 0) {
        n.classList.add("is-visible");
      } else {
        io.observe(n);
      }
    });
  }

  /**
   * Private visitor stats via GoatCounter (dashboard only — not shown on the site).
   * Create a free site at https://www.goatcounter.com with this code, and set
   * “Dashboard viewable by” to logged-in users only.
   */
  const SAIL_GOATCOUNTER = "sail-website";

  function initAnalytics() {
    if (!SAIL_GOATCOUNTER) return;
    const host = location.hostname;
    if (host === "localhost" || host === "127.0.0.1") return;

    const s = document.createElement("script");
    s.async = true;
    s.dataset.goatcounter = `https://${SAIL_GOATCOUNTER}.goatcounter.com/count`;
    s.src = "https://gc.zgo.at/count.js";
    document.head.appendChild(s);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initNav();
    setLang(detectLang());
    initReveal();
    initAnalytics();
  });

  window.Weave = { setLang, t, getLang, topicLabel, formatDate };
})();
