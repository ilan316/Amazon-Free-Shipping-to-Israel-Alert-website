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
  contactForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const name = document.querySelector("#contact-name")?.value.trim() || "";
    const email = document.querySelector("#contact-email")?.value.trim() || "";
    const message = document.querySelector("#contact-message")?.value.trim() || "";

    const emailSubject = encodeURIComponent("[פנייה מהאתר] Amazon Israel Free Ship Alert");
    const emailBody = encodeURIComponent(
      `שם: ${name}\nאימייל: ${email}\n\nתוכן הפנייה:\n${message}`
    );

    window.location.href = `mailto:amazonisraelalert@gmail.com?subject=${emailSubject}&body=${emailBody}`;
  });
}
