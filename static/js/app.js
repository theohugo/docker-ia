(function () {
    "use strict";

    var root = document.documentElement;
    var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    function storedTheme() {
        try {
            return window.localStorage.getItem("cadria-theme");
        } catch (error) {
            return null;
        }
    }

    function setTheme(theme, persist) {
        var safeTheme = theme === "dark" ? "dark" : "light";
        root.dataset.theme = safeTheme;

        var toggle = document.querySelector("[data-theme-toggle]");
        if (toggle) {
            var willEnableDark = safeTheme !== "dark";
            toggle.setAttribute("aria-pressed", String(safeTheme === "dark"));
            toggle.setAttribute("aria-label", "Thème sombre");
            toggle.title = willEnableDark ? "Activer le thème sombre" : "Activer le thème clair";
        }

        var themeMeta = document.querySelector('meta[name="theme-color"]');
        if (themeMeta) {
            themeMeta.content = safeTheme === "dark" ? "#100d18" : "#faf5ff";
        }

        if (persist) {
            try {
                window.localStorage.setItem("cadria-theme", safeTheme);
            } catch (error) {
                // Le thème reste appliqué même si le stockage est indisponible.
            }
        }
    }

    function initTheme() {
        setTheme(root.dataset.theme, false);

        var toggle = document.querySelector("[data-theme-toggle]");
        if (toggle) {
            toggle.addEventListener("click", function () {
                setTheme(root.dataset.theme === "dark" ? "light" : "dark", true);
            });
        }

        var systemPreference = window.matchMedia("(prefers-color-scheme: dark)");
        systemPreference.addEventListener("change", function (event) {
            if (!storedTheme()) {
                setTheme(event.matches ? "dark" : "light", false);
            }
        });
    }

    function initBriefForm() {
        var form = document.querySelector("[data-brief-form]");
        if (!form) {
            return;
        }

        var idea = form.querySelector("#id_raw_idea, textarea[name='raw_idea']");
        var counter = form.querySelector("[data-char-count]");
        var submit = form.querySelector("[data-submit-button]");
        var submitLabel = form.querySelector("[data-submit-label]");
        var dirty = false;
        var submitting = false;

        function updateCount() {
            if (!idea || !counter) {
                return;
            }
            var count = idea.value.length;
            counter.textContent = count + " caractère" + (count > 1 ? "s" : "");
        }

        if (idea) {
            updateCount();
            idea.addEventListener("input", updateCount);
        }

        form.addEventListener("input", function () {
            dirty = true;
        });

        form.addEventListener("keydown", function (event) {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                form.requestSubmit();
            }
        });

        window.addEventListener("beforeunload", function (event) {
            if (dirty && !submitting) {
                event.preventDefault();
                event.returnValue = "";
            }
        });

        form.addEventListener("submit", function () {
            submitting = true;
            if (!submit) {
                return;
            }
            submit.classList.add("is-loading");
            submit.setAttribute("aria-busy", "true");
            submit.disabled = true;
            if (submitLabel) {
                submitLabel.textContent = "Transmission à CadrIA…";
            }
        });
    }

    function focusFirstFormError() {
        var invalidField = document.querySelector(
            ".field--error input, .field--error textarea, .field--error select"
        );
        if (invalidField) {
            invalidField.focus();
        }
    }

    function initCopyResult() {
        var button = document.querySelector("[data-copy-result]");
        var result = document.querySelector("[data-result-content]");
        var status = document.querySelector("[data-copy-status]");
        if (!button || !result) {
            return;
        }

        var label = button.querySelector("span");
        var originalLabel = label ? label.textContent : "Copier le brief";

        function legacyCopy(text) {
            var area = document.createElement("textarea");
            area.value = text;
            area.setAttribute("readonly", "");
            area.className = "sr-only";
            document.body.appendChild(area);
            area.select();
            document.execCommand("copy");
            area.remove();
        }

        button.addEventListener("click", function () {
            var text = result.innerText.trim();
            var operation = navigator.clipboard && window.isSecureContext
                ? navigator.clipboard.writeText(text)
                : Promise.resolve().then(function () { legacyCopy(text); });

            operation.then(function () {
                if (label) {
                    label.textContent = "Brief copié";
                }
                if (status) {
                    status.textContent = "Le brief est copié dans le presse-papiers.";
                }
                button.setAttribute("aria-label", "Le brief a été copié");
                window.setTimeout(function () {
                    if (label) {
                        label.textContent = originalLabel;
                    }
                    button.removeAttribute("aria-label");
                    if (status) {
                        status.textContent = "";
                    }
                }, 2200);
            }).catch(function () {
                if (label) {
                    label.textContent = "Copie impossible";
                }
                if (status) {
                    status.textContent = "Copie impossible. Sélectionnez le contenu du brief et copiez-le manuellement.";
                }
                window.setTimeout(function () {
                    if (label) {
                        label.textContent = originalLabel;
                    }
                }, 3200);
            });
        });
    }

    function initBriefPolling() {
        var poller = document.querySelector("[data-brief-poller]");
        if (!poller) {
            return;
        }

        var statusUrl = poller.dataset.statusUrl;
        var detailUrl = poller.dataset.detailUrl || window.location.href;
        var currentStatus = poller.dataset.currentStatus || "queued";
        var title = poller.querySelector("[data-progress-title]");
        var message = poller.querySelector("[data-progress-message]");
        var announcer = poller.querySelector("[data-poll-announcer]");
        var errorBox = poller.querySelector("[data-poll-error]");
        var errorTitle = poller.querySelector("[data-poll-error-title]");
        var errorMessage = poller.querySelector("[data-poll-error-message]");
        var retryButton = poller.querySelector("[data-poll-retry]");
        var loginLink = poller.querySelector("[data-poll-login]");
        var statusPill = document.querySelector("[data-status-pill]");
        var statusLabel = document.querySelector("[data-status-label]");
        var timer = null;
        var controller = null;
        var stopped = false;
        var failures = 0;

        var copy = {
            draft: {
                title: "Votre brief se prépare…",
                message: "La demande va rejoindre la file d’analyse.",
                label: "Préparation"
            },
            queued: {
                title: "Votre idée prend place dans la file…",
                message: "Le brief démarrera dès qu’un worker sera disponible.",
                label: "Dans la file d’attente"
            },
            processing: {
                title: "L’IA construit votre plan…",
                message: "Objectifs, livrables, risques et prochaines étapes sont en cours de structuration.",
                label: "Analyse en cours"
            },
            completed: {
                title: "Votre brief est prêt.",
                message: "Chargement de la restitution…",
                label: "Analyse prête"
            },
            failed: {
                title: "L’analyse s’est interrompue.",
                message: "Chargement du diagnostic…",
                label: "Analyse interrompue"
            }
        };

        function setProgress(status, announce) {
            var normalized = status === "pending" ? "queued" : status;
            var content = copy[normalized] || copy.queued;
            currentStatus = normalized;
            poller.dataset.currentStatus = normalized;

            if (title) {
                title.textContent = content.title;
            }
            if (message) {
                message.textContent = content.message;
            }
            if (statusLabel) {
                statusLabel.textContent = content.label;
            }
            if (statusPill) {
                ["draft", "queued", "pending", "processing", "completed", "failed"].forEach(function (name) {
                    statusPill.classList.remove("status-pill--" + name);
                });
                statusPill.classList.add("status-pill--" + normalized);
            }

            var rank = normalized === "processing" ? 1 : normalized === "completed" ? 2 : 0;
            poller.querySelectorAll("[data-progress-step]").forEach(function (step, index) {
                step.classList.toggle("is-complete", index < rank || normalized === "completed");
                step.classList.toggle("is-active", index === rank && normalized !== "failed");
            });

            if (announce && announcer) {
                announcer.textContent = content.label + ". " + content.message;
            }
        }

        function errorCopy(code, fallback) {
            if (code === "provider_quota") {
                return ["Quota IA atteint", fallback || "Le fournisseur a atteint sa limite. Votre brief est sauvegardé."];
            }
            if (code === "provider_authentication" || code === "configuration_error") {
                return ["Authentification du fournisseur impossible", fallback || "La configuration IA doit être vérifiée."];
            }
            if (code === "provider_unavailable" || code === "queue_unavailable") {
                return ["Service IA momentanément indisponible", fallback || "Votre brief est sauvegardé. Réessayez un peu plus tard."];
            }
            return ["Analyse interrompue", fallback || "Votre brief reste enregistré dans votre espace."];
        }

        function showError(heading, detail) {
            if (!errorBox) {
                return;
            }
            errorBox.hidden = false;
            if (errorTitle) {
                errorTitle.textContent = heading;
            }
            if (errorMessage) {
                errorMessage.textContent = detail;
            }
        }

        function hideError() {
            if (errorBox) {
                errorBox.hidden = true;
            }
            if (retryButton) {
                retryButton.hidden = false;
            }
            if (loginLink) {
                loginLink.hidden = true;
            }
        }

        function schedule(delay) {
            window.clearTimeout(timer);
            if (!stopped) {
                timer = window.setTimeout(poll, delay);
            }
        }

        function finishAt(url) {
            stopped = true;
            window.clearTimeout(timer);
            if (controller) {
                controller.abort();
            }
            window.location.assign(url || detailUrl);
        }

        function poll() {
            if (stopped) {
                return;
            }
            if (document.hidden) {
                schedule(1800);
                return;
            }

            controller = new AbortController();
            var timeout = window.setTimeout(function () { controller.abort(); }, 10000);

            fetch(statusUrl, {
                method: "GET",
                credentials: "same-origin",
                cache: "no-store",
                headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" },
                signal: controller.signal
            }).then(function (response) {
                window.clearTimeout(timeout);

                if (response.status === 401 || response.status === 403 || (response.redirected && response.url.indexOf("login") !== -1)) {
                    var authError = new Error("Votre session a expiré. Reconnectez-vous pour suivre ce brief.");
                    authError.kind = "auth";
                    throw authError;
                }
                if (response.status === 429) {
                    var quotaError = new Error("Le service a reçu trop de demandes. Nouvelle tentative dans quelques instants.");
                    quotaError.kind = "quota";
                    throw quotaError;
                }
                if (!response.ok) {
                    var providerError = new Error("Le service de suivi ne répond pas correctement.");
                    providerError.kind = response.status >= 500 ? "provider" : "network";
                    throw providerError;
                }

                var contentType = response.headers.get("content-type") || "";
                if (contentType.indexOf("application/json") === -1) {
                    var formatError = new Error("La réponse du service est illisible.");
                    formatError.kind = "provider";
                    throw formatError;
                }
                return response.json();
            }).then(function (data) {
                failures = 0;
                hideError();
                var nextStatus = data.status || currentStatus;
                var changed = nextStatus !== currentStatus;
                setProgress(nextStatus, changed);

                if (nextStatus === "completed") {
                    finishAt(data.analysis_url || detailUrl);
                    return;
                }
                if (nextStatus === "failed") {
                    var serverError = data.error || {};
                    var text = errorCopy(serverError.code, serverError.message);
                    showError(text[0], text[1]);
                    window.setTimeout(function () { finishAt(detailUrl); }, reducedMotion.matches ? 0 : 900);
                    return;
                }
                schedule(1800);
            }).catch(function (error) {
                window.clearTimeout(timeout);
                if (stopped || error.name === "AbortError" && document.hidden) {
                    return;
                }

                failures += 1;
                if (error.kind === "auth") {
                    showError("Session expirée", error.message);
                    if (retryButton) {
                        retryButton.hidden = true;
                    }
                    if (loginLink) {
                        loginLink.hidden = false;
                    }
                    stopped = true;
                    return;
                }
                if (error.kind === "quota") {
                    showError("Trop de demandes", error.message);
                } else if (error.kind === "provider") {
                    showError("Service momentanément indisponible", error.message);
                } else {
                    showError("Connexion interrompue", "Nous retentons automatiquement sans perdre votre brief.");
                }
                schedule(Math.min(10000, 1800 * Math.pow(1.55, failures)));
            });
        }

        if (retryButton) {
            retryButton.addEventListener("click", function () {
                stopped = false;
                failures = 0;
                hideError();
                poll();
            });
        }

        document.addEventListener("visibilitychange", function () {
            if (!document.hidden && !stopped) {
                window.clearTimeout(timer);
                poll();
            }
        });

        window.addEventListener("pagehide", function () {
            stopped = true;
            window.clearTimeout(timer);
            if (controller) {
                controller.abort();
            }
        });

        setProgress(currentStatus, false);
        schedule(700);
    }

    document.addEventListener("DOMContentLoaded", function () {
        initTheme();
        focusFirstFormError();
        initBriefForm();
        initCopyResult();
        initBriefPolling();
    });
}());
