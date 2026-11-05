// Landing-page scroll animation: sections fade and rise into view as the visitor
// scrolls, with a small stagger between sibling cards. Decorative only.
//
// Content stays visible if this script does not run, and nothing animates for
// visitors who prefer reduced motion or browsers without IntersectionObserver.
(function () {
  "use strict";

  const reduced =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || typeof window.IntersectionObserver !== "function") {
    return;
  }

  const GROUPS = [
    ".problem-band .two-column > *",
    ".section-heading",
    ".steps li",
    ".status-grid article",
    ".section-link",
    ".cta > *"
  ];
  const STAGGER_MS = 90;

  const targets = [];
  GROUPS.forEach((selector) => {
    document.querySelectorAll(selector).forEach((element) => {
      if (!targets.includes(element)) {
        targets.push(element);
      }
    });
  });
  if (targets.length === 0) {
    return;
  }

  targets.forEach((element) => {
    const siblings = Array.from(element.parentElement.children).filter((child) =>
      targets.includes(child)
    );
    element.style.setProperty("--d", `${siblings.indexOf(element) * STAGGER_MS}ms`);
    element.setAttribute("data-scroll", "");
  });

  // The class that hides the targets is only added once the observer is ready.
  document.documentElement.classList.add("js-anim");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -6% 0px" }
  );

  targets.forEach((element) => observer.observe(element));
})();
