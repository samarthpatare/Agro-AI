(function () {
    "use strict";

    const LANGUAGES = {
        en: "English",
        hi: "हिन्दी",
        mr: "मराठी"
    };

    const CACHE_PREFIX = "smartKisanI18n:";
    const MAX_BATCH = 8;
    const MAX_SOURCE_LENGTH = 4000;

    const queue = new Map();
    let flushTimer = null;
    let translating = false;

    // =========================================================
    // GET CURRENT LANGUAGE
    // =========================================================

    function getLanguage() {

        const serverLanguage =
            window.SMART_KISAN_SERVER_LANGUAGE;

        const htmlLanguage =
            document.documentElement.getAttribute(
                "data-language"
            );

        const storedLanguage =
            localStorage.getItem(
                "smartKisanLanguage"
            );

        const language =
            serverLanguage ||
            htmlLanguage ||
            storedLanguage ||
            "en";

        return Object.prototype.hasOwnProperty.call(
            LANGUAGES,
            language
        )
            ? language
            : "en";
    }


    // =========================================================
    // CACHE
    // =========================================================

    function cacheKey(
        language,
        source
    ) {

        return (
            CACHE_PREFIX +
            language +
            ":" +
            source
        );
    }


    function readCache(
        language,
        source
    ) {

        try {

            return localStorage.getItem(
                cacheKey(
                    language,
                    source
                )
            );

        } catch (_) {

            return null;
        }
    }


    function writeCache(
        language,
        source,
        translated
    ) {

        try {

            localStorage.setItem(
                cacheKey(
                    language,
                    source
                ),
                translated
            );

        } catch (_) {

            // Ignore localStorage errors.
        }
    }


    // =========================================================
    // WHITESPACE
    // =========================================================

    function splitWhitespace(
        value
    ) {

        const match =
            String(value).match(
                /^(\s*)([\s\S]*?)(\s*)$/
            );

        return {

            prefix:
                match
                    ? match[1]
                    : "",

            core:
                match
                    ? match[2]
                    : String(value),

            suffix:
                match
                    ? match[3]
                    : ""

        };
    }


    // =========================================================
    // ELEMENTS THAT MUST NOT BE TRANSLATED
    // =========================================================

    function shouldSkipElement(
        element
    ) {

        if (!element) {
            return true;
        }

        return !!element.closest(
            [
                "[data-no-translate]",
                "script",
                "style",
                "noscript",
                "textarea",
                "code",
                "pre"
            ].join(",")
        );
    }


    // =========================================================
    // TEXT NODE CHECK
    // =========================================================

    function shouldTranslateTextNode(
        node
    ) {

        if (
            !node ||
            node.nodeType !==
                Node.TEXT_NODE
        ) {

            return false;
        }

        if (
            !node.parentElement ||
            shouldSkipElement(
                node.parentElement
            )
        ) {

            return false;
        }

        const source =
            node.dataset.smartKisanOriginalText ||
            node.nodeValue ||
            "";

        const core =
            splitWhitespace(
                source
            )
                .core
                .trim();

        if (!core) {
            return false;
        }

        // Ignore numbers, symbols and emojis only.
        if (!/[A-Za-z]/.test(core)) {
            return false;
        }

        if (
            core.length >
            MAX_SOURCE_LENGTH
        ) {

            return false;
        }

        return true;
    }


    // =========================================================
    // ORIGINAL TEXT
    // =========================================================

    function getOriginalText(
        node
    ) {

        if (
            node.dataset
                .smartKisanOriginalText ===
            undefined
        ) {

            node.dataset
                .smartKisanOriginalText =
                node.nodeValue || "";
        }

        return node.dataset
            .smartKisanOriginalText;
    }


    // =========================================================
    // ORIGINAL ATTRIBUTE
    // =========================================================

    function getOriginalAttribute(
        element,
        attribute
    ) {

        const key =
            "smartKisanOriginalAttr" +
            attribute.replace(
                /[^A-Za-z0-9]/g,
                "_"
            );

        if (
            element.dataset[key] ===
            undefined
        ) {

            element.dataset[key] =
                element.getAttribute(
                    attribute
                ) || "";
        }

        return element.dataset[key];
    }


    // =========================================================
    // ORIGINAL OPTION TEXT
    // =========================================================

    function getOriginalOptionText(
        option
    ) {

        if (
            option.dataset
                .smartKisanOriginalOptionText ===
            undefined
        ) {

            option.dataset
                .smartKisanOriginalOptionText =
                option.textContent || "";
        }

        return option.dataset
            .smartKisanOriginalOptionText;
    }


    // =========================================================
    // APPLY TRANSLATION
    // =========================================================

    function applyText(
        node,
        translated
    ) {

        if (!node.isConnected) {
            return;
        }

        const source =
            getOriginalText(node);

        const parts =
            splitWhitespace(
                source
            );

        node.nodeValue =
            parts.prefix +
            translated +
            parts.suffix;
    }


    // =========================================================
    // QUEUE TRANSLATION
    // =========================================================

    function enqueue(
        source,
        apply
    ) {

        const language =
            getLanguage();

        if (
            language === "en"
        ) {

            return;
        }

        const cleanSource =
            String(
                source || ""
            ).trim();

        if (!cleanSource) {
            return;
        }

        if (!/[A-Za-z]/.test(
            cleanSource
        )) {

            return;
        }

        if (
            cleanSource.length >
            MAX_SOURCE_LENGTH
        ) {

            return;
        }

        const cached =
            readCache(
                language,
                cleanSource
            );

        if (cached) {

            apply(cached);
            return;
        }

        const jobs =
            queue.get(
                cleanSource
            ) || [];

        jobs.push(apply);

        queue.set(
            cleanSource,
            jobs
        );

        scheduleFlush();
    }


    // =========================================================
    // SCHEDULE
    // =========================================================

    function scheduleFlush() {

        if (
            flushTimer !== null
        ) {

            return;
        }

        flushTimer =
            window.setTimeout(
                function () {

                    flushTimer =
                        null;

                    flushQueue();

                },
                150
            );
    }


    // =========================================================
    // CALL FLASK TRANSLATION API
    // =========================================================

    async function callTranslationAPI(
        sources,
        language
    ) {

        const response =
            await fetch(
                "/api/translate-text",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            language:
                                language,

                            texts:
                                sources

                        })
                }
            );

        if (!response.ok) {

            throw new Error(
                "Translation service is unavailable."
            );
        }

        const data =
            await response.json();

        if (
            !data.success ||
            !Array.isArray(
                data.translations
            )
        ) {

            throw new Error(
                data.error ||
                "Translation service returned an invalid response."
            );
        }

        return data.translations;
    }


    // =========================================================
    // PROCESS TRANSLATION QUEUE
    // =========================================================

    async function flushQueue() {

        if (
            translating ||
            queue.size === 0
        ) {

            return;
        }

        translating = true;

        const language =
            getLanguage();

        try {

            const entries =
                Array.from(
                    queue.entries()
                ).slice(
                    0,
                    MAX_BATCH
                );

            entries.forEach(
                function (entry) {

                    queue.delete(
                        entry[0]
                    );

                }
            );

            const sources =
                entries.map(
                    function (entry) {
                        return entry[0];
                    }
                );

            const translations =
                await callTranslationAPI(
                    sources,
                    language
                );

            sources.forEach(
                function (
                    source,
                    index
                ) {

                    const translated =
                        typeof translations[index] ===
                        "string"
                            ? translations[index].trim()
                            : "";

                    if (!translated) {
                        return;
                    }

                    writeCache(
                        language,
                        source,
                        translated
                    );

                    const jobs =
                        entries[index][1] ||
                        [];

                    jobs.forEach(
                        function (
                            apply
                        ) {

                            try {

                                apply(
                                    translated
                                );

                            } catch (_) {

                                // Ignore DOM update error.
                            }

                        }
                    );

                }
            );

        } catch (error) {

            console.warn(
                "Smart Kisan translation:",
                error.message
            );

        } finally {

            translating = false;

            if (
                queue.size > 0
            ) {

                scheduleFlush();
            }
        }
    }


    // =========================================================
    // SCAN TEXT
    // =========================================================

    function scanText(
        root
    ) {

        if (!root) {
            return;
        }


        // Single text node
        if (
            root.nodeType ===
            Node.TEXT_NODE
        ) {

            if (
                shouldTranslateTextNode(
                    root
                )
            ) {

                const source =
                    getOriginalText(
                        root
                    );

                enqueue(
                    splitWhitespace(
                        source
                    )
                        .core
                        .trim(),

                    function (
                        translated
                    ) {

                        applyText(
                            root,
                            translated
                        );

                    }
                );
            }

            return;
        }


        if (
            root.nodeType !==
            Node.ELEMENT_NODE
        ) {

            return;
        }

        if (
            shouldSkipElement(
                root
            )
        ) {

            return;
        }


        const walker =
            document.createTreeWalker(
                root,
                NodeFilter.SHOW_TEXT
            );

        const nodes = [];

        let node;

        while (
            (node =
                walker.nextNode())
        ) {

            nodes.push(
                node
            );
        }


        nodes.forEach(
            function (
                textNode
            ) {

                if (
                    !shouldTranslateTextNode(
                        textNode
                    )
                ) {

                    return;
                }

                const source =
                    getOriginalText(
                        textNode
                    );

                enqueue(
                    splitWhitespace(
                        source
                    )
                        .core
                        .trim(),

                    function (
                        translated
                    ) {

                        applyText(
                            textNode,
                            translated
                        );

                    }
                );

            }
        );
    }


    // =========================================================
    // SCAN ATTRIBUTES
    // =========================================================

    function scanAttributes(
        root
    ) {

        if (
            !root ||
            !root.querySelectorAll
        ) {

            return;
        }

        const elements =
            root.querySelectorAll(
                [
                    "input[placeholder]",
                    "textarea[placeholder]",
                    "[aria-label]",
                    "[title]",
                    "option"
                ].join(",")
            );


        elements.forEach(
            function (
                element
            ) {

                if (
                    shouldSkipElement(
                        element
                    )
                ) {

                    return;
                }


                [
                    "placeholder",
                    "aria-label",
                    "title"
                ].forEach(
                    function (
                        attribute
                    ) {

                        if (
                            !element.hasAttribute(
                                attribute
                            )
                        ) {

                            return;
                        }

                        const source =
                            getOriginalAttribute(
                                element,
                                attribute
                            ).trim();

                        if (
                            !source ||
                            !/[A-Za-z]/.test(
                                source
                            )
                        ) {

                            return;
                        }

                        enqueue(
                            source,

                            function (
                                translated
                            ) {

                                if (
                                    element.isConnected
                                ) {

                                    element.setAttribute(
                                        attribute,
                                        translated
                                    );
                                }
                            }
                        );

                    }
                );


                // OPTION TEXT
                if (
                    element.tagName ===
                    "OPTION"
                ) {

                    const source =
                        getOriginalOptionText(
                            element
                        ).trim();

                    if (
                        !source ||
                        !/[A-Za-z]/.test(
                            source
                        )
                    ) {

                        return;
                    }

                    enqueue(
                        source,

                        function (
                            translated
                        ) {

                            if (
                                element.isConnected
                            ) {

                                element.textContent =
                                    translated;
                            }
                        }
                    );
                }

            }
        );
    }


    // =========================================================
    // SCAN COMPLETE PAGE
    // =========================================================

    function scanPage(
        root
    ) {

        const language =
            getLanguage();

        document.documentElement.lang =
            language;

        document.documentElement.setAttribute(
            "data-language",
            language
        );

        if (
            language === "en"
        ) {

            return;
        }

        scanText(
            root
        );

        scanAttributes(
            root
        );

        scheduleFlush();
    }


    // =========================================================
    // GLOBAL LANGUAGE SELECTOR
    // =========================================================

    function addSelector() {

        if (
            document.getElementById(
                "languageSelect"
            )
        ) {

            return;
        }

        if (
            document.getElementById(
                "smartKisanGlobalLanguage"
            )
        ) {

            return;
        }


        const wrapper =
            document.createElement(
                "div"
            );

        wrapper.id =
            "smartKisanGlobalLanguage";


        wrapper.innerHTML = `
            <label
                for="smartKisanLanguageSelect"
            >
                🌐
            </label>

            <select
                id="smartKisanLanguageSelect"
                aria-label="Select language"
            >

                <option value="en">
                    English
                </option>

                <option value="hi">
                    हिन्दी
                </option>

                <option value="mr">
                    मराठी
                </option>

            </select>
        `;


        Object.assign(
            wrapper.style,
            {

                position:
                    "fixed",

                top:
                    "14px",

                right:
                    "14px",

                zIndex:
                    "99999",

                display:
                    "flex",

                alignItems:
                    "center",

                gap:
                    "6px",

                padding:
                    "7px 9px",

                borderRadius:
                    "12px",

                background:
                    "rgba(8,27,14,.94)",

                border:
                    "1px solid rgba(120,220,145,.20)",

                boxShadow:
                    "0 10px 30px rgba(0,0,0,.25)",

                backdropFilter:
                    "blur(12px)",

                color:
                    "white",

                fontSize:
                    "12px"
            }
        );


        const select =
            wrapper.querySelector(
                "select"
            );


        Object.assign(
            select.style,
            {

                border:
                    "0",

                background:
                    "transparent",

                color:
                    "white",

                fontWeight:
                    "700",

                outline:
                    "none",

                cursor:
                    "pointer"

            }
        );


        select.value =
            getLanguage();


        select.addEventListener(
            "change",
            async function () {

                const language =
                    this.value;


                localStorage.setItem(
                    "smartKisanLanguage",
                    language
                );


                try {

                    const response =
                        await fetch(
                            "/set-language",
                            {

                                method:
                                    "POST",

                                headers:
                                    {
                                        "Content-Type":
                                            "application/json"
                                    },

                                body:
                                    JSON.stringify({
                                        language:
                                            language
                                    })

                            }
                        );


                    const data =
                        await response.json();


                    if (
                        !response.ok ||
                        !data.success
                    ) {

                        throw new Error(
                            data.error ||
                            "Unable to change language."
                        );
                    }


                    window.location.reload();


                } catch (
                    error
                ) {

                    alert(
                        error.message ||
                        "Unable to change language."
                    );

                    this.value =
                        getLanguage();
                }

            }
        );


        document.body.appendChild(
            wrapper
        );
    }


    // =========================================================
    // START
    // =========================================================

    document.addEventListener(
        "DOMContentLoaded",
        function () {

            addSelector();

            scanPage(
                document.body
            );


            // Watch for AI-generated content
            // and dynamically inserted elements.

            const observer =
                new MutationObserver(
                    function (
                        mutations
                    ) {

                        if (
                            getLanguage() ===
                            "en"
                        ) {

                            return;
                        }


                        mutations.forEach(
                            function (
                                mutation
                            ) {

                                mutation
                                    .addedNodes
                                    .forEach(
                                        function (
                                            node
                                        ) {

                                            scanText(
                                                node
                                            );


                                            if (
                                                node.nodeType ===
                                                Node.ELEMENT_NODE
                                            ) {

                                                scanAttributes(
                                                    node
                                                );

                                            }

                                        }
                                    );

                            }
                        );


                        scheduleFlush();
                    }
                );


            observer.observe(
                document.body,
                {
                    childList:
                        true,

                    subtree:
                        true
                }
            );

        }
    );

})();