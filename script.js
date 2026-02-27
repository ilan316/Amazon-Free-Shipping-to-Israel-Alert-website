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
    { threshold: 0.18 }
  );

  revealNodes.forEach((node) => observer.observe(node));
} else {
  // Fallback for older browsers without IntersectionObserver.
  revealNodes.forEach((node) => node.classList.add("in"));
}

const contactForm = document.querySelector("#contact-form");

if (contactForm) {
  const nameInput = document.querySelector("#contact-name");
  const emailInput = document.querySelector("#contact-email");
  const messageInput = document.querySelector("#contact-message");
  const statusEl = document.querySelector("#contact-status");
  const submitBtn = contactForm.querySelector("button[type='submit']");

  const setRequiredValidity = (input, message) => {
    if (!input) {
      return true;
    }
    if (!input.value.trim()) {
      input.setCustomValidity(message);
      return false;
    }
    input.setCustomValidity("");
    return true;
  };

  [nameInput, emailInput, messageInput].forEach((input) => {
    if (!input) {
      return;
    }
    input.addEventListener("input", () => input.setCustomValidity(""));
  });

  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const isNameValid = setRequiredValidity(nameInput, "יש למלא שם");
    const isEmailValid = setRequiredValidity(emailInput, "יש למלא אימייל");
    const isMessageValid = setRequiredValidity(messageInput, "יש למלא תוכן פנייה");

    if (!isNameValid || !isEmailValid || !isMessageValid || !contactForm.checkValidity()) {
      contactForm.reportValidity();
      if (statusEl) {
        statusEl.textContent = "יש למלא את כל שדות החובה לפני שליחה.";
      }
      return;
    }

    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const message = messageInput.value.trim();
    const payload = {
      name,
      email,
      message,
      _subject: "[פנייה מהאתר] Amazon Israel Free Ship Alert",
      _captcha: "false",
      _template: "table",
    };

    try {
      if (submitBtn) {
        submitBtn.disabled = true;
      }
      if (statusEl) {
        statusEl.textContent = "שולח פנייה...";
      }

      const res = await fetch("https://formsubmit.co/ajax/amazonisraelalert@gmail.com", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Submit failed");
      }

      if (statusEl) {
        statusEl.textContent = "הפנייה נשלחה בהצלחה.";
      }
      contactForm.reset();
    } catch (err) {
      if (statusEl) {
        statusEl.innerHTML =
          'שליחה נכשלה. אפשר לשלוח ידנית לכתובת: <strong>amazonisraelalert@gmail.com</strong>';
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
      }
    }
  });
}
