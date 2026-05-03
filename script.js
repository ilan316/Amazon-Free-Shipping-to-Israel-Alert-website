/* ===========================
   REVEAL ON SCROLL
   =========================== */

const revealNodes = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  revealNodes.forEach((node) => observer.observe(node));
} else {
  revealNodes.forEach((node) => node.classList.add("in"));
}

/* ===========================
   ANIMATED COUNTERS
   =========================== */

const counters = document.querySelectorAll(".counter");

if ("IntersectionObserver" in window && counters.length > 0) {
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;

        const el = entry.target;
        const target = parseInt(el.dataset.target, 10);
        const duration = 1400;
        const start = performance.now();

        const tick = (now) => {
          const elapsed = now - start;
          const progress = Math.min(elapsed / duration, 1);
          // Ease-out cubic
          const eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = Math.round(eased * target).toLocaleString("he-IL");
          if (progress < 1) requestAnimationFrame(tick);
        };

        requestAnimationFrame(tick);
        counterObserver.unobserve(el);
      });
    },
    { threshold: 0.6 }
  );

  counters.forEach((counter) => counterObserver.observe(counter));
}

/* ===========================
   HAMBURGER MENU
   =========================== */

const hamburgerBtn = document.getElementById("hamburger-btn");
const mainNav = document.getElementById("main-nav");

if (hamburgerBtn && mainNav) {
  hamburgerBtn.addEventListener("click", () => {
    const isOpen = mainNav.classList.toggle("open");
    hamburgerBtn.setAttribute("aria-expanded", isOpen);
  });
  // סגור תפריט בלחיצה על לינק
  mainNav.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => {
      mainNav.classList.remove("open");
      hamburgerBtn.setAttribute("aria-expanded", "false");
    });
  });
  // סגור בלחיצה מחוץ לנאב
  document.addEventListener("click", (e) => {
    if (!hamburgerBtn.contains(e.target) && !mainNav.contains(e.target)) {
      mainNav.classList.remove("open");
      hamburgerBtn.setAttribute("aria-expanded", "false");
    }
  });
}

/* ===========================
   STICKY NAV SHADOW
   =========================== */

const topbar = document.getElementById("topbar");

const onScroll = () => {
  if (!topbar) return;
  topbar.classList.toggle("scrolled", window.scrollY > 20);

  // Floating CTA logic
  const floatingCta = document.getElementById("floating-cta");
  const downloadSection = document.getElementById("download");

  if (floatingCta && downloadSection) {
    const scrolled = window.scrollY > 450;
    const downloadRect = downloadSection.getBoundingClientRect();
    const nearDownload = downloadRect.top < window.innerHeight && downloadRect.bottom > 0;
    const nearBottom = (window.innerHeight + window.scrollY) >= document.documentElement.scrollHeight - 120;

    if (scrolled && !nearDownload && !nearBottom) {
      floatingCta.classList.add("visible");
    } else {
      floatingCta.classList.remove("visible");
    }
  }
};

window.addEventListener("scroll", onScroll, { passive: true });

/* ===========================
   DOWNLOAD CLICK TRACKING
   =========================== */

["hero-download-btn", "main-download-btn", "nav-download-btn", "floating-download-btn"].forEach(
  (id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("click", () => {
      if (window.va) {
        window.va("event", { name: "download_click", source: id });
      }
    });
  }
);

/* ===========================
   CONTACT FORM
   =========================== */

const contactForm = document.querySelector("#contact-form");

if (contactForm) {
  const nameInput = document.querySelector("#contact-name");
  const emailInput = document.querySelector("#contact-email");
  const messageInput = document.querySelector("#contact-message");
  const statusEl = document.querySelector("#contact-status");
  const submitBtn = contactForm.querySelector("button[type='submit']");

  const setRequiredValidity = (input, message) => {
    if (!input) return true;
    if (!input.value.trim()) {
      input.setCustomValidity(message);
      return false;
    }
    input.setCustomValidity("");
    return true;
  };

  [nameInput, emailInput, messageInput].forEach((input) => {
    if (!input) return;
    input.addEventListener("input", () => input.setCustomValidity(""));
  });

  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const isNameValid = setRequiredValidity(nameInput, "יש למלא שם");
    const isEmailValid = setRequiredValidity(emailInput, "יש למלא אימייל");
    const isMessageValid = setRequiredValidity(messageInput, "יש למלא תוכן פנייה");

    if (!isNameValid || !isEmailValid || !isMessageValid || !contactForm.checkValidity()) {
      contactForm.reportValidity();
      if (statusEl) statusEl.textContent = "יש למלא את כל שדות החובה לפני שליחה.";
      return;
    }

    const payload = {
      name: nameInput.value.trim(),
      email: emailInput.value.trim(),
      message: messageInput.value.trim(),
      _subject: "[פנייה מהאתר] AMZ Free Ship Alert",
      _captcha: "false",
      _template: "table",
    };

    try {
      if (submitBtn) submitBtn.disabled = true;
      if (statusEl) statusEl.textContent = "שולח פנייה...";

      const res = await fetch("https://app.amzfreeil.com/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: payload.name, email: payload.email, message: payload.message }),
      });

      if (!res.ok) throw new Error("Submit failed");

      if (statusEl) statusEl.textContent = "הפנייה נשלחה בהצלחה.";
      contactForm.reset();
    } catch (err) {
      if (statusEl) {
        statusEl.innerHTML =
          'שליחה נכשלה. אפשר לשלוח ידנית לכתובת: <strong>alerts@amzfreeil.com</strong>';
      }
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

// Alert modal
const alertModal = document.getElementById('alert-modal');
const alertClose = document.getElementById('alert-modal-close');
if (alertModal && alertClose) {
  alertClose.addEventListener('click', () => {
    alertModal.classList.add('hidden');
  });
}
