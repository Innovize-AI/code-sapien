(function () {
    // Configuration
    const API_URL = "http://localhost:8000/api/webhooks/generic"; // Update this in production
    const FORM_SELECTOR = "form[data-lead-capture]";

    function init() {
        document.addEventListener("submit", function (event) {
            const form = event.target;
            if (form.matches(FORM_SELECTOR)) {
                event.preventDefault();
                submitLead(form);
            }
        });
    }

    async function submitLead(form) {
        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => {
            data[key] = value;
        });

        // Add some context
        data.source_url = window.location.href;
        data.referrer = document.referrer;
        data.timestamp = new Date().toISOString();

        const submitBtn = form.querySelector('[type="submit"]');
        const originalText = submitBtn ? submitBtn.innerText : "";
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerText = "Processing...";
        }

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                const result = await response.json();
                console.log("Lead captured:", result);
                // Trigger success visual
                if (form.dataset.onSuccess === "redirect") {
                    window.location.href = form.dataset.redirectUrl || "/success";
                } else {
                    form.innerHTML = "<div class='success-msg'>Thank you! Your research is being prepared.</div>";
                }
            } else {
                throw new Error("Failed to submit");
            }
        } catch (error) {
            console.error("Lead capture error:", error);
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerText = originalText;
            }
            alert("Sorry, there was an error processing your request. Please try again.");
        }
    }

    // Initialize on load
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
