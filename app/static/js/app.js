const root = document.documentElement;
const toggle = document.querySelector("[data-theme-toggle]");
const savedTheme = localStorage.getItem("aijobcopilot-theme");

if (savedTheme) {
    root.setAttribute("data-theme", savedTheme);
}

if (toggle) {
    toggle.addEventListener("click", () => {
        const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", nextTheme);
        localStorage.setItem("aijobcopilot-theme", nextTheme);
    });
}

const analysisForm = document.querySelector("[data-analysis-form]");

if (analysisForm) {
    const savedJobSelect = analysisForm.querySelector("[data-saved-job-select]");
    const customFields = analysisForm.querySelector("[data-custom-job-fields]");
    const customInputs = customFields ? customFields.querySelectorAll("input, textarea") : [];

    const syncAnalysisMode = () => {
        const usingSavedJob = Boolean(savedJobSelect && savedJobSelect.value);
        if (!customFields) {
            return;
        }

        customFields.hidden = usingSavedJob;
        customInputs.forEach((input) => {
            if (usingSavedJob) {
                input.value = "";
            }
            input.toggleAttribute("disabled", usingSavedJob);
        });
    };

    savedJobSelect?.addEventListener("change", syncAnalysisMode);
    syncAnalysisMode();
}

const closeModal = (modalId) => {
    const modal = document.getElementById(modalId);
    if (!modal) {
        return;
    }

    modal.hidden = true;
    document.body.style.overflow = "";
};

const openModal = (modalId) => {
    const modal = document.getElementById(modalId);
    if (!modal) {
        return;
    }

    modal.hidden = false;
    document.body.style.overflow = "hidden";
};

document.addEventListener("click", (event) => {
    const openTrigger = event.target.closest("[data-modal-open]");
    if (openTrigger) {
        openModal(openTrigger.dataset.modalOpen);
        return;
    }

    const closeTrigger = event.target.closest("[data-modal-close]");
    if (closeTrigger) {
        closeModal(closeTrigger.dataset.modalClose);
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
        return;
    }

    document.querySelectorAll(".modal-shell").forEach((modal) => {
        if (!modal.hidden) {
            closeModal(modal.id);
        }
    });
});

document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }

    const lockSubmitControl = (control) => {
        if (!(control instanceof HTMLButtonElement || control instanceof HTMLInputElement)) {
            return;
        }

        if (control.dataset.submitting === "true") {
            return;
        }

        control.dataset.submitting = "true";
        control.disabled = true;
        control.setAttribute("aria-disabled", "true");

        if (control instanceof HTMLButtonElement) {
            control.dataset.originalText = control.textContent || "";
            control.textContent = control.dataset.loadingText || "Please wait...";
        } else {
            control.dataset.originalValue = control.value;
            control.value = control.dataset.loadingText || "Please wait...";
        }
    };

    const submitter = event.submitter;
    if (submitter instanceof HTMLButtonElement || submitter instanceof HTMLInputElement) {
        lockSubmitControl(submitter);
        return;
    }

    form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach((control) => {
        lockSubmitControl(control);
    });
});
