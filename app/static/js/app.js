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
