/* =========================================================
   SMART KISAN AI
   FIRST PAGE JAVASCRIPT
========================================================= */

document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       TRANSLATIONS
    ===================================================== */

    const translations = {

        en: {

            home: "Home",
            features: "Features",
            about: "About",
            contact: "Contact",

            login: "Login",
            register: "Register",

            hero_badge:
                "AI Powered Agriculture",

            hero_line_1:
                "Smart Farming.",

            hero_line_2:
                "Better Future.",

            hero_description:
                "Smart Kisan AI brings farming tools, weather information, AI assistance, crop reports and government schemes together in one simple platform for farmers.",

            get_started:
                "Get Started",

            explore_features:
                "Explore Features",

            hero_point_1:
                "Farmer Friendly",

            hero_point_2:
                "AI Powered",

            hero_point_3:
                "Location Based",

            smart_agriculture:
                "SMART AGRICULTURE",

            future_farming:
                "Future of Farming",

            live_weather:
                "Live Weather",

            ai_tools:
                "AI Tools",

            ready:
                "Ready",

            main_features:
                "SMART KISAN FEATURES",

            features_title:
                "Everything a Farmer Needs",

            features_description:
                "Important farming services are available in one place, designed to be simple and easy for farmers to use.",

            farmer_details:
                "Farmer Details",

            farmer_description:
                "Manage farmer name, mobile number, location and language information.",

            farm_details:
                "Farm Details",

            farm_description:
                "Store farm area, soil type, irrigation, water source, season and location.",

            live_weather_title:
                "Live Weather",

            weather_description:
                "Get live weather information for your farm location and monitor farming conditions.",

            ai_tools_title:
                "AI Tools",

            ai_description:
                "Access smart agriculture AI tools including crop assistance, disease analysis and more.",

            crop_report:
                "Crop Report",

            crop_description:
                "Explore useful crop information, reports and farming insights.",

            government_schemes:
                "Government Schemes",

            scheme_description:
                "Find useful government agriculture schemes and farmer support information.",

            open:
                "Open",

            about_label:
                "ABOUT SMART KISAN AI",

            about_title:
                "Technology Made for Farmers",

            about_text:
                "Smart Kisan AI is designed to bring important agricultural information and smart farming tools into one easy-to-use platform.",

            about_point_1:
                "Farmer-friendly interface",

            about_point_2:
                "English, Hindi and Marathi support",

            about_point_3:
                "Location-based farming information",

            about_point_4:
                "AI-powered agriculture tools",

            about_card:
                "Smart technology for smarter farming.",

            cta_title:
                "Make Your Farming Smarter",

            cta_text:
                "Create your farmer profile and start using Smart Kisan AI.",

            register_now:
                "Register Now →",

            contact_label:
                "CONTACT",

            contact_title:
                "Smart Support for Smart Farmers",

            contact_text:
                "Smart Kisan AI is built to make agricultural technology easier and more useful for farmers.",

            footer_text:
                "Smart technology for a smarter agricultural future.",

            rights:
                "All rights reserved."
        },


        hi: {

            home:
                "होम",

            features:
                "फीचर्स",

            about:
                "हमारे बारे में",

            contact:
                "संपर्क",

            login:
                "लॉगिन",

            register:
                "रजिस्टर",

            hero_badge:
                "AI आधारित कृषि",

            hero_line_1:
                "स्मार्ट खेती।",

            hero_line_2:
                "बेहतर भविष्य।",

            hero_description:
                "Smart Kisan AI किसानों के लिए खेती के उपकरण, मौसम की जानकारी, AI सहायता, फसल रिपोर्ट और सरकारी योजनाओं को एक आसान प्लेटफॉर्म पर लाता है।",

            get_started:
                "शुरू करें",

            explore_features:
                "फीचर्स देखें",

            hero_point_1:
                "किसान अनुकूल",

            hero_point_2:
                "AI आधारित",

            hero_point_3:
                "स्थान आधारित",

            smart_agriculture:
                "स्मार्ट कृषि",

            future_farming:
                "खेती का भविष्य",

            live_weather:
                "लाइव मौसम",

            ai_tools:
                "AI टूल्स",

            ready:
                "तैयार",

            main_features:
                "SMART KISAN फीचर्स",

            features_title:
                "किसान के लिए जरूरी सभी सुविधाएं",

            features_description:
                "खेती की महत्वपूर्ण सुविधाएं एक ही जगह उपलब्ध हैं और इन्हें किसानों के लिए आसान बनाया गया है।",

            farmer_details:
                "किसान विवरण",

            farmer_description:
                "किसान का नाम, मोबाइल नंबर, स्थान और भाषा की जानकारी प्रबंधित करें।",

            farm_details:
                "खेत विवरण",

            farm_description:
                "खेत का क्षेत्रफल, मिट्टी, सिंचाई, पानी का स्रोत, मौसम और स्थान की जानकारी रखें।",

            live_weather_title:
                "लाइव मौसम",

            weather_description:
                "अपने खेत के स्थान के लिए लाइव मौसम की जानकारी प्राप्त करें।",

            ai_tools_title:
                "AI टूल्स",

            ai_description:
                "फसल सहायता, रोग विश्लेषण और अन्य स्मार्ट कृषि AI टूल्स का उपयोग करें।",

            crop_report:
                "फसल रिपोर्ट",

            crop_description:
                "उपयोगी फसल जानकारी, रिपोर्ट और कृषि संबंधी जानकारी देखें।",

            government_schemes:
                "सरकारी योजनाएं",

            scheme_description:
                "कृषि और किसानों के लिए उपयोगी सरकारी योजनाओं की जानकारी प्राप्त करें।",

            open:
                "खोलें",

            about_label:
                "SMART KISAN AI के बारे में",

            about_title:
                "किसानों के लिए बनाया गया तकनीक",

            about_text:
                "Smart Kisan AI महत्वपूर्ण कृषि जानकारी और स्मार्ट खेती के उपकरणों को एक आसान प्लेटफॉर्म पर लाने के लिए बनाया गया है।",

            about_point_1:
                "किसान के लिए आसान इंटरफेस",

            about_point_2:
                "अंग्रेजी, हिंदी और मराठी समर्थन",

            about_point_3:
                "स्थान आधारित कृषि जानकारी",

            about_point_4:
                "AI आधारित कृषि उपकरण",

            about_card:
                "स्मार्ट खेती के लिए स्मार्ट तकनीक।",

            cta_title:
                "अपनी खेती को स्मार्ट बनाएं",

            cta_text:
                "अपनी किसान प्रोफाइल बनाएं और Smart Kisan AI का उपयोग शुरू करें।",

            register_now:
                "अभी रजिस्टर करें →",

            contact_label:
                "संपर्क",

            contact_title:
                "स्मार्ट किसानों के लिए स्मार्ट सहायता",

            contact_text:
                "Smart Kisan AI कृषि तकनीक को किसानों के लिए आसान और अधिक उपयोगी बनाने के लिए बनाया गया है।",

            footer_text:
                "स्मार्ट कृषि भविष्य के लिए स्मार्ट तकनीक।",

            rights:
                "सर्वाधिकार सुरक्षित।"
        },


        mr: {

            home:
                "मुख्यपृष्ठ",

            features:
                "फीचर्स",

            about:
                "आमच्याबद्दल",

            contact:
                "संपर्क",

            login:
                "लॉगिन",

            register:
                "नोंदणी",

            hero_badge:
                "AI आधारित शेती",

            hero_line_1:
                "स्मार्ट शेती.",

            hero_line_2:
                "चांगले भविष्य.",

            hero_description:
                "Smart Kisan AI शेतकऱ्यांसाठी शेती साधने, हवामान माहिती, AI मदत, पीक अहवाल आणि सरकारी योजना एका सोप्या प्लॅटफॉर्मवर आणते.",

            get_started:
                "सुरुवात करा",

            explore_features:
                "फीचर्स पहा",

            hero_point_1:
                "शेतकरी अनुकूल",

            hero_point_2:
                "AI आधारित",

            hero_point_3:
                "स्थान आधारित",

            smart_agriculture:
                "स्मार्ट शेती",

            future_farming:
                "शेतीचे भविष्य",

            live_weather:
                "लाइव्ह हवामान",

            ai_tools:
                "AI टूल्स",

            ready:
                "तयार",

            main_features:
                "SMART KISAN फीचर्स",

            features_title:
                "शेतकऱ्याला आवश्यक सर्व सुविधा",

            features_description:
                "शेतीसाठी आवश्यक सेवा एका ठिकाणी उपलब्ध आहेत आणि शेतकऱ्यांसाठी वापरण्यास सोप्या आहेत.",

            farmer_details:
                "शेतकरी माहिती",

            farmer_description:
                "शेतकऱ्याचे नाव, मोबाईल नंबर, स्थान आणि भाषेची माहिती व्यवस्थापित करा.",

            farm_details:
                "शेती माहिती",

            farm_description:
                "शेताचे क्षेत्रफळ, माती, सिंचन, पाण्याचा स्रोत, हंगाम आणि स्थानाची माहिती ठेवा.",

            live_weather_title:
                "लाइव्ह हवामान",

            weather_description:
                "तुमच्या शेताच्या स्थानासाठी लाइव्ह हवामानाची माहिती मिळवा.",

            ai_tools_title:
                "AI टूल्स",

            ai_description:
                "पीक सहाय्य, रोग विश्लेषण आणि इतर स्मार्ट कृषी AI टूल्स वापरा.",

            crop_report:
                "पीक अहवाल",

            crop_description:
                "उपयुक्त पीक माहिती, अहवाल आणि शेतीसंबंधी माहिती पहा.",

            government_schemes:
                "सरकारी योजना",

            scheme_description:
                "शेतकरी आणि कृषीसाठी उपयुक्त सरकारी योजनांची माहिती मिळवा.",

            open:
                "उघडा",

            about_label:
                "SMART KISAN AI बद्दल",

            about_title:
                "शेतकऱ्यांसाठी तयार केलेले तंत्रज्ञान",

            about_text:
                "Smart Kisan AI महत्त्वाची कृषी माहिती आणि स्मार्ट शेतीची साधने एका सोप्या प्लॅटफॉर्मवर आणण्यासाठी तयार केले आहे.",

            about_point_1:
                "शेतकरी अनुकूल इंटरफेस",

            about_point_2:
                "इंग्रजी, हिंदी आणि मराठी समर्थन",

            about_point_3:
                "स्थान आधारित कृषी माहिती",

            about_point_4:
                "AI आधारित कृषी साधने",

            about_card:
                "स्मार्ट शेतीसाठी स्मार्ट तंत्रज्ञान.",

            cta_title:
                "तुमची शेती स्मार्ट बनवा",

            cta_text:
                "तुमची शेतकरी प्रोफाइल तयार करा आणि Smart Kisan AI वापरण्यास सुरुवात करा.",

            register_now:
                "आता नोंदणी करा →",

            contact_label:
                "संपर्क",

            contact_title:
                "स्मार्ट शेतकऱ्यांसाठी स्मार्ट मदत",

            contact_text:
                "Smart Kisan AI कृषी तंत्रज्ञान शेतकऱ्यांसाठी सोपे आणि अधिक उपयुक्त करण्यासाठी तयार करण्यात आले आहे.",

            footer_text:
                "स्मार्ट कृषी भविष्यासाठी स्मार्ट तंत्रज्ञान.",

            rights:
                "सर्व हक्क राखीव."
        }

    };


    /* =====================================================
       APPLY TRANSLATION
    ===================================================== */

    function applyLanguage(language) {

        const selected =
            translations[language]
                ? language
                : "en";

        const elements =
            document.querySelectorAll("[data-i18n]");

        elements.forEach(function (element) {

            const key =
                element.getAttribute("data-i18n");

            if (
                translations[selected][key]
            ) {
                element.textContent =
                    translations[selected][key];
            }

        });

        document.documentElement.lang =
            selected;

        localStorage.setItem(
            "smartKisanLanguage",
            selected
        );
    }


    /* =====================================================
       LANGUAGE SELECTOR
    ===================================================== */

    const languageSelector =
        document.getElementById(
            "languageSelector"
        );

    const savedLanguage =
        localStorage.getItem(
            "smartKisanLanguage"
        ) || "en";

    if (languageSelector) {

        languageSelector.value =
            savedLanguage;

        languageSelector.addEventListener(
            "change",
            function () {

                applyLanguage(
                    this.value
                );

            }
        );
    }

    applyLanguage(savedLanguage);


    /* =====================================================
       MOBILE MENU
    ===================================================== */

    const menuButton =
        document.getElementById(
            "menuButton"
        );

    const mobileMenu =
        document.getElementById(
            "mobileMenu"
        );

    if (
        menuButton &&
        mobileMenu
    ) {

        menuButton.addEventListener(
            "click",
            function () {

                mobileMenu.classList.toggle(
                    "open"
                );

                menuButton.textContent =
                    mobileMenu.classList.contains(
                        "open"
                    )
                    ? "✕"
                    : "☰";

            }
        );


        mobileMenu
            .querySelectorAll("a")
            .forEach(function (link) {

                link.addEventListener(
                    "click",
                    function () {

                        mobileMenu.classList.remove(
                            "open"
                        );

                        menuButton.textContent =
                            "☰";

                    }
                );

            });

    }


    /* =====================================================
       ACTIVE NAVIGATION
    ===================================================== */

    const sections =
        document.querySelectorAll(
            "section[id]"
        );

    const navLinks =
        document.querySelectorAll(
            ".desktop-nav .nav-link"
        );

    function updateActiveNavigation() {

        let current =
            "home";

        sections.forEach(
            function (section) {

                const top =
                    section.offsetTop - 150;

                if (
                    window.scrollY >= top
                ) {
                    current =
                        section.getAttribute(
                            "id"
                        );
                }

            }
        );

        navLinks.forEach(
            function (link) {

                link.classList.remove(
                    "active"
                );

                if (
                    link.getAttribute(
                        "href"
                    ) === "#" + current
                ) {
                    link.classList.add(
                        "active"
                    );
                }

            }
        );

    }

    window.addEventListener(
        "scroll",
        updateActiveNavigation
    );

    updateActiveNavigation();


    /* =====================================================
       SMOOTH SCROLL
    ===================================================== */

    document
        .querySelectorAll(
            'a[href^="#"]'
        )
        .forEach(
            function (link) {

                link.addEventListener(
                    "click",
                    function (event) {

                        const targetId =
                            this.getAttribute(
                                "href"
                            );

                        if (
                            targetId === "#"
                        ) {
                            return;
                        }

                        const target =
                            document.querySelector(
                                targetId
                            );

                        if (target) {

                            event.preventDefault();

                            target.scrollIntoView({
                                behavior: "smooth",
                                block: "start"
                            });

                        }

                    }
                );

            }
        );


    /* =====================================================
       CLOSE MOBILE MENU OUTSIDE
    ===================================================== */

    document.addEventListener(
        "click",
        function (event) {

            if (
                !mobileMenu ||
                !menuButton
            ) {
                return;
            }

            if (
                mobileMenu.classList.contains(
                    "open"
                ) &&
                !mobileMenu.contains(
                    event.target
                ) &&
                !menuButton.contains(
                    event.target
                )
            ) {

                mobileMenu.classList.remove(
                    "open"
                );

                menuButton.textContent =
                    "☰";

            }

        }
    );


    /* =====================================================
       FOOTER YEAR
    ===================================================== */

    const year =
        document.getElementById(
            "year"
        );

    if (year) {

        year.textContent =
            new Date().getFullYear();

    }


});