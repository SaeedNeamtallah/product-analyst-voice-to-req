/**
 * Tawasul Web Frontend
 * Main Application Logic
 */

// Configuration
const API_BASE_URL = `${globalThis.location.protocol}//${globalThis.location.hostname}:8500`;

const inMemoryStorage = {};

function safeStorageGet(key, fallback = null) {
    try {
        const value = globalThis.localStorage.getItem(key);
        return value === null ? fallback : value;
    } catch (error) {
        console.warn('localStorage get failed, using in-memory fallback.', error);
        const value = inMemoryStorage[key];
        return value === undefined ? fallback : value;
    }
}

function safeStorageSet(key, value) {
    inMemoryStorage[key] = String(value);
    try {
        globalThis.localStorage.setItem(key, value);
    } catch (error) {
        console.warn('localStorage set failed, kept in-memory value.', error);
    }
}

function safeStorageRemove(key) {
    delete inMemoryStorage[key];
    try {
        globalThis.localStorage.removeItem(key);
    } catch (error) {
        console.warn('localStorage remove failed, removed in-memory value only.', error);
    }
}

// Translations
const i18n = {
    ar: {
        nav_dashboard: "لوحة التحكم",
        nav_projects: "المشاريع",
        nav_chat: "مقابلة الذكاء الاصطناعي",
        nav_templates: "النماذج",
        interview_mode: "وضع المقابلة",
        nav_srs: "مستندات SRS",
        nav_settings: "الإعدادات",
        nav_ai_config: "نموذج الذكاء",
        ai_config_title: "نموذج الذكاء الاصطناعي",
        settings_title: "الإعدادات",
        settings_tab_ai: "نموذج الذكاء الاصطناعي",
        settings_tab_bot: "بوت تليجرام",
        project_files_btn: "ملفات المشروع",
        stat_projects: "إجمالي المشاريع",
        stat_docs: "المستندات",
        stat_chunks: "القطع النصية",
        recent_projects: "المشاريع الأخيرة",
        view_all: "عرض الكل",
        your_projects: "مشاريعك",
        project_goal_hint: "أضف هدفًا مختصرًا لمساعدة الذكاء الاصطناعي على توليد SRS أفضل.",
        welcome_title: "مرحباً بك في Tawasul",
        project_name_ph: "مثلاً: أبحاث الذكاء الاصطناعي",
        project_desc_ph: "وصف مختصر للمشروع...",
        create_project_btn: "إنشاء المشروع",
        upload_title: "رفع مستندات جديدة",
        upload_desc: "اسحب الملفات هنا أو اضغط للاختيار",
        upload_optional: "(اختياري) ارفع مستندات مرجعية لدعم المقابلة",
        start_interview_btn: "ابدأ المقابلة الذكية",
        interview_cta_hint: "ابدأ محادثة مع محلل الأعمال الذكي لبناء مستند المتطلبات",
        docs_title: "المستندات الحالية",
        bot_settings_title: "إعدادات بوت التليجرام",
        bot_active_project: "المشروع النشط",
        bot_active_project_desc: "اختر المشروع الذي سيقوم البوت بالإجابة منه.",
        save_settings: "حفظ الإعدادات",
        bot_profile: "ملف البوت",
        bot_profile_desc: "تحديث اسم البوت على تليجرام.",
        bot_name: "اسم البوت",
        update_profile: "تحديث الملف الشخصي",
        processing_label: "جار المعالجة",
        ai_settings_title: "إعدادات النماذج",
        ai_settings_desc: "اختر مزود التوليد.",
        gen_provider_label: "مزود التوليد",
        select_project_ph: "اختر مشروعاً...",
        delete_confirm: "هل أنت متأكد؟",
        success_saved: "تم الحفظ بنجاح",
        error_generic: "حدث خطأ ما",
        embedding_size_label: "أبعاد التضمين",
        config_group_providers: "المزودون",
        config_group_chunking: "التجزئة",
        config_group_retrieval: "الاسترجاع",
        search_placeholder: "ابحث عن مشروع أو مستند...",
        empty_projects: "لا توجد مشاريع بعد",
        empty_projects_desc: "أنشئ أول مشروع لك وابدأ في رفع المستندات.",
        empty_docs: "لا توجد مستندات بعد",
        empty_docs_desc: "ارفع ملفات PDF أو TXT أو DOCX لبدء المعالجة.",
        copy_btn: "نسخ",
        copied_btn: "تم النسخ!",
        srs_title: "مراجعة المتطلبات (SRS)",
        srs_subtitle: "نسخة أولية من المتطلبات مع نقاط تحتاج توضيح.",
        srs_refresh: "تحديث المسودة",
        srs_export: "تصدير SRS",
        srs_export_pdf: "تصدير PDF",
        srs_export_word: "تصدير Word",
        srs_export_markdown: "تصدير Markdown",
        srs_summary_title: "ملخص سريع",
        srs_open_questions: "نقاط تحتاج توضيح",
        srs_next_steps: "الخطوات القادمة",
        srs_book_meeting: "احجز جلسة مع الفريق",
        srs_confirm: "اعتماد المتطلبات",
        srs_confirmed: "تم اعتماد المتطلبات بنجاح!",
        book_meeting_title: "حجز جلسة مع الفريق التقني",
        book_name: "الاسم",
        book_email: "البريد الإلكتروني",
        book_date: "التاريخ المفضل",
        book_time: "الوقت المفضل",
        book_notes: "ملاحظات إضافية",
        book_submit: "تأكيد الحجز",
        book_success: "تم الحجز بنجاح! سيتم التواصل معك قريباً.",
        book_fill_required: "يرجى ملء جميع الحقول المطلوبة",
        stage_discovery: "الاستكشاف",
        stage_scope: "النطاق",
        stage_users: "المستخدمون",
        stage_features: "الميزات",
        stage_constraints: "القيود",
        mic_recording: "جاري التسجيل...",
        mic_transcribing: "جاري التحويل...",
        mic_error: "تعذر الوصول للميكروفون",
        mic_no_support: "المتصفح لا يدعم التسجيل الصوتي",
        live_doc_title: "ملخص المتطلبات",
        live_doc_empty: "ابدأ المقابلة وسيتم تحديث الملخص تلقائياً...",
        start_idea_btn: "ابدأ فكرة جديدة",
        upload_reference_docs: "رفع مستندات",
        start_idea_title: "ابدأ فكرة جديدة",
        idea_name_ph: "مثلاً: تطبيق إدارة المهام",
        start_idea_submit: "ابدأ الآن",
        confirm_yes: "نعم، متأكد",
        confirm_cancel: "إلغاء",
        offline_banner: "أنت غير متصل بالإنترنت",
        rate_limit_msg: "محاولات كثيرة. انتظر {seconds} ثانية",
        validation_email_invalid: "البريد الإلكتروني غير صالح",
        validation_password_min: "كلمة المرور يجب أن تكون 6 أحرف على الأقل",
        validation_required: "هذا الحقل مطلوب",
        validation_project_name: "يرجى إدخال اسم المشروع",
        interview_save_later: "احفظ وكمل بعدين",
        interview_resume: "استكمال آخر مقابلة",
        interview_select_hint: "اختر إجابة مقترحة",
        interview_select_send: "إرسال الاختيار",
        interview_option_skip: "تخطّي السؤال الحالي",
        interview_option_unsure: "مش متأكد - أعد صياغة السؤال ببساطة",
        interview_review: "مراجعة قبل الإرسال",
        interview_privacy: "بياناتك لن تُستخدم إلا لإعداد متطلبات المشروع وتحسين دقة التحليل.",
        interview_next_step: "الخطوة التالية: سيتم توليد SRS فورًا ويمكنك مراجعته واعتماده.",
        interview_restored: "تم استرجاع آخر جلسة مقابلة محفوظة.",
        interview_saved: "تم حفظ المقابلة. يمكنك المتابعة لاحقًا من نفس المشروع.",
        interview_completed: "اكتملت المقابلة! راجع الإجابات النهائية قبل الإرسال.",
        interview_duplicate_guard: "يبدو أن الإجابة مكررة. أضف تفصيلة جديدة أو استخدم تخطّي.",
        interview_progress: "تم الإنجاز: {percent}%",
        templates_title: "ابدأ بسرعة باستخدام قالب جاهز",
        template_use: "استخدم هذا القالب",
        template_ecommerce_title: "E-commerce SRS",
        template_ecommerce_desc: "متجر إلكتروني مع إدارة منتجات، سلة شراء، دفع، وتتبع الطلبات.",
        template_saas_title: "SaaS Platform",
        template_saas_desc: "منصة SaaS متعددة العملاء مع خطط اشتراك وصلاحيات ولوحة تقارير.",
        template_mobile_title: "Mobile App",
        template_mobile_desc: "تطبيق جوال مع تسجيل مستخدمين، إشعارات، وتكامل API."
    },
    en: {
        nav_dashboard: "Dashboard",
        nav_projects: "Projects",
        nav_chat: "AI Interview",
        nav_templates: "Templates",
        interview_mode: "Interview mode",
        nav_srs: "SRS Documents",
        nav_settings: "Settings",
        nav_ai_config: "AI Model",
        ai_config_title: "AI Model",
        settings_title: "Settings",
        settings_tab_ai: "AI Model",
        settings_tab_bot: "Telegram Bot",
        project_files_btn: "Project Files",
        stat_projects: "Total Projects",
        stat_docs: "Documents",
        stat_chunks: "Text Chunks",
        recent_projects: "Recent Projects",
        view_all: "View All",
        your_projects: "Your Projects",
        project_goal_hint: "Add a brief goal to help our AI generate a better SRS.",
        welcome_title: "Welcome to Tawasul",
        project_name_ph: "Ex: AI Research",
        project_desc_ph: "Short description...",
        create_project_btn: "Create Project",
        upload_title: "Upload New Documents",
        upload_desc: "Drag files here or click to select",
        upload_optional: "(Optional) Upload reference documents to support the interview",
        start_interview_btn: "Start Smart Interview",
        interview_cta_hint: "Chat with the AI Business Analyst to build your requirements document",
        docs_title: "Current Documents",
        bot_settings_title: "Telegram Bot Settings",
        bot_active_project: "Active Project",
        bot_active_project_desc: "Select the project the bot will answer from.",
        save_settings: "Save Settings",
        bot_profile: "Bot Profile",
        bot_profile_desc: "Update Bot Name on Telegram.",
        bot_name: "Bot Name",
        update_profile: "Update Profile",
        processing_label: "Processing",
        ai_settings_title: "Model Settings",
        ai_settings_desc: "Select the generation provider.",
        gen_provider_label: "Generation Provider",
        select_project_ph: "Select a project...",
        delete_confirm: "Are you sure?",
        success_saved: "Saved successfully",
        error_generic: "Something went wrong",
        embedding_size_label: "Embedding Dimensions",
        config_group_providers: "Providers",
        config_group_chunking: "Chunking",
        config_group_retrieval: "Retrieval",
        search_placeholder: "Search projects or documents...",
        empty_projects: "No projects yet",
        empty_projects_desc: "Create your first project and start uploading documents.",
        empty_docs: "No documents yet",
        empty_docs_desc: "Upload PDF, TXT, or DOCX files to start processing.",
        copy_btn: "Copy",
        copied_btn: "Copied!",
        srs_title: "SRS Review",
        srs_subtitle: "A first draft of requirements with items that need clarification.",
        srs_refresh: "Refresh Draft",
        srs_export: "Export SRS",
        srs_export_pdf: "Export PDF",
        srs_export_word: "Export Word",
        srs_export_markdown: "Export Markdown",
        srs_summary_title: "Quick Summary",
        srs_open_questions: "Open Questions",
        srs_next_steps: "Next Steps",
        srs_book_meeting: "Book a team session",
        srs_confirm: "Approve Requirements",
        srs_confirmed: "Requirements approved successfully!",
        book_meeting_title: "Book a session with the technical team",
        book_name: "Name",
        book_email: "Email",
        book_date: "Preferred Date",
        book_time: "Preferred Time",
        book_notes: "Additional Notes",
        book_submit: "Confirm Booking",
        book_success: "Booked successfully! We will contact you soon.",
        book_fill_required: "Please fill all required fields",
        stage_discovery: "Discovery",
        stage_scope: "Scope",
        stage_users: "Users",
        stage_features: "Features",
        stage_constraints: "Constraints",
        mic_recording: "Recording...",
        mic_transcribing: "Transcribing...",
        mic_error: "Cannot access microphone",
        mic_no_support: "Browser does not support audio recording",
        live_doc_title: "Requirements Summary",
        live_doc_empty: "Start the interview and the summary will update automatically...",
        start_idea_btn: "Start New Idea",
        upload_reference_docs: "Upload Docs",
        start_idea_title: "Start a New Idea",
        idea_name_ph: "Ex: Task Management App",
        start_idea_submit: "Start Now",
        confirm_yes: "Yes, confirm",
        confirm_cancel: "Cancel",
        offline_banner: "You are offline",
        rate_limit_msg: "Too many attempts. Wait {seconds} seconds",
        validation_email_invalid: "Invalid email address",
        validation_password_min: "Password must be at least 6 characters",
        validation_required: "This field is required",
        validation_project_name: "Please enter a project name",
        interview_save_later: "Save & continue later",
        interview_resume: "Resume last interview",
        interview_select_hint: "Choose a suggested answer",
        interview_select_send: "Send selection",
        interview_option_skip: "Skip this question",
        interview_option_unsure: "Not sure - please rephrase simply",
        interview_review: "Review before submit",
        interview_privacy: "Your data is used only for project requirements preparation and analysis quality.",
        interview_next_step: "Next step: SRS will be generated immediately for your review.",
        interview_restored: "Your latest saved interview session was restored.",
        interview_saved: "Interview progress saved. You can resume later from this project.",
        interview_completed: "Interview complete! Review final answers before submit.",
        interview_duplicate_guard: "This answer looks repeated. Add a new detail or use Skip.",
        interview_progress: "Completed: {percent}%",
        templates_title: "Start faster with ready templates",
        template_use: "Use this template",
        template_ecommerce_title: "E-commerce SRS",
        template_ecommerce_desc: "Online store with catalog, cart, checkout, payments, and order tracking.",
        template_saas_title: "SaaS Platform",
        template_saas_desc: "Multi-tenant SaaS platform with subscriptions, roles, and reporting dashboard.",
        template_mobile_title: "Mobile App",
        template_mobile_desc: "Mobile application with onboarding, notifications, and API integration."
    }
};

const INTERVIEW_AREAS = ['discovery', 'scope', 'users', 'features', 'constraints'];
const ADMIN_ONLY_VIEWS = new Set(['settings']);
const IDEA_TEMPLATES = {
    ecommerce: {
        ar: {
            title: 'E-commerce SRS',
            description: 'متجر إلكتروني مع إدارة المنتجات، سلة الشراء، الدفع، وتتبع الطلبات.',
            prompt: 'نطاق المشروع: متجر إلكتروني B2C. ركّز على إدارة المنتجات، السلة، الدفع، وتتبع الشحن، وسياسات الإرجاع.'
        },
        en: {
            title: 'E-commerce SRS',
            description: 'Online store with catalog, cart, payments, and order tracking.',
            prompt: 'Project scope: B2C e-commerce. Focus on product catalog, cart, checkout, shipping tracking, and returns policy.'
        }
    },
    saas: {
        ar: {
            title: 'SaaS Platform',
            description: 'منصة SaaS متعددة العملاء مع اشتراكات وصلاحيات ولوحات تقارير.',
            prompt: 'نطاق المشروع: منصة SaaS متعددة العملاء. ركّز على خطط الاشتراك، إدارة الفرق، الصلاحيات، ولوحة تقارير للإدارة.'
        },
        en: {
            title: 'SaaS Platform',
            description: 'Multi-tenant SaaS platform with subscriptions, roles, and dashboards.',
            prompt: 'Project scope: multi-tenant SaaS. Focus on subscription plans, team management, role permissions, and admin reporting dashboard.'
        }
    },
    'mobile-app': {
        ar: {
            title: 'Mobile App',
            description: 'تطبيق جوال مع تسجيل المستخدمين، إشعارات، وتكامل API.',
            prompt: 'نطاق المشروع: تطبيق جوال iOS/Android. ركّز على التسجيل، ملفات المستخدمين، الإشعارات، وتجربة استخدام سريعة.'
        },
        en: {
            title: 'Mobile App',
            description: 'Mobile app with onboarding, notifications, and API integration.',
            prompt: 'Project scope: iOS/Android mobile app. Focus on onboarding, profile management, notifications, and fast UX flows.'
        }
    }
};

// State Management
const state = {
    currentView: 'projects',
    projects: [],
    stats: null,
    selectedProject: null,
    chatMessages: [],
    isUploading: false,
    docPoller: null,
    interviewMode: false,
    interviewStage: 'discovery',
    isRecording: false,
    mediaRecorder: null,
    pendingProjectSelect: null,
    chatProjectId: null,
    srsRefreshing: false,
    previousSummary: null,
    lastCoverage: null,
    lastInterviewSignals: null,
    lastLivePatch: null,
    lastCycleTrace: null,
    lastTopicNavigation: null,
    lastInterviewTelemetry: null,
    interviewDraftMeta: null,
    lastAssistantQuestion: '',
    lastUserInterviewAnswer: '',
    lastRenderedSrsDraft: null,
    pendingInterviewSelectionMeta: null,
    pendingSttMeta: null,
    summaryCollapsed: true,
    authToken: safeStorageGet('authToken', null),
    currentUser: JSON.parse(safeStorageGet('currentUser', 'null')),
    lang: safeStorageGet('lang', 'ar'),
    theme: safeStorageGet('theme', 'light')
};

let _msgIdCounter = 0;

function getFallbackSrsDraft() {
    return {
        status: state.lang === 'ar' ? 'مسودة أولية' : 'First Draft',
        updated: state.lang === 'ar' ? 'آخر تحديث: اليوم' : 'Last updated: today',
        summary: state.lang === 'ar'
            ? 'لا توجد مسودة بعد. حدّث المحادثة أولاً ثم اضغط تحديث المسودة.'
            : 'No draft yet. Start a chat and click refresh to generate one.',
        metrics: [],
        sections: [],
        activity_diagram: [],
        questions: [],
        nextSteps: []
    };
}

// DOM Elements
const elements = {
    viewContainer: document.getElementById('view-container'),
    navItems: document.querySelectorAll('.sidebar-nav li'),
    newProjectBtn: document.getElementById('new-project-btn'),
    modalOverlay: document.getElementById('modal-overlay'),
    modalTitle: document.getElementById('modal-title'),
    modalBody: document.getElementById('modal-body'),
    closeModalBtn: document.querySelector('.close-modal'),
    themeToggle: document.getElementById('theme-toggle'),
    langToggle: document.getElementById('lang-toggle'),
    sidebarToggleBtn: document.getElementById('sidebar-toggle-btn')
};

function isAdminUser() {
    return Boolean(state.currentUser?.role === 'admin');
}

function applyRoleBasedNavigation() {
    const isAdmin = isAdminUser();
    elements.navItems.forEach((item) => {
        const viewName = item.dataset.view;
        if (!viewName) return;
        if (!ADMIN_ONLY_VIEWS.has(viewName)) return;
        item.style.display = isAdmin ? '' : 'none';
    });
}

// --- API Client ---

function authHeaders(extra = {}) {
    const headers = { ...extra };
    if (state.authToken) {
        headers['Authorization'] = `Bearer ${state.authToken}`;
    }
    return headers;
}

// --- Network Offline Banner helpers (3.5) ---

function showOfflineBanner() {
    const banner = document.getElementById('offline-banner');
    if (banner) banner.classList.add('visible');
}

function hideOfflineBanner() {
    const banner = document.getElementById('offline-banner');
    if (banner) banner.classList.remove('visible');
}

async function throwIfNotOk(response, fallbackMessage = 'Request failed') {
    if (!response.ok) {
        const contentType = response.headers.get('content-type') || '';
        const err = contentType.includes('application/json') ? await response.json() : null;
        throw new Error(err?.detail || fallbackMessage);
    }
    return response;
}

const api = {
    async get(endpoint, requestOptions = {}) {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                headers: authHeaders(),
                ...requestOptions
            });
            if (response.status === 401) {
                clearAuthState();
                showAuthScreen();
                throw new Error(state.lang === 'ar' ? 'انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى' : 'Session expired, please login again');
            }
            await throwIfNotOk(response);
            hideOfflineBanner();
            return await response.json();
        } catch (error) {
            console.error(`API Get Error (${endpoint}):`, error);
            if (error instanceof TypeError) {
                showOfflineBanner();
            } else {
                showNotification(error.message || (state.lang === 'ar' ? 'خطأ في الاتصال بالسيرفر' : 'Server Connection Error'), 'error');
            }
            throw error;
        }
    },

    async post(endpoint, data, isFormData = false, requestOptions = {}) {
        try {
            const headers = isFormData
                ? authHeaders()
                : authHeaders({ 'Content-Type': 'application/json' });
            const options = {
                method: 'POST',
                headers,
                body: isFormData ? data : JSON.stringify(data),
                ...requestOptions
            };

            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
            if (response.status === 401) {
                clearAuthState();
                showAuthScreen();
                throw new Error(state.lang === 'ar' ? 'انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى' : 'Session expired, please login again');
            }
            await throwIfNotOk(response);
            hideOfflineBanner();
            return await response.json();
        } catch (error) {
            console.error(`API Post Error (${endpoint}):`, error);
            if (error instanceof TypeError) {
                showOfflineBanner();
            } else {
                showNotification(error.message, 'error');
            }
            throw error;
        }
    },

    async delete(endpoint, requestOptions = {}) {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'DELETE',
                headers: authHeaders(),
                ...requestOptions
            });
            if (response.status === 401) {
                clearAuthState();
                showAuthScreen();
                throw new Error(state.lang === 'ar' ? 'انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى' : 'Session expired, please login again');
            }
            await throwIfNotOk(response);
            return true;
        } catch (error) {
            console.error(`API Delete Error (${endpoint}):`, error);
            showNotification(error.message, 'error');
            throw error;
        }
    }
};

// --- View Rendering ---

const views = {
    async dashboard() {
        renderTemplate('dashboard-template');
        showLoader();

        try {
            const [projects, stats] = await Promise.all([
                api.get('/projects/'),
                api.get('/stats/')
            ]);
            state.projects = projects;

            // Animate stats
            animateCounter('stat-projects-dashboard', stats.projects);
            animateCounter('stat-docs-dashboard', stats.documents);

            // Render recent projects
            const list = document.getElementById('recent-projects-list-dashboard');
            list.innerHTML = '';
            if (projects.length === 0) {
                list.innerHTML = createEmptyState('fa-folder-open', 'empty_projects', 'empty_projects_desc');
            } else {
                projects.slice(0, 3).forEach(project => {
                    list.appendChild(createProjectCard(project));
                });
            }

            // View All link -> switch to projects
            const viewAllLink = document.querySelector('.section-header .link');
            if (viewAllLink) {
                viewAllLink.onclick = (e) => { e.preventDefault(); switchView('projects'); };
            }

            applyTranslations();
        } catch (error) {
            console.error('Dashboard Load Error:', error);
        } finally {
            hideLoader();
        }
    },

    async projects() {
        renderTemplate('projects-template');
        showLoader();

        try {
            const projectsNewBtn = document.getElementById('projects-new-project-btn');
            if (projectsNewBtn) {
                projectsNewBtn.onclick = handleNewProject;
            }

            const [projects, stats] = await Promise.all([
                api.get('/projects/'),
                api.get('/stats/')
            ]);
            state.projects = projects;

            animateCounter('stat-projects', stats.projects || projects.length || 0);
            animateCounter('stat-docs', stats.documents || 0);

            const list = document.getElementById('all-projects-list');
            list.innerHTML = '';
            if (projects.length === 0) {
                list.innerHTML = createEmptyState('fa-folder-open', 'empty_projects', 'empty_projects_desc');
            } else {
                projects.forEach(project => {
                    list.appendChild(createProjectCard(project));
                });
            }
            applyTranslations();
        } catch (error) {
            console.error('Projects Load Error:', error);
        } finally {
            hideLoader();
        }
    },

    async chat() {
        renderTemplate('chat-template');

        const select = document.getElementById('chat-project-select');
        const projects = await api.get('/projects/');

        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            select.appendChild(opt);
        });

        // Auto-select project if coming from "Start New Idea"
        if (state.pendingProjectSelect) {
            select.value = state.pendingProjectSelect;
            state.chatProjectId = state.pendingProjectSelect;
            updateChatProjectHeader(state.pendingProjectSelect);
            loadChatHistory(state.pendingProjectSelect);
            state.pendingProjectSelect = null;
        } else if (state.chatProjectId) {
            select.value = state.chatProjectId;
            updateChatProjectHeader(state.chatProjectId);
            loadChatHistory(state.chatProjectId);
        } else if (projects.length > 0) {
            const lastProjectId = Number(projects[projects.length - 1].id);
            select.value = String(lastProjectId);
            state.chatProjectId = lastProjectId;
            updateChatProjectHeader(lastProjectId);
            loadChatHistory(lastProjectId);
        } else {
            // No projects at all — show empty state CTA
            const messagesContainer = document.getElementById('chat-messages');
            if (messagesContainer) {
                updateChatProjectHeader(null);
                messagesContainer.innerHTML = `
                    <div class="welcome-msg-pro">
                        <div class="welcome-icon"><i class="fas fa-folder-plus"></i></div>
                        <h2>${state.lang === 'ar' ? 'لا توجد مشاريع بعد' : 'No projects yet'}</h2>
                        <p>${state.lang === 'ar' ? 'أنشئ مشروعك الأول لبدء المقابلة الذكية' : 'Create your first project to start an interview'}</p>
                        <button class="btn btn-primary mt-4" id="chat-new-project-cta">
                            <i class="fas fa-plus"></i>
                            <span>${state.lang === 'ar' ? 'إنشاء مشروع جديد' : 'Create a project'}</span>
                        </button>
                    </div>
                `;
                const cta = document.getElementById('chat-new-project-cta');
                if (cta) cta.onclick = handleNewProject;
            }
        }

        if (select.value) {
            const draft = await loadInterviewDraft(Number.parseInt(select.value, 10));
            if (draft) {
                state.previousSummary = draft.summary || null;
                state.lastCoverage = draft.coverage || null;
                state.lastInterviewSignals = draft.signals || null;
                state.lastLivePatch = draft.livePatch || null;
                state.lastCycleTrace = draft.cycleTrace || null;
                state.lastTopicNavigation = draft.topicNavigation || null;
                state.interviewStage = draft.stage || 'discovery';
                state.lastAssistantQuestion = draft.lastAssistantQuestion || '';
                state.interviewDraftMeta = draft;
                if (draft.mode) state.interviewMode = true;
                showNotification(i18n[state.lang].interview_restored, 'info');
            }
        }

        // Load chat history when switching projects
        select.onchange = async () => {
            if (select.value) {
                state.chatProjectId = Number.parseInt(select.value, 10);
                updateChatProjectHeader(state.chatProjectId);
                loadChatHistory(state.chatProjectId);
                const draft = await loadInterviewDraft(state.chatProjectId);
                if (draft) {
                    state.previousSummary = draft.summary || null;
                    state.lastCoverage = draft.coverage || null;
                    state.lastInterviewSignals = draft.signals || null;
                    state.lastLivePatch = draft.livePatch || null;
                    state.lastCycleTrace = draft.cycleTrace || null;
                    state.lastTopicNavigation = draft.topicNavigation || null;
                    state.interviewStage = draft.stage || 'discovery';
                    state.lastAssistantQuestion = draft.lastAssistantQuestion || '';
                    state.interviewDraftMeta = draft;
                    if (draft.mode) state.interviewMode = true;
                    if (interviewToggle) interviewToggle.checked = state.interviewMode;
                    showNotification(i18n[state.lang].interview_restored, 'info');
                } else {
                    state.previousSummary = null;
                    state.lastCoverage = null;
                    state.lastInterviewSignals = null;
                    state.lastLivePatch = null;
                    state.lastCycleTrace = null;
                    state.lastTopicNavigation = null;
                    state.interviewDraftMeta = null;
                    state.lastAssistantQuestion = '';
                }
                updateInterviewProgress(state.lastCoverage, false);
                updateInterviewAssistBar(state.lastCoverage);
                if (typeof updateResumeButtonState === 'function') {
                    updateResumeButtonState();
                }
            }
        };

        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        const langSelect = document.getElementById('chat-lang');
        const clearBtn = document.getElementById('clear-chat-btn');
        const interviewToggle = document.getElementById('chat-interview-toggle');
        const summaryToggleBtn = document.getElementById('summary-toggle-btn');

        // Enable/disable send button based on input
        chatInput.oninput = () => {
            sendBtn.disabled = !chatInput.value.trim();
            autoResizeTextarea(chatInput);
        };

        sendBtn.onclick = handleChatSubmit;
        chatInput.onkeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (chatInput.value.trim()) handleChatSubmit();
            }
        };

        // Mic button handler
        const micBtn = document.getElementById('mic-btn');
        if (micBtn) {
            micBtn.onclick = () => {
                if (state.isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            };
        }

        if (interviewToggle) {
            interviewToggle.checked = state.interviewMode;
            interviewToggle.onchange = () => {
                state.interviewMode = interviewToggle.checked;
                if (!state.interviewMode) {
                    state.lastInterviewSignals = null;
                    state.lastLivePatch = null;
                    state.lastCycleTrace = null;
                }
                updateInterviewProgress(null, false);
                updateInterviewAssistBar(state.lastCoverage);
                const hint = state.lang === 'ar'
                    ? 'وضع المقابلة: الأسئلة ستكون موجّهة لاستخراج المتطلبات.'
                    : 'Interview mode: guided questions to capture requirements.';
                showNotification(hint, 'info');
            };
        }

        const resumeBtn = document.getElementById('interview-resume-btn');
        const saveLaterBtn = document.getElementById('interview-save-later-btn');
        const reviewBtn = document.getElementById('interview-review-btn');

        const updateResumeButtonState = () => {
            if (!resumeBtn) return;
            const projectId = Number.parseInt(select.value || '0', 10);
            const localDraft = projectId ? loadInterviewDraftLocal(projectId) : null;
            resumeBtn.disabled = !(projectId && localDraft);
        };

        const restoreDraftForCurrentProject = async () => {
            const projectId = Number.parseInt(select.value || '0', 10);
            if (!projectId) {
                showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                return;
            }

            const draft = await loadInterviewDraft(projectId);
            if (!draft) {
                showNotification(state.lang === 'ar' ? 'لا يوجد حفظ سابق لهذه المقابلة.' : 'No saved interview found for this project.', 'warning');
                updateResumeButtonState();
                return;
            }

            state.previousSummary = draft.summary || null;
            state.lastCoverage = draft.coverage || null;
            state.lastInterviewSignals = draft.signals || null;
            state.lastLivePatch = draft.livePatch || null;
            state.lastCycleTrace = draft.cycleTrace || null;
            state.lastTopicNavigation = draft.topicNavigation || null;
            state.interviewStage = draft.stage || 'discovery';
            state.lastAssistantQuestion = draft.lastAssistantQuestion || '';
            state.interviewDraftMeta = draft;
            if (draft.mode) {
                state.interviewMode = true;
                if (interviewToggle) interviewToggle.checked = true;
            }

            updateInterviewProgress(state.lastCoverage, false);
            updateInterviewAssistBar(state.lastCoverage);
            showNotification(i18n[state.lang].interview_restored, 'success');
            updateResumeButtonState();
        };

        if (resumeBtn) {
            const label = resumeBtn.querySelector('span');
            const resumeText = i18n[state.lang].interview_resume;
            if (label) label.textContent = resumeText;
            resumeBtn.title = resumeText;
            resumeBtn.dataset.tooltip = resumeText;
            resumeBtn.onclick = restoreDraftForCurrentProject;
        }

        if (saveLaterBtn) {
            const label = saveLaterBtn.querySelector('span');
            const saveLaterText = i18n[state.lang].interview_save_later;
            if (label) label.textContent = saveLaterText;
            saveLaterBtn.title = saveLaterText;
            saveLaterBtn.dataset.tooltip = saveLaterText;
            saveLaterBtn.onclick = async () => {
                const projectId = Number.parseInt(select.value || '0', 10);
                if (!projectId) {
                    showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                    return;
                }
                await saveInterviewDraft(projectId);
                showNotification(i18n[state.lang].interview_saved, 'success');
                updateResumeButtonState();
            };
        }

        if (reviewBtn) {
            const label = reviewBtn.querySelector('span');
            const reviewText = i18n[state.lang].interview_review;
            if (label) label.textContent = reviewText;
            reviewBtn.title = reviewText;
            reviewBtn.dataset.tooltip = reviewText;
            reviewBtn.onclick = async () => {
                const projectId = Number.parseInt(select.value || '0', 10);
                if (!projectId) return;
                await openInterviewReviewModal(projectId, langSelect.value, {
                    summary: state.previousSummary || {},
                    stage: state.interviewStage || 'discovery',
                    coverage: state.lastCoverage || {},
                    done: false
                });
            };
        }

        // Init interview progress bar state
        updateChatProjectHeader(Number.parseInt(select.value || '0', 10) || null);
        applySummaryDrawerState();
        updateInterviewProgress(state.lastCoverage, false);
        updateInterviewAssistBar(state.lastCoverage);
        updateResumeButtonState();

        // Live doc close button
        const liveDocClose = document.getElementById('live-doc-close');
        if (liveDocClose) {
            liveDocClose.onclick = () => {
                state.summaryCollapsed = true;
                applySummaryDrawerState();
            };
        }

        if (summaryToggleBtn) {
            const summaryText = state.lang === 'ar' ? 'ملخص المتطلبات' : 'Requirements Summary';
            const summaryLabel = summaryToggleBtn.querySelector('span');
            if (summaryLabel) summaryLabel.textContent = summaryText;
            summaryToggleBtn.title = summaryText;
            summaryToggleBtn.dataset.tooltip = summaryText;
            summaryToggleBtn.onclick = () => {
                state.summaryCollapsed = !state.summaryCollapsed;
                applySummaryDrawerState();
            };
        }

        // Project Files drawer toggle
        const filesBtn = document.getElementById('chat-files-btn');
        const filesDrawer = document.getElementById('files-drawer');
        const filesDrawerClose = document.getElementById('files-drawer-close');

        const openFilesDrawer = async () => {
            const projectId = Number.parseInt(select.value || '0', 10);
            if (!projectId) {
                showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                return;
            }
            filesDrawer.style.display = '';
            setupUploadZone(projectId);
            try {
                const docs = await api.get(`/projects/${projectId}/documents`);
                renderDocsList(docs);
                startDocPolling(projectId, docs);
            } catch (e) {
                console.error('Files Drawer Load Error:', e);
            }
        };

        if (filesBtn) filesBtn.onclick = openFilesDrawer;
        if (filesDrawerClose) filesDrawerClose.onclick = () => { filesDrawer.style.display = 'none'; };

        // Clear chat handler
        if (clearBtn) {
            clearBtn.onclick = async () => {
                const messagesContainer = document.getElementById('chat-messages');
                const projectId = Number.parseInt(select.value || '0', 10);

                if (projectId) {
                    try {
                        await api.delete(`/projects/${projectId}/messages`);
                    } catch (error) {
                        console.error('Clear chat failed:', error);
                        showNotification(state.lang === 'ar' ? 'تعذر مسح المحادثة من السيرفر' : 'Failed to clear chat on server', 'error');
                        return;
                    }
                }

                messagesContainer.innerHTML = `
                    ${getChatWelcomeMarkup(projectId)}
                `;
                bindSuggestionChips();
                state.chatMessages = [];
                showNotification(state.lang === 'ar' ? 'تم مسح المحادثة' : 'Chat cleared', 'success');
            };
        }

        // Suggestion chips handler
        bindSuggestionChips();

        applyTranslations();
    },

    async srs() {
        renderTemplate('srs-template');
        showLoader();

        try {
            const projects = await api.get('/projects/');
            const select = document.getElementById('srs-project-select');
            const exportFormat = document.getElementById('srs-export-format');
            const refreshBtn = document.getElementById('srs-refresh-btn');
            const exportBtn = document.getElementById('srs-export-btn');
            const bookBtn = document.getElementById('srs-book-btn');

            if (exportFormat) {
                updateExportButtonLabel(exportFormat.value || 'pdf');
                exportFormat.onchange = () => updateExportButtonLabel(exportFormat.value || 'pdf');
            }

            projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                select.appendChild(opt);
            });

            // Support navigation from project cards (pending selection), then fallback to selected project
            if (state.pendingProjectSelect && select) {
                select.value = state.pendingProjectSelect;
                state.pendingProjectSelect = null;
            } else if (state.selectedProject && select) {
                select.value = state.selectedProject.id;
            }

            refreshBtn.onclick = async () => {
                if (!select.value) {
                    showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                    return;
                }
                setButtonLoading(refreshBtn, true);
                await loadSrsDraft(select.value, true);
                setButtonLoading(refreshBtn, false);
            };
            exportBtn.onclick = async () => {
                if (!select.value) {
                    showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                    return;
                }
                setButtonLoading(exportBtn, true);
                const selectedFormat = exportFormat?.value || 'pdf';
                await exportSrsDocument(select.value, selectedFormat);
                setButtonLoading(exportBtn, false);
            };
            bookBtn.onclick = () => openBookingModal();

            const confirmBtn = document.getElementById('srs-confirm-btn');
            if (confirmBtn) {
                confirmBtn.onclick = async () => {
                    if (!select.value) {
                        showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                        return;
                    }
                    setButtonLoading(confirmBtn, true);
                    try {
                        const clientName = state.currentUser ? state.currentUser.name : '';
                        const clientEmail = state.currentUser ? state.currentUser.email : '';
                        await api.post(`/projects/${select.value}/handoff`, {
                            client_name: clientName,
                            client_email: clientEmail,
                            notes: ''
                        });
                    } catch (error) {
                        console.error('Handoff error:', error);
                    }
                    setButtonLoading(confirmBtn, false);
                    showNotification(i18n[state.lang].srs_confirmed, 'success');
                    confirmBtn.disabled = true;
                    confirmBtn.innerHTML = `<i class="fas fa-check-double"></i> <span>${state.lang === 'ar' ? 'تم الاعتماد' : 'Approved'}</span>`;
                    confirmBtn.classList.remove('btn-primary');
                    confirmBtn.classList.add('btn-confirmed');
                };
            }

            exportBtn.disabled = !select.value;
            select.onchange = async () => {
                exportBtn.disabled = !select.value;
                if (select.value) {
                    await loadSrsDraft(select.value, false);
                } else {
                    renderSrsDraft(getFallbackSrsDraft());
                }
            };

            if (select.value) {
                await loadSrsDraft(select.value, false);
            } else {
                renderSrsDraft(getFallbackSrsDraft());
            }
            applyTranslations();
        } catch (error) {
            console.error('SRS View Error:', error);
        } finally {
            hideLoader();
        }
    },

    async settings() {
        renderTemplate('settings-template');
        showLoader();

        try {
            const [projects, botConfig, aiConfig] = await Promise.all([
                api.get('/projects/'),
                api.get('/bot/config'),
                api.get('/config/providers'),
            ]);

            const aiSelect = document.getElementById('settings-ai-gen-provider');
            const aiSaveBtn = document.getElementById('settings-save-ai-config-btn');

            const genProviders = aiConfig.available?.llm || [];
            const labelMap = {
                gemini: 'Gemini 2.5 Flash',
                'gemini-2.5-lite-flash': 'Gemini 2.5 Lite Flash',
                'openrouter-gemini-2.0-flash': 'OpenRouter: Gemini 2.0 Flash',
                'openrouter-free': 'OpenRouter: Free',
                'groq-llama-3.3-70b-versatile': 'Groq: Llama 3.3 70B',
                'cerebras-llama-3.3-70b': 'Cerebras: Llama 3.3 70B',
                'cerebras-llama-3.1-8b': 'Cerebras: Llama 3.1 8B',
                cohere: 'Cohere',
            };

            genProviders.forEach((name) => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.textContent = labelMap[name] || name;
                if (aiConfig.llm_provider === name) opt.selected = true;
                aiSelect.appendChild(opt);
            });

            if (aiSaveBtn) {
                aiSaveBtn.onclick = async () => {
                    setButtonLoading(aiSaveBtn, true);
                    try {
                        await api.post('/config/providers', { llm_provider: aiSelect.value });
                        showNotification(i18n[state.lang].success_saved, 'success');
                    } catch (e) {
                        console.error(e);
                    } finally {
                        setButtonLoading(aiSaveBtn, false);
                    }
                };
            }

            // --- Bot config ---
            const botSelect = document.getElementById('bot-active-project');
            projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                if (botConfig.active_project_id == p.id) opt.selected = true;
                botSelect.appendChild(opt);
            });

            document.getElementById('save-bot-config-btn').onclick = async () => {
                const projectId = botSelect.value;
                if (!projectId) return;
                const btn = document.getElementById('save-bot-config-btn');
                setButtonLoading(btn, true);
                try {
                    await api.post('/bot/config', { active_project_id: Number.parseInt(projectId, 10) });
                    showNotification(i18n[state.lang].success_saved, 'success');
                } catch (e) {
                    console.error(e);
                } finally {
                    setButtonLoading(btn, false);
                }
            };

            document.getElementById('update-bot-profile-btn').onclick = async () => {
                const name = document.getElementById('bot-name-input').value;
                if (!name) return;
                const btn = document.getElementById('update-bot-profile-btn');
                setButtonLoading(btn, true);
                const formData = new FormData();
                formData.append('name', name);
                try {
                    await api.post('/bot/profile', formData, true);
                    showNotification(i18n[state.lang].success_saved, 'success');
                } catch (e) {
                    console.error(e);
                } finally {
                    setButtonLoading(btn, false);
                }
            };

            applyTranslations();
        } catch (error) {
            console.error('Settings Error:', error);
        } finally {
            hideLoader();
        }
    }
};

// --- Helpers ---

function renderTemplate(templateId) {
    const template = document.getElementById(templateId);
    const clone = template.content.cloneNode(true);
    elements.viewContainer.innerHTML = '';
    elements.viewContainer.appendChild(clone);
    elements.viewContainer.classList.toggle('chat-mode', templateId === 'chat-template');
}

function applySidebarCollapsedState() {
    const appContainer = document.getElementById('app-container');
    if (!appContainer) return;

    const isCollapsed = safeStorageGet('sidebarCollapsed', '0') === '1';
    appContainer.classList.toggle('sidebar-collapsed', isCollapsed);
}

function toggleSidebarCollapsed() {
    const appContainer = document.getElementById('app-container');
    if (!appContainer) return;

    const next = !appContainer.classList.contains('sidebar-collapsed');
    appContainer.classList.toggle('sidebar-collapsed', next);
    safeStorageSet('sidebarCollapsed', next ? '1' : '0');
}

function showLoader() {
    const loader = document.createElement('div');
    loader.className = 'loader-container';
    loader.innerHTML = '<div class="loader"></div>';
    elements.viewContainer.appendChild(loader);
}

function hideLoader() {
    const loader = elements.viewContainer.querySelector('.loader-container');
    if (loader) loader.remove();
}

function interviewStorageKey(projectId) {
    return `interviewDraft:${projectId}`;
}

function buildInterviewDraftPayload() {
    return {
        summary: state.previousSummary,
        coverage: state.lastCoverage,
        signals: state.lastInterviewSignals,
        livePatch: state.lastLivePatch,
        cycleTrace: state.lastCycleTrace,
        topicNavigation: state.lastTopicNavigation,
        stage: state.interviewStage,
        mode: state.interviewMode,
        lastAssistantQuestion: state.lastAssistantQuestion,
        savedAt: new Date().toISOString(),
        lang: state.lang
    };
}

async function saveInterviewDraft(projectId) {
    if (!projectId) return;
    const payload = buildInterviewDraftPayload();
    safeStorageSet(interviewStorageKey(projectId), JSON.stringify(payload));
    state.interviewDraftMeta = payload;

    try {
        const response = await api.post(`/projects/${projectId}/interview/draft`, payload);
        if (response?.draft) {
            state.interviewDraftMeta = response.draft;
        }
    } catch (error) {
        console.warn('Failed to save interview draft on server, local draft kept.', error);
    }
}

function parseDraftDate(value) {
    if (!value) return 0;
    const ts = Date.parse(value);
    return Number.isNaN(ts) ? 0 : ts;
}

function pickLatestDraft(localDraft, serverDraft) {
    if (localDraft && !serverDraft) return localDraft;
    if (!localDraft && serverDraft) return serverDraft;
    if (!localDraft && !serverDraft) return null;

    const localTime = parseDraftDate(localDraft.savedAt);
    const serverTime = parseDraftDate(serverDraft.savedAt);
    return serverTime >= localTime ? serverDraft : localDraft;
}

function loadInterviewDraftLocal(projectId) {
    if (!projectId) return null;
    const raw = safeStorageGet(interviewStorageKey(projectId), null);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch (error) {
        console.warn('Invalid local interview draft JSON, ignoring.', error);
        return null;
    }
}

function getProjectProgressInfo(project) {
    const draft = loadInterviewDraftLocal(project.id);
    const coverage = draft?.coverage || null;
    const progress = coverage ? getAverageCoverage(coverage) : 0;
    const done = progress >= 85;
    if (!draft) {
        return {
            progress: 0,
            label: state.lang === 'ar' ? 'لم تبدأ المقابلة' : 'Interview not started'
        };
    }
    if (done) {
        return {
            progress: 100,
            label: state.lang === 'ar' ? 'SRS جاهز للمراجعة' : 'SRS ready for review'
        };
    }
    return {
        progress,
        label: state.lang === 'ar' ? `المقابلة قيد التقدم ${progress}%` : `Interview in progress ${progress}%`
    };
}

async function loadInterviewDraft(projectId) {
    if (!projectId) return null;

    const localDraft = loadInterviewDraftLocal(projectId);
    let serverDraft = null;

    try {
        const response = await api.get(`/projects/${projectId}/interview/draft`);
        serverDraft = response?.draft || null;
    } catch (error) {
        console.warn('Failed to load interview draft from server, using local fallback.', error);
    }

    const selected = pickLatestDraft(localDraft, serverDraft);
    if (selected) {
        safeStorageSet(interviewStorageKey(projectId), JSON.stringify(selected));
    }
    return selected;
}

async function clearInterviewDraft(projectId) {
    if (!projectId) return;
    safeStorageRemove(interviewStorageKey(projectId));
    try {
        await api.delete(`/projects/${projectId}/interview/draft`);
    } catch (error) {
        console.warn('Failed to clear interview draft on server.', error);
    }
}

function normalizeInterviewText(value) {
    return String(value || '')
        .trim()
        .toLowerCase()
    .replaceAll(/\s+/g, ' ')
    .replaceAll(/[?.!،؛:]+$/g, '');
}

function getAverageCoverage(coverage) {
    if (!coverage) return 0;
    const values = INTERVIEW_AREAS.map((area) => Number(coverage[area] || 0));
    const sum = values.reduce((acc, val) => acc + val, 0);
    return Math.round(sum / INTERVIEW_AREAS.length);
}

function parseSuggestedAnswers(rawSuggestions) {
    if (Array.isArray(rawSuggestions)) return rawSuggestions;

    if (typeof rawSuggestions === 'string') {
        const trimmed = rawSuggestions.trim();
        if (!trimmed) return [];

        const parsedList = parseSuggestedAnswersFromJson(trimmed);
        if (parsedList.length) return parsedList;

        return trimmed
            .split(/\n|•|-\s+/)
            .map((line) => line.trim())
            .filter(Boolean);
    }

    if (rawSuggestions && typeof rawSuggestions === 'object') {
        return getSuggestionArray(rawSuggestions);
    }

    return [];
}

function getSuggestionArray(value) {
    if (!value || typeof value !== 'object') return [];
    if (Array.isArray(value.suggested_answers)) return value.suggested_answers;
    if (Array.isArray(value.options)) return value.options;
    if (Array.isArray(value.answers)) return value.answers;
    return [];
}

function parseSuggestedAnswersFromJson(trimmed) {
    try {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed;
        return getSuggestionArray(parsed);
    } catch (error_) {
        console.warn('Failed to parse suggested answers payload.', error_);
        return [];
    }
}

function getQuestionAwareFallbackOptions(questionText = '', stage = 'discovery') {
    const q = normalizeInterviewText(questionText);
    const isAr = state.lang === 'ar';

    const byStage = {
        ar: {
            discovery: [
                'المشكلة الحالية أننا نعتمد على خطوات يدوية متعددة تؤخر التنفيذ وتزيد الأخطاء.',
                'الجمهور المتأثر الأساسي هو المستخدم النهائي وفريق التشغيل، ونحتاج تحسين التجربة والزمن.',
                'هدف النجاح هو تقليل زمن الإنجاز ورفع نسبة الإكمال الصحيح من أول مرة.'
            ],
            scope: [
                'في MVP نركز على العمليات الأساسية التي تعطي قيمة مباشرة للمستخدم.',
                'خارج النطاق حالياً أي تكاملات معقدة أو خصائص غير ضرورية للإطلاق الأول.',
                'المرحلة التالية تشمل تحسينات التوسع بعد التأكد من استقرار الإصدار الأول.'
            ],
            users: [
                'الأدوار الأساسية هي مستخدم نهائي، موظف تشغيل، ومشرف بصلاحيات أوسع.',
                'نحتاج صلاحيات واضحة لكل دور لضمان التحكم والأمان وعدم تضارب المهام.',
                'رحلة المستخدم الأساسية يجب أن تكون قصيرة وواضحة من البداية حتى إتمام الطلب.'
            ],
            features: [
                'الميزة الأساسية المطلوبة هي إدارة دورة الطلب كاملة مع تتبع واضح للحالة.',
                'معيار القبول أن تنفذ العملية بدون تعقيد وبزمن استجابة مناسب للمستخدم.',
                'في الحالات الاستثنائية نحتاج إعادة محاولة تلقائية وتسجيل كامل للأخطاء.'
            ],
            constraints: [
                'القيود الرئيسية عندنا هي الزمن، الميزانية، والالتزام بمعايير الأمان.',
                'نحتاج حل متوافق مع البنية الحالية بدون تعطيل التشغيل القائم.',
                'من المهم الالتزام بمتطلبات الامتثال وتوثيق كل العمليات الحساسة.'
            ]
        },
        en: {
            discovery: [
                'The current workflow relies on multiple manual steps that slow delivery and increase errors.',
                'Primary impacted groups are end users and operations staff, so speed and usability must improve.',
                'Success target is faster turnaround and higher first-pass completion quality.'
            ],
            scope: [
                'For MVP, we should prioritize core high-value flows needed for initial launch.',
                'Out of scope for now are complex integrations and non-essential enhancements.',
                'Phase two can include scalability and advanced capabilities after stability is proven.'
            ],
            users: [
                'Key roles are end user, operations agent, and supervisor with broader permissions.',
                'Role-based permissions are required to control access and reduce operational risk.',
                'The primary user journey should be short, clear, and easy to complete end to end.'
            ],
            features: [
                'The core feature is full workflow lifecycle management with clear status tracking.',
                'Acceptance criteria should confirm smooth flow completion with practical response-time targets.',
                'For edge cases, we need retries and reliable failure logging without data loss.'
            ],
            constraints: [
                'Main constraints are timeline, budget, and mandatory security controls.',
                'The solution should integrate with existing systems without disrupting current operations.',
                'Compliance requirements must be enforced with traceability for sensitive actions.'
            ]
        }
    };

    const intentFallback = isAr
        ? [
            { keys: ['مقياس', 'نجاح', 'kpi', 'مؤشر'], choices: [
                'مؤشر النجاح الرئيسي: تقليل زمن التنفيذ ورفع دقة الإنجاز ضمن فترة زمنية محددة.',
                'سنقيس النجاح عبر KPI أسبوعي واضح: زمن الدورة، نسبة الأخطاء، والالتزام بالـSLA.',
                'الهدف الكمي المقترح: خفض زمن المعالجة ورفع جودة التنفيذ بصورة قابلة للقياس.'
            ] },
            { keys: ['قبول', 'معيار', 'acceptance'], choices: [
                'معيار القبول: تنفيذ السيناريو الأساسي كاملًا بدون تدخل يدوي غير مخطط.',
                'يُقبل السيناريو إذا أنهى المستخدم المهمة بعدد خطوات محدود وبنسبة أخطاء منخفضة.',
                'المعيار يشمل صحة البيانات، زمن الاستجابة، وتتبع الأحداث في سجل التدقيق.'
            ] }
        ]
        : [
            { keys: ['metric', 'success', 'kpi'], choices: [
                'Primary success metric is measurable cycle-time reduction with improved completion quality.',
                'We should track weekly KPIs: cycle time, error rate, and SLA adherence.',
                'A strong target is quantifiable speed and quality improvement within a defined period.'
            ] },
            { keys: ['acceptance', 'criteria'], choices: [
                'Acceptance criteria should validate full end-to-end completion without unplanned manual workarounds.',
                'A flow is accepted when users complete it in limited steps with low error rate.',
                'Criteria must include data correctness, response targets, and audit traceability.'
            ] }
        ];

    const matchedIntent = intentFallback.find((entry) => entry.keys.some((key) => q.includes(normalizeInterviewText(key))));
    if (matchedIntent) return matchedIntent.choices;

    return (byStage[isAr ? 'ar' : 'en'][stage] || byStage[isAr ? 'ar' : 'en'].discovery);
}

function getInterviewAnswerOptions(suggestedAnswers = [], questionText = '', stage = 'discovery') {
    const questionTokens = normalizeInterviewText(questionText)
        .split(' ')
        .map((token) => token.trim())
        .filter((token) => token.length >= 3)
        .filter((token) => !['what', 'which', 'when', 'where', 'كيف', 'ايه', 'ما', 'هو', 'هي', 'على', 'في', 'من'].includes(token));

    const isRelevantOption = (optionText) => {
        if (!questionTokens.length) return true;
        const normalized = normalizeInterviewText(optionText);
        if (!normalized) return false;
        const overlap = questionTokens.filter((token) => normalized.includes(token)).length;
        return overlap >= 1;
    };

    const parsed = parseSuggestedAnswers(suggestedAnswers);
    const cleaned = parsed
        .map((item) => String(item || '').trim())
        .filter(Boolean);

    const unique = [];
    const seen = new Set();
    cleaned.forEach((item) => {
        const key = normalizeInterviewText(item);
        if (!key || seen.has(key)) return;
        seen.add(key);
        unique.push(item);
    });

    const relevant = unique.filter(isRelevantOption);

    const coreChoices = relevant.length >= 2
        ? relevant.slice(0, 2)
        : getQuestionAwareFallbackOptions(questionText, stage).slice(0, 2);

    return [
        ...coreChoices,
        i18n[state.lang].interview_option_skip,
        i18n[state.lang].interview_option_unsure
    ];
}

function attachInterviewSelectToMessage(messageId, suggestedAnswers = [], questionText = '', stage = 'discovery') {
    if (!state.interviewMode) return;
    const msgDiv = document.getElementById(`msg-${messageId}`);
    if (!msgDiv) return;

    // Disable all previous selection wrappers
    document.querySelectorAll('.interview-answer-select-wrap').forEach((node) => {
        node.querySelectorAll('.suggestion-card').forEach(card => card.classList.add('disabled'));
        const btnEl = node.querySelector('button');
        if (btnEl) btnEl.disabled = true;
    });

    const options = getInterviewAnswerOptions(suggestedAnswers, questionText, stage);
    const wrapper = document.createElement('div');
    wrapper.className = 'interview-answer-select-wrap';

    // Build card chips
    const cardsHtml = options.map((opt, idx) => `
        <div class="suggestion-card" data-idx="${idx}" data-value="${escapeHtml(opt)}" role="radio" aria-checked="false" tabindex="0">
            <span class="suggestion-card-radio"></span>
            <span class="suggestion-card-text">${escapeHtml(opt)}</span>
        </div>
    `).join('');

    wrapper.innerHTML = `
        <div class="suggestion-cards-list" role="radiogroup" aria-label="${escapeHtml(i18n[state.lang].interview_select_hint)}">
            ${cardsHtml}
        </div>
        <button class="btn btn-secondary interview-mini-btn" disabled>${escapeHtml(i18n[state.lang].interview_select_send)}</button>
    `;

    const sendBtn = wrapper.querySelector('button');
    let selectedValue = null;

    wrapper.querySelectorAll('.suggestion-card').forEach(card => {
        const activate = () => {
            wrapper.querySelectorAll('.suggestion-card').forEach(c => {
                c.classList.remove('selected');
                c.setAttribute('aria-checked', 'false');
            });
            card.classList.add('selected');
            card.setAttribute('aria-checked', 'true');
            selectedValue = card.dataset.value;
            if (sendBtn) sendBtn.disabled = false;
        };
        card.onclick = activate;
        card.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') activate(); };
    });

    if (sendBtn) {
        sendBtn.onclick = () => {
            if (!selectedValue) return;
            const input = document.getElementById('chat-input');
            if (!input) return;
            state.pendingInterviewSelectionMeta = {
                interview_selection: true,
                source: 'suggested_answer',
                stage,
                question: questionText || ''
            };
            input.value = selectedValue;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            handleChatSubmit();
            wrapper.querySelectorAll('.suggestion-card').forEach(c => c.classList.add('disabled'));
            sendBtn.disabled = true;
        };
    }

    msgDiv.querySelector('.msg-body')?.appendChild(wrapper);

    // Scroll chat to show the newly appended cards
    const container = document.getElementById('chat-messages');
    if (container) {
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }
}

function updateInterviewAssistBar(coverage) {
    const assistBar = document.getElementById('interview-assist-bar');
    const reviewBtn = document.getElementById('interview-review-btn');
    if (!reviewBtn) return;

    if (!state.interviewMode) {
        if (assistBar) assistBar.style.display = 'none';
        return;
    }

    const avg = getAverageCoverage(coverage || state.lastCoverage || {});
    if (assistBar) assistBar.style.display = 'none';

    reviewBtn.disabled = avg < 60;
}

async function refreshInterviewTelemetry(projectId) {
    try {
        const telemetry = await api.get(`/projects/${projectId}/interview/telemetry`);
        if (!telemetry || typeof telemetry !== 'object') {
            state.lastInterviewTelemetry = null;
            return;
        }
        state.lastInterviewTelemetry = telemetry;
    } catch (error) {
        state.lastInterviewTelemetry = null;
        console.error('Interview Telemetry Refresh Error:', error);
    }
}

// --- Button Loading State ---
function setButtonLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
        btn.dataset.originalHtml = btn.innerHTML;
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
        if (btn.dataset.originalHtml) {
            btn.innerHTML = btn.dataset.originalHtml;
            delete btn.dataset.originalHtml;
        }
    }
}

// --- Custom Confirm Dialog ---
function showConfirmDialog(message) {
    return new Promise((resolve) => {
        const overlay = document.getElementById('confirm-overlay');
        const msgEl = document.getElementById('confirm-message');
        const okBtn = document.getElementById('confirm-ok-btn');
        const cancelBtn = document.getElementById('confirm-cancel-btn');

        msgEl.textContent = message;
        okBtn.textContent = i18n[state.lang].confirm_yes;
        cancelBtn.textContent = i18n[state.lang].confirm_cancel;

        overlay.classList.remove('hidden');

        function cleanup() {
            overlay.classList.add('hidden');
            okBtn.onclick = null;
            cancelBtn.onclick = null;
            overlay.onclick = null;
            document.removeEventListener('keydown', handleEsc);
        }

        function handleEsc(e) {
            if (e.key === 'Escape') { cleanup(); resolve(false); }
        }

        okBtn.onclick = () => { cleanup(); resolve(true); };
        cancelBtn.onclick = () => { cleanup(); resolve(false); };
        overlay.onclick = (e) => {
            if (e.target === overlay) { cleanup(); resolve(false); }
        };
        document.addEventListener('keydown', handleEsc);
        cancelBtn.focus();
    });
}

// --- Form Validation ---
function showFieldError(input, message) {
    const group = input.closest('.form-group');
    if (!group) return;
    group.classList.add('has-error');
    let errorEl = group.querySelector('.field-error');
    if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.className = 'field-error';
        group.appendChild(errorEl);
    }
    errorEl.textContent = message;
}

function clearFieldError(input) {
    const group = input.closest('.form-group');
    if (!group) return;
    group.classList.remove('has-error');
    const errorEl = group.querySelector('.field-error');
    if (errorEl) errorEl.textContent = '';
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function setupFieldValidation(input, validateFn) {
    input.addEventListener('blur', () => {
        const error = validateFn(input.value);
        if (error) showFieldError(input, error);
    });
    input.addEventListener('input', () => clearFieldError(input));
}

// --- Rate Limiter ---
const rateLimiter = {
    attempts: [],
    lockedUntil: null,
    maxAttempts: 5,
    windowMs: 60000,
    lockoutMs: 30000,

    recordFailure() {
        const now = Date.now();
        this.attempts.push(now);
        this.attempts = this.attempts.filter(t => now - t < this.windowMs);
        if (this.attempts.length >= this.maxAttempts) {
            this.lockedUntil = now + this.lockoutMs;
            this.attempts = [];
        }
    },

    reset() {
        this.attempts = [];
        this.lockedUntil = null;
    },

    isLocked() {
        if (!this.lockedUntil) return false;
        if (Date.now() > this.lockedUntil) {
            this.lockedUntil = null;
            return false;
        }
        return true;
    },

    getRemainingSeconds() {
        if (!this.lockedUntil) return 0;
        return Math.ceil((this.lockedUntil - Date.now()) / 1000);
    }
};

function startLockoutCountdown(errorEl) {
    const interval = setInterval(() => {
        if (!rateLimiter.isLocked()) {
            clearInterval(interval);
            errorEl.style.display = 'none';
            return;
        }
        const secs = rateLimiter.getRemainingSeconds();
        errorEl.textContent = i18n[state.lang].rate_limit_msg.replace('{seconds}', secs);
        errorEl.style.display = 'block';
    }, 1000);
}

// --- SRS Progress Stepper (3.1) ---

function showSrsProgress(currentStep) {
    const sectionsEl = document.getElementById('srs-sections');
    if (!sectionsEl) return;

    const isAr = state.lang === 'ar';
    const steps = isAr
        ? ['تحليل نص المقابلة', 'هيكلة المتطلبات', 'مراجعة تقنية', 'مراجعة الأعمال', 'تنقيح وإتمام الوثيقة']
        : ['Analyzing interview transcript', 'Structuring requirements', 'Technical review', 'Business review', 'Refining & finalizing'];

    const stepIcons = steps.map((label, idx) => {
        if (idx < currentStep) return `<span class="srs-step done"><i class="fas fa-check-circle"></i> ${label}</span>`;
        if (idx === currentStep) return `<span class="srs-step active"><i class="fas fa-spinner fa-spin"></i> ${label}</span>`;
        return `<span class="srs-step pending"><i class="far fa-circle"></i> ${label}</span>`;
    }).join('');

    sectionsEl.innerHTML = `
        <div class="srs-progress-stepper">
            <p class="srs-progress-title">${isAr ? 'جارٍ إنشاء مستند المتطلبات...' : 'Generating your SRS...'}</p>
            <div class="srs-steps">${stepIcons}</div>
        </div>
    `;
}

function hideSrsProgress() {
    // Stepper will be overwritten naturally by renderSrsDraft or guidance banner
}

// --- SRS Quality-Gate Guidance Banner (3.3) ---

function showSrsGuidanceBanner(message) {
    const sectionsEl = document.getElementById('srs-sections');
    if (!sectionsEl) return;
    const isAr = state.lang === 'ar';
    sectionsEl.innerHTML = `
        <div class="srs-guidance-banner">
            <div class="srs-guidance-icon"><i class="fas fa-triangle-exclamation"></i></div>
            <div class="srs-guidance-body">
                <strong>${isAr ? 'محتوى غير كافٍ بعد' : 'Not enough content yet'}</strong>
                <p>${message}</p>
            </div>
            <div class="srs-guidance-actions">
                <button class="btn btn-primary btn-sm" id="srs-go-interview-btn">
                    ${isAr ? 'الذهاب إلى المقابلة' : 'Go to Interview'}
                    <i class="fas fa-arrow-left" style="margin-${isAr ? 'right' : 'left'}:6px"></i>
                </button>
                <button class="btn btn-sm srs-guidance-dismiss" id="srs-guidance-dismiss-btn">${isAr ? 'تجاهل' : 'Dismiss'}</button>
            </div>
        </div>
    `;
    const goBtn = document.getElementById('srs-go-interview-btn');
    if (goBtn) goBtn.onclick = () => switchView('chat');
    const dismissBtn = document.getElementById('srs-guidance-dismiss-btn');
    if (dismissBtn) dismissBtn.onclick = () => { sectionsEl.innerHTML = ''; };
}

async function loadSrsDraft(projectId, forceRefresh = false) {
    if (state.srsRefreshing) return;
    state.srsRefreshing = true;

    let progressTimers = [];

    try {
        let draft = await tryLoadExistingSrs(projectId, forceRefresh);
        if (!draft) {
            draft = await generateSrsDraftWithProgress(projectId);
        }

        renderSrsDraft(draft.content, draft);
    } catch (error) {
        clearSrsProgressTimers(progressTimers);
        progressTimers = [];
        console.error('SRS Load Error:', error);
        handleSrsLoadError(error);
    } finally {
        state.srsRefreshing = false;
    }
}

async function tryLoadExistingSrs(projectId, forceRefresh) {
    if (forceRefresh) return null;
    try {
        return await api.get(`/projects/${projectId}/srs`);
    } catch (error) {
        if (error.status !== 404) throw error;
        return null;
    }
}

async function generateSrsDraftWithProgress(projectId) {
    showSrsProgress(0);
    const progressTimers = scheduleSrsProgressTimers();
    try {
        return await api.post(`/projects/${projectId}/srs/refresh`, {
            language: state.lang
        });
    } finally {
        clearSrsProgressTimers(progressTimers);
        hideSrsProgress();
    }
}

function handleSrsLoadError(error) {
    const errMsg = error?.message || '';
    hideSrsProgress();

    if (isSrsInsufficientContentError(errMsg)) {
        showSrsGuidanceBanner(
            state.lang === 'ar'
                ? 'المقابلة تحتاج مزيداً من التفاصيل. أكمل 3–5 محادثات إضافية ثم حاول مرة أخرى.'
                : 'The interview needs more detail. Complete 3–5 more turns, then try again.'
        );
        return;
    }

    renderSrsDraft(getFallbackSrsDraft(), null);
    showNotification(state.lang === 'ar' ? 'تعذر تحميل المسودة' : 'Failed to load draft', 'error');
}

function scheduleSrsProgressTimers() {
    const timers = [];
    const stepDelays = [0, 3000, 8000, 14000, 20000];
    stepDelays.forEach((delay, step) => {
        const timerId = setTimeout(() => showSrsProgress(step), delay);
        timers.push(timerId);
    });
    return timers;
}

function clearSrsProgressTimers(timers) {
    timers.forEach(timerId => clearTimeout(timerId));
}

function isSrsInsufficientContentError(message) {
    const errMsg = String(message || '');
    return errMsg.toLowerCase().includes('insufficient content')
        || errMsg.includes('minimum of 80 words')
        || errMsg.includes('80 كلمة');
}

function renderSrsDraft(content, draftMeta) {
    const draft = content || getFallbackSrsDraft();
    state.lastRenderedSrsDraft = { content: draft, meta: draftMeta || null };
    const statusEl = document.getElementById('srs-status');
    const updatedEl = document.getElementById('srs-updated');
    const summaryEl = document.getElementById('srs-summary-text');
    const metricsEl = document.getElementById('srs-metrics');
    const sectionsEl = document.getElementById('srs-sections');
    const questionsEl = document.getElementById('srs-open-questions');
    const nextStepsEl = document.getElementById('srs-next-steps');

    if (statusEl) statusEl.textContent = draft.status || (state.lang === 'ar' ? 'مسودة أولية' : 'First Draft');
    if (updatedEl) {
        const fallbackTime = state.lang === 'ar' ? 'آخر تحديث: الآن' : 'Last updated: now';
        const updatedPrefix = state.lang === 'ar' ? 'آخر تحديث:' : 'Last updated:';
        updatedEl.textContent = draftMeta?.created_at
            ? `${updatedPrefix} ${new Date(draftMeta.created_at).toLocaleString()}`
            : draft.updated || fallbackTime;
    }
    if (summaryEl) {
        summaryEl.textContent = draft.summary;
        summaryEl.setAttribute('dir', 'auto');
    }

    if (metricsEl) {
        metricsEl.innerHTML = (draft.metrics || [])
            .map(item => `
                <div class="metric-chip">
                    <span class="metric-label">${escapeHtml(item.label)}</span>
                    <span class="metric-value">${escapeHtml(item.value)}</span>
                </div>
            `)
            .join('');
    }

    if (sectionsEl) {
        const sections = draft.sections || [];
        const activityDiagram = Array.isArray(draft.activity_diagram) ? draft.activity_diagram : [];
        const activityMermaid = typeof draft.activity_diagram_mermaid === 'string'
            ? draft.activity_diagram_mermaid.trim()
            : '';
        const activityDiagrams = Array.isArray(draft.activity_diagrams) ? draft.activity_diagrams : [];
        const activityTitle = state.lang === 'ar' ? 'مخطط النشاط' : 'Activity Diagram';
        const textFlowLabel = state.lang === 'ar' ? 'عرض المسار النصي' : 'Show text flow';
        const emptyDraftTitle = state.lang === 'ar' ? 'لا توجد مسودة بعد' : 'No draft yet';
        const emptyDraftDesc = state.lang === 'ar'
            ? 'أجرِ مقابلة مع محلل الأعمال الذكي ثم اضغط تحديث.'
            : 'Your SRS will appear here. Start an interview to generate it.';
        const startInterviewLabel = state.lang === 'ar' ? 'بدء المقابلة ←' : 'Start Interview →';

        const activityDiagramHtml = activityDiagram.length
            ? `
                <article class="srs-section srs-activity-diagram">
                    <div class="srs-section-header">
                        <h3>${activityTitle}</h3>
                    </div>
                    <ul class="activity-diagram-list">
                        ${activityDiagram
                            .map((line) => `<li dir="auto">${escapeHtml(String(line).replaceAll(/\s*->\s*/g, ' → '))}</li>`)
                            .join('')}
                    </ul>
                </article>
            `
            : '';

        const fallbackDiagramHtml = activityDiagram.length
            ? `
                        <details class="srs-mermaid-fallback">
                            <summary>${textFlowLabel}</summary>
                            <ul class="activity-diagram-list">
                                ${activityDiagram
                                    .map((line) => `<li dir="auto">${escapeHtml(String(line).replaceAll(/\s*->\s*/g, ' → '))}</li>`)
                                    .join('')}
                            </ul>
                        </details>
                    `
            : '';

        const activityMermaidHtml = activityMermaid
            ? `
                <article class="srs-section srs-activity-diagram">
                    <div class="srs-section-header">
                        <h3>${activityTitle} (Mermaid)</h3>
                    </div>
                    <div class="srs-mermaid-surface" id="srs-mermaid-surface"></div>
                    ${fallbackDiagramHtml}
                </article>
            `
            : '';

        const multiActivityHtml = activityDiagrams
            .map((diagram, idx) => createActivityDiagramArticle(diagram, idx, activityTitle, textFlowLabel))
            .filter(Boolean)
            .join('');
        const hasMultiActivity = multiActivityHtml.length > 0;
        const activityHeaderHtml = hasMultiActivity ? multiActivityHtml : (activityMermaidHtml || activityDiagramHtml);
        const sectionsHtml = sections
            .map((section, idx) => `
                <article class="srs-section" data-confidence="${escapeHtml(section.confidence)}" data-idx="${idx}">
                    <div class="srs-section-header">
                        <h3>${escapeHtml(section.title)}</h3>
                        <div class="srs-section-actions">
                            <span class="confidence-badge">${escapeHtml(section.confidence)}</span>
                            <button class="srs-edit-btn" data-idx="${idx}" title="${state.lang === 'ar' ? 'تعديل' : 'Edit'}">
                                <i class="fas fa-pen"></i>
                            </button>
                        </div>
                    </div>
                    <ul>
                        ${section.items.map((item, iIdx) => `<li data-section="${idx}" data-item="${iIdx}" dir="auto">${escapeHtml(item)}</li>`).join('')}
                    </ul>
                </article>
            `)
            .join('');

        sectionsEl.innerHTML = sections.length
            ? `${activityHeaderHtml}${sectionsHtml}`
            : `<div class="empty-state">
                    <div class="empty-state-icon"><i class="fas fa-file-circle-xmark"></i></div>
                    <h3>${emptyDraftTitle}</h3>
                    <p>${emptyDraftDesc}</p>
                    <button class="btn btn-primary mt-4" onclick="switchView('chat')">
                        <i class="fas fa-comments"></i>
                        <span>${startInterviewLabel}</span>
                    </button>
                </div>`;

        // Attach inline edit handlers
        attachSrsEditHandlers(sectionsEl);

        if (hasMultiActivity) {
            renderAllSrsMermaid(activityDiagrams);
        } else if (activityMermaidHtml) {
            renderSrsMermaid(activityMermaid);
        }
    }

    // --- User Stories ---
    const userStories = Array.isArray(draft.user_stories) ? draft.user_stories : [];
    let userStoriesContainer = document.getElementById('srs-user-stories');
    if (!userStoriesContainer && sectionsEl) {
        userStoriesContainer = document.createElement('div');
        userStoriesContainer.id = 'srs-user-stories';
        sectionsEl.parentNode.insertBefore(userStoriesContainer, sectionsEl.nextSibling);
    }
    if (userStoriesContainer) {
        if (userStories.length) {
            const storiesTitle = state.lang === 'ar' ? 'قصص المستخدمين ومعايير القبول' : 'User Stories & Acceptance Criteria';
            const asLabel = state.lang === 'ar' ? 'بوصفي' : 'As a';
            const wantLabel = state.lang === 'ar' ? 'أريد' : 'I want to';
            const soLabel = state.lang === 'ar' ? 'حتى أتمكن من' : 'so that';
            const acLabel = state.lang === 'ar' ? 'معايير القبول' : 'Acceptance Criteria';
            userStoriesContainer.innerHTML = `
                <article class="srs-section srs-user-stories">
                    <div class="srs-section-header"><h3>${storiesTitle}</h3></div>
                    ${userStories.map((s, i) => `
                        <div class="user-story-card">
                            <div class="user-story-statement" dir="auto">
                                <strong>${asLabel}</strong> ${escapeHtml(s.role || '')},
                                <strong>${wantLabel}</strong> ${escapeHtml(s.action || '')},
                                <strong>${soLabel}</strong> ${escapeHtml(s.goal || '')}
                            </div>
                            ${Array.isArray(s.acceptance_criteria) && s.acceptance_criteria.length ? `
                            <details class="acceptance-criteria">
                                <summary>${acLabel} (${s.acceptance_criteria.length})</summary>
                                <ul>${s.acceptance_criteria.map(ac => `<li dir="auto">✓ ${escapeHtml(ac)}</li>`).join('')}</ul>
                            </details>` : ''}
                        </div>
                    `).join('')}
                </article>`;
        } else {
            userStoriesContainer.innerHTML = '';
        }
    }

    // --- User Roles ---
    const userRoles = Array.isArray(draft.user_roles) ? draft.user_roles : [];
    let userRolesContainer = document.getElementById('srs-user-roles');
    if (!userRolesContainer && sectionsEl) {
        userRolesContainer = document.createElement('div');
        userRolesContainer.id = 'srs-user-roles';
        if (userStoriesContainer) {
            sectionsEl.parentNode.insertBefore(userRolesContainer, userStoriesContainer.nextSibling);
        } else {
            sectionsEl.parentNode.insertBefore(userRolesContainer, sectionsEl.nextSibling);
        }
    }
    if (userRolesContainer) {
        if (userRoles.length) {
            const rolesTitle = state.lang === 'ar' ? 'أدوار المستخدمين' : 'User Roles';
            const permLabel = state.lang === 'ar' ? 'الصلاحيات' : 'Permissions';
            userRolesContainer.innerHTML = `
                <article class="srs-section srs-user-roles">
                    <div class="srs-section-header"><h3>${rolesTitle}</h3></div>
                    <table class="user-roles-table">
                        <thead><tr>
                            <th>${state.lang === 'ar' ? 'الدور' : 'Role'}</th>
                            <th>${state.lang === 'ar' ? 'الوصف' : 'Description'}</th>
                            <th>${permLabel}</th>
                        </tr></thead>
                        <tbody>
                            ${userRoles.map(r => `<tr>
                                <td dir="auto"><strong>${escapeHtml(r.role || '')}</strong></td>
                                <td dir="auto">${escapeHtml(r.description || '')}</td>
                                <td dir="auto">${Array.isArray(r.permissions) ? r.permissions.map(p => `<span class="perm-tag">${escapeHtml(p)}</span>`).join(' ') : ''}</td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </article>`;
        } else {
            userRolesContainer.innerHTML = '';
        }
    }

    if (questionsEl) {
        questionsEl.innerHTML = (draft.questions || [])
            .map(item => `<li>${escapeHtml(item)}</li>`)
            .join('');
    }

    if (nextStepsEl) {
        nextStepsEl.innerHTML = (draft.nextSteps || draft.next_steps || [])
            .map(item => `<li>${escapeHtml(item)}</li>`)
            .join('');
    }
}

async function renderSrsMermaid(code) {
    const surface = document.getElementById('srs-mermaid-surface');
    if (!surface) return;

    const mermaidApi = globalThis.mermaid;
    if (!mermaidApi || typeof mermaidApi.render !== 'function') {
        surface.innerHTML = `<div class="srs-mermaid-error">${state.lang === 'ar' ? 'تعذر تحميل مكتبة Mermaid.' : 'Failed to load Mermaid library.'}</div>`;
        return;
    }

    try {
        if (!globalThis.__tawasulMermaidInitialized) {
            mermaidApi.initialize({ startOnLoad: false, securityLevel: 'loose' });
            globalThis.__tawasulMermaidInitialized = true;
        }

        const graphId = `srs-mermaid-${Date.now()}`;
        const result = await mermaidApi.render(graphId, code);
        surface.innerHTML = result.svg || '';
    } catch (error) {
        console.error('Mermaid render error:', error);
        surface.innerHTML = `<div class="srs-mermaid-error">${state.lang === 'ar' ? 'فشل رسم مخطط Mermaid. سيتم عرض النسخة النصية.' : 'Failed to render Mermaid diagram. Text flow is shown instead.'}</div>`;
    }
}

function createActivityDiagramArticle(diagram, idx, activityTitle, textFlowLabel) {
    if (!diagram || typeof diagram !== 'object') return '';
    const title = String(diagram.title || `${activityTitle} ${idx + 1}`).trim();
    const lines = Array.isArray(diagram.activity_diagram)
        ? diagram.activity_diagram.map((line) => String(line).trim()).filter(Boolean)
        : [];
    const mermaid = typeof diagram.activity_diagram_mermaid === 'string'
        ? diagram.activity_diagram_mermaid.trim()
        : '';

    if (!lines.length && !mermaid) return '';

    const fallbackHtml = lines.length
        ? `
            <details class="srs-mermaid-fallback">
                <summary>${textFlowLabel}</summary>
                <ul class="activity-diagram-list">
                    ${lines.map((line) => `<li dir="auto">${escapeHtml(String(line).replaceAll(/\s*->\s*/g, ' → '))}</li>`).join('')}
                </ul>
            </details>
        `
        : '';

    if (mermaid) {
        return `
            <article class="srs-section srs-activity-diagram">
                <div class="srs-section-header">
                    <h3>${escapeHtml(title)} (Mermaid)</h3>
                </div>
                <div class="srs-mermaid-surface" id="srs-mermaid-surface-${idx}"></div>
                ${fallbackHtml}
            </article>
        `;
    }

    return `
        <article class="srs-section srs-activity-diagram">
            <div class="srs-section-header">
                <h3>${escapeHtml(title)}</h3>
            </div>
            <ul class="activity-diagram-list">
                ${lines.map((line) => `<li dir="auto">${escapeHtml(String(line).replaceAll(/\s*->\s*/g, ' → '))}</li>`).join('')}
            </ul>
        </article>
    `;
}

async function renderAllSrsMermaid(activityDiagrams) {
    if (!Array.isArray(activityDiagrams) || activityDiagrams.length === 0) return;

    const mermaidApi = globalThis.mermaid;
    if (!mermaidApi || typeof mermaidApi.render !== 'function') {
        document.querySelectorAll('[id^="srs-mermaid-surface-"]').forEach((surface) => {
            surface.innerHTML = `<div class="srs-mermaid-error">${state.lang === 'ar' ? 'تعذر تحميل مكتبة Mermaid.' : 'Failed to load Mermaid library.'}</div>`;
        });
        return;
    }

    try {
        if (!globalThis.__tawasulMermaidInitialized) {
            mermaidApi.initialize({ startOnLoad: false, securityLevel: 'loose' });
            globalThis.__tawasulMermaidInitialized = true;
        }
    } catch (error) {
        console.error('Mermaid init error:', error);
    }

    for (let idx = 0; idx < activityDiagrams.length; idx += 1) {
        await renderSingleSrsMermaidByIndex(mermaidApi, activityDiagrams[idx], idx);
    }
}

async function renderSingleSrsMermaidByIndex(mermaidApi, diagram, idx) {
    const code = typeof diagram?.activity_diagram_mermaid === 'string' ? diagram.activity_diagram_mermaid.trim() : '';
    if (!code) return;

    const surface = document.getElementById(`srs-mermaid-surface-${idx}`);
    if (!surface) return;

    try {
        const graphId = `srs-mermaid-${Date.now()}-${idx}`;
        const result = await mermaidApi.render(graphId, code);
        surface.innerHTML = result.svg || '';
    } catch (error) {
        console.error('Mermaid render error:', error);
        surface.innerHTML = `<div class="srs-mermaid-error">${state.lang === 'ar' ? 'فشل رسم مخطط Mermaid. سيتم عرض النسخة النصية.' : 'Failed to render Mermaid diagram. Text flow is shown instead.'}</div>`;
    }
}

function attachSrsEditHandlers(sectionsEl) {
    sectionsEl.querySelectorAll('.srs-edit-btn').forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            const sectionIdx = Number.parseInt(btn.dataset.idx, 10);
            const article = sectionsEl.querySelector(`[data-idx="${sectionIdx}"]`);
            if (!article) return;
            const ul = article.querySelector('ul');
            if (!ul || ul.classList.contains('editing')) return;

            ul.classList.add('editing');
            const items = ul.querySelectorAll('li');
            for (const li of items) {
                li.contentEditable = 'true';
                li.classList.add('editable');
            }

            // Change button to save
            btn.innerHTML = `<i class="fas fa-check"></i>`;
            btn.title = state.lang === 'ar' ? 'حفظ' : 'Save';
            btn.classList.add('saving');

            btn.onclick = () => {
                for (const li of items) {
                    li.contentEditable = 'false';
                    li.classList.remove('editable');
                }
                ul.classList.remove('editing');
                btn.innerHTML = `<i class="fas fa-pen"></i>`;
                btn.title = state.lang === 'ar' ? 'تعديل' : 'Edit';
                btn.classList.remove('saving');
                showNotification(state.lang === 'ar' ? 'تم حفظ التعديلات محلياً' : 'Changes saved locally', 'success');

                // Re-attach the edit handler properly (no recursive btn.click)
                attachSrsEditHandlers(sectionsEl);
            };
        };
    });
}

function updateExportButtonLabel(format = 'pdf') {
    const exportLabel = document.querySelector('#srs-export-btn span');
    if (!exportLabel) return;
    if (format === 'word') {
        exportLabel.textContent = i18n[state.lang].srs_export_word;
    } else if (format === 'markdown') {
        exportLabel.textContent = i18n[state.lang].srs_export_markdown;
    } else {
        exportLabel.textContent = i18n[state.lang].srs_export_pdf;
    }
}

function toMarkdownFromSrs(draftContent, draftMeta) {
    const content = draftContent || {};
    const lines = [];
    lines.push(
        `# ${state.lang === 'ar' ? 'وثيقة متطلبات البرمجيات' : 'Software Requirements Specification'}`,
        '',
        `- ${state.lang === 'ar' ? 'المشروع' : 'Project'}: ${draftMeta?.project_id || '-'}`,
        `- ${state.lang === 'ar' ? 'الإصدار' : 'Version'}: ${draftMeta?.version || 1}`,
        `- ${state.lang === 'ar' ? 'الحالة' : 'Status'}: ${content.status || 'draft'}`,
        ''
    );

    appendSummaryMarkdown(lines, content.summary);

    const sections = Array.isArray(content.sections) ? content.sections : [];
    sections.forEach((section) => appendMarkdownSection(lines, section));

    const activityDiagram = Array.isArray(content.activity_diagram) ? content.activity_diagram : [];
    appendMarkdownListBlock(
        lines,
        state.lang === 'ar' ? 'مخطط النشاط' : 'Activity Diagram',
        activityDiagram.map((line) => String(line).replaceAll(/\s*->\s*/g, ' → '))
    );

    const activityDiagrams = Array.isArray(content.activity_diagrams) ? content.activity_diagrams : [];
    if (activityDiagrams.length) {
        activityDiagrams.forEach((diagram, idx) => {
            const title = String(diagram?.title || (state.lang === 'ar' ? `تدفق نشاط ${idx + 1}` : `Activity Flow ${idx + 1}`)).trim();
            const flowLines = Array.isArray(diagram?.activity_diagram)
                ? diagram.activity_diagram.map((line) => String(line).replaceAll(/\s*->\s*/g, ' → '))
                : [];
            appendMarkdownListBlock(lines, title, flowLines);

            const mermaidCode = typeof diagram?.activity_diagram_mermaid === 'string'
                ? diagram.activity_diagram_mermaid.trim()
                : '';
            if (mermaidCode) {
                lines.push(`### ${title} (Mermaid)`, '```mermaid', mermaidCode, '```', '');
            }
        });
    }

    const activityMermaid = typeof content.activity_diagram_mermaid === 'string'
        ? content.activity_diagram_mermaid.trim()
        : '';
    appendMermaidMarkdown(lines, activityMermaid);

    const questions = Array.isArray(content.questions) ? content.questions : [];
    appendMarkdownListBlock(lines, state.lang === 'ar' ? 'نقاط تحتاج توضيح' : 'Open Questions', questions);

    // User Stories
    const userStories = Array.isArray(content.user_stories) ? content.user_stories : [];
    if (userStories.length) {
        lines.push(`## ${state.lang === 'ar' ? 'قصص المستخدمين ومعايير القبول' : 'User Stories & Acceptance Criteria'}`);
        userStories.forEach(s => {
            const asA    = state.lang === 'ar' ? 'بوصفي' : 'As a';
            const iWant  = state.lang === 'ar' ? 'أريد' : 'I want to';
            const soThat = state.lang === 'ar' ? 'حتى أتمكن من' : 'so that';
            lines.push(`- **${asA}** ${s.role || ''}, **${iWant}** ${s.action || ''}, **${soThat}** ${s.goal || ''}`);
            (s.acceptance_criteria || []).forEach(ac => lines.push(`  - ✓ ${ac}`));
        });
        lines.push('');
    }

    // User Roles
    const userRoles = Array.isArray(content.user_roles) ? content.user_roles : [];
    if (userRoles.length) {
        lines.push(`## ${state.lang === 'ar' ? 'أدوار المستخدمين' : 'User Roles'}`);
        userRoles.forEach(r => {
            const perms = Array.isArray(r.permissions) && r.permissions.length
                ? ` — ${r.permissions.join(', ')}`
                : '';
            lines.push(`- **${r.role || ''}**: ${r.description || ''}${perms}`);
        });
        lines.push('');
    }

    const nextSteps = Array.isArray(content.nextSteps || content.next_steps) ? (content.nextSteps || content.next_steps) : [];
    appendMarkdownListBlock(lines, state.lang === 'ar' ? 'الخطوات القادمة' : 'Next Steps', nextSteps);

    lines.push('---', 'Generated intelligently by Tawasul AI');
    return lines.join('\n');
}

function appendMarkdownSection(lines, section) {
    const title = section?.title || (state.lang === 'ar' ? 'قسم' : 'Section');
    const confidence = section?.confidence ? ` (${section.confidence})` : '';
    const items = Array.isArray(section?.items) ? section.items : [];
    appendMarkdownListBlock(lines, `${title}${confidence}`, items);
}

function appendSummaryMarkdown(lines, summary) {
    if (!summary) return;
    lines.push(`## ${state.lang === 'ar' ? 'الملخص' : 'Summary'}`, String(summary), '');
}

function appendMermaidMarkdown(lines, mermaidCode) {
    if (!mermaidCode) return;
    lines.push('```mermaid', mermaidCode, '```', '');
}

function appendMarkdownListBlock(lines, heading, items) {
    if (!items.length) return;
    lines.push(`## ${heading}`);
    items.forEach((item) => lines.push(`- ${item}`));
    lines.push('');
}

function downloadTextBlob(filename, mimeType, text) {
    const blob = new Blob([text], { type: mimeType });
    const url = globalThis.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    globalThis.URL.revokeObjectURL(url);
}

async function exportSrsDocument(projectId, format = 'pdf') {
    if (format === 'pdf') {
        await downloadSrsPdf(projectId);
        return;
    }

    const draftBundle = state.lastRenderedSrsDraft;
    if (!draftBundle?.content) {
        showNotification(state.lang === 'ar' ? 'حدّث المسودة أولاً ثم أعد التصدير.' : 'Refresh draft first, then export again.', 'warning');
        return;
    }

    const markdown = toMarkdownFromSrs(draftBundle.content, draftBundle.meta || {});
    if (format === 'word') {
        const mermaidCode = typeof draftBundle?.content?.activity_diagram_mermaid === 'string'
            ? draftBundle.content.activity_diagram_mermaid.trim()
            : '';
        const mermaidSvg = mermaidCode ? await renderMermaidForExport(mermaidCode) : '';
        const mermaidTitle = state.lang === 'ar' ? 'مخطط النشاط (Mermaid)' : 'Activity Diagram (Mermaid)';
        const mermaidBody = mermaidSvg ? `<div>${mermaidSvg}</div>` : `<pre>${escapeHtml(mermaidCode)}</pre>`;
        const mermaidBlock = mermaidCode
            ? `
                <h3>${escapeHtml(mermaidTitle)}</h3>
                ${mermaidBody}
            `
            : '';

        const htmlDoc = `<!doctype html><html><head><meta charset="utf-8"></head><body>${mermaidBlock}<pre>${escapeHtml(markdown)}</pre><p>Generated intelligently by Tawasul AI</p></body></html>`;
        downloadTextBlob(`srs_project_${projectId}.doc`, 'application/msword', htmlDoc);
        return;
    }
    downloadTextBlob(`srs_project_${projectId}.md`, 'text/markdown;charset=utf-8', markdown);
}

async function renderMermaidForExport(code) {
    const mermaidApi = globalThis.mermaid;
    if (!mermaidApi || typeof mermaidApi.render !== 'function') {
        return '';
    }

    try {
        if (!globalThis.__tawasulMermaidInitialized) {
            mermaidApi.initialize({ startOnLoad: false, securityLevel: 'loose' });
            globalThis.__tawasulMermaidInitialized = true;
        }
        const graphId = `srs-export-mermaid-${Date.now()}`;
        const result = await mermaidApi.render(graphId, code);
        return result?.svg || '';
    } catch (error) {
        console.error('Mermaid export render error:', error);
        return '';
    }
}

async function downloadSrsPdf(projectId) {
    try {
        const response = await fetch(`${API_BASE_URL}/projects/${projectId}/srs/export`, {
            headers: authHeaders()
        });
        await throwIfNotOk(response);
        const blob = await response.blob();
        const url = globalThis.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `srs_project_${projectId}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        globalThis.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('SRS Export Error:', error);
        showNotification(state.lang === 'ar' ? 'تعذر تصدير SRS' : 'Failed to export SRS', 'error');
    }
}

async function logChatMessages(projectId, userText, assistantText, sources, userMetadata = null) {
    try {
        await api.post(`/projects/${projectId}/messages`, {
            messages: [
                { role: 'user', content: userText, metadata: userMetadata || undefined },
                { role: 'assistant', content: assistantText, metadata: { sources: sources || [] } }
            ]
        });
        return true;
    } catch (error) {
        console.error('Log Messages Error:', error);
        return false;
    }
}

async function refreshLivePatchPanel(projectId, language) {
    try {
        const patchResult = await api.post(`/projects/${projectId}/messages/live-patch`, {
            language,
            last_summary: state.previousSummary || null,
            last_coverage: state.lastCoverage || null
        });
        if (!patchResult?.summary) return;

        state.previousSummary = patchResult.summary || state.previousSummary;
        state.lastCoverage = patchResult.coverage || state.lastCoverage;
        state.lastInterviewSignals = patchResult.signals || null;
        state.lastLivePatch = patchResult.live_patch || null;
        state.lastCycleTrace = patchResult.cycle_trace || null;
        state.lastTopicNavigation = patchResult.topic_navigation || null;
        state.interviewStage = patchResult.stage || state.interviewStage;

        const liveDocPanel = document.getElementById('live-doc-panel');
        if (liveDocPanel) {
            applySummaryDrawerState();
        }

        updateLiveDoc(patchResult.summary, patchResult.stage || 'discovery');
    } catch (error) {
        console.error('Live Patch Refresh Error:', error);
        showNotification(error?.message || (state.lang === 'ar' ? 'تعذر تحديث لوحة التقدم' : 'Failed to refresh live patch'), 'warning');
    }
}

function getProjectNameById(projectId) {
    const project = (state.projects || []).find((item) => Number(item.id) === Number(projectId));
    return project?.name || '';
}

function updateChatProjectHeader(projectId) {
    const titleEl = document.getElementById('chat-project-title');
    if (!titleEl) return;

    const projectName = projectId ? getProjectNameById(projectId) : '';
    const fallback = state.lang === 'ar' ? 'المشروع: -' : 'Project: -';
    const projectLabel = state.lang === 'ar' ? `المشروع: ${projectName}` : `Project: ${projectName}`;
    titleEl.textContent = projectName
        ? projectLabel
        : fallback;
}

function applySummaryDrawerState() {
    const panel = document.getElementById('live-doc-panel');
    const summaryBtn = document.getElementById('summary-toggle-btn');
    if (!panel) return;

    const shouldShow = state.interviewMode && !state.summaryCollapsed;
    panel.classList.toggle('is-collapsed', !shouldShow);
    panel.style.display = shouldShow ? 'flex' : 'none';

    if (summaryBtn) {
        summaryBtn.classList.toggle('active', shouldShow);
        summaryBtn.setAttribute('aria-expanded', shouldShow ? 'true' : 'false');
    }
}

function getInterviewStarterPrompts(projectId) {
    const projectName = getProjectNameById(projectId);
    if (state.lang === 'ar') {
        return [
            `ما المشكلة الأساسية التي يحلها ${projectName || 'المشروع'}؟`,
            `مين المستخدمين الأساسيين في ${projectName || 'المشروع'} وإيه أولوياتهم؟`,
            `ما أهم 3 متطلبات MVP والقيود الزمنية/الميزانية؟`
        ];
    }

    return [
        `What core problem does ${projectName || 'this project'} solve?`,
        `Who are the primary users of ${projectName || 'this project'} and what matters most to them?`,
        'What are the top 3 MVP requirements and timeline/budget constraints?'
    ];
}

function getChatWelcomeMarkup(projectId) {
    const prompts = getInterviewStarterPrompts(projectId);
    const title = state.lang === 'ar'
        ? 'لنبدأ اكتشاف المتطلبات'
        : 'Let’s start requirements discovery';
    const subtitle = state.lang === 'ar'
        ? 'اكتب تفاصيل مشروعك، وسأطرح أسئلة مرتبطة مباشرة لبناء SRS احترافي.'
        : 'Share your project details and I will ask focused questions to build a professional SRS.';

    return `
        <div class="welcome-msg-pro">
            <div class="welcome-icon">
                <i class="fas fa-robot"></i>
            </div>
            <h2>${title}</h2>
            <p>${subtitle}</p>
            <div class="welcome-suggestions">
                ${prompts.map((prompt) => `<button class="suggestion-chip">${escapeHtml(prompt)}</button>`).join('')}
            </div>
        </div>
    `;
}

function bindSuggestionChips() {
    const chatInput = document.getElementById('chat-input');
    if (!chatInput) return;
    document.querySelectorAll('.suggestion-chip').forEach((chip) => {
        chip.onclick = () => {
            chatInput.value = chip.textContent;
            chatInput.dispatchEvent(new Event('input', { bubbles: true }));
            chatInput.focus();
        };
    });
}

async function loadChatHistory(projectId) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    updateChatProjectHeader(projectId);

    // Show loading state
    messagesContainer.innerHTML = `
        <div class="welcome-msg-pro">
            <div class="welcome-icon">
                <i class="fas fa-spinner fa-spin"></i>
            </div>
            <p>${state.lang === 'ar' ? 'جاري تحميل المحادثة...' : 'Loading conversation...'}</p>
        </div>
    `;

    try {
        const messages = await api.get(`/projects/${projectId}/messages?limit=120`);

        // Clear container
        messagesContainer.innerHTML = '';

        if (!messages || messages.length === 0) {
            // Show welcome message if no history
            messagesContainer.innerHTML = getChatWelcomeMarkup(projectId);
            bindSuggestionChips();
            await refreshInterviewTelemetry(projectId);
            updateInterviewAssistBar(state.lastCoverage);
            return;
        }

        // Render each message from history
        for (const msg of messages) {
            const role = msg.role === 'user' ? 'user' : 'bot';
            const id = addChatMessage(role, msg.role === 'user' ? msg.content : '', false);

            // For assistant messages, render formatted HTML
            if (msg.role === 'assistant') {
                const textEl = document.querySelector(`#msg-${id} .msg-text`);
                if (textEl) {
                    textEl.innerHTML = formatAnswerHtml(msg.content) || escapeHtml(msg.content);
                    textEl.dir = detectTextDirection(msg.content);
                }

                // Render sources if available in metadata
                if (msg.metadata?.sources?.length > 0) {
                    const msgDiv = document.getElementById(`msg-${id}`);
                    const sourcesDiv = document.createElement('div');
                    sourcesDiv.className = 'msg-sources-pro';
                    sourcesDiv.innerHTML = `
                        <div class="sources-header">
                            <i class="fas fa-book-open"></i>
                            <span>${state.lang === 'ar' ? 'المصادر المستخدمة' : 'Sources Used'}</span>
                        </div>
                    `;
                    const list = document.createElement('ul');
                    msg.metadata.sources.slice(0, 5).forEach(s => {
                        const li = document.createElement('li');
                        li.innerHTML = `
                            <i class="fas fa-file-alt"></i>
                            <span>${escapeHtml(s.document_name || s.name || '')}</span>
                            ${s.similarity ? `<span class="source-score">${(s.similarity * 100).toFixed(0)}%</span>` : ''}
                        `;
                        list.appendChild(li);
                    });
                    sourcesDiv.appendChild(list);
                    msgDiv.querySelector('.msg-body').appendChild(sourcesDiv);
                }
            }
        }

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        if (messages.length > 0) {
            await refreshLivePatchPanel(projectId, state.lang);
        }
        await refreshInterviewTelemetry(projectId);
        updateInterviewAssistBar(state.lastCoverage);
    } catch (error) {
        console.error('Load Chat History Error:', error);
        showNotification(error?.message || (state.lang === 'ar' ? 'تعذر تحميل المحادثة' : 'Failed to load conversation'), 'error');
        messagesContainer.innerHTML = getChatWelcomeMarkup(projectId);
        bindSuggestionChips();
    }
}

function createProjectCard(project) {
    const card = document.createElement('div');
    card.className = 'project-card';
    const docCount = project.document_count || 0;
    const progressInfo = getProjectProgressInfo(project);
    card.innerHTML = `
        <h3>${escapeHtml(project.name)}</h3>
        <p>${escapeHtml(project.description || i18n[state.lang].project_goal_hint)}</p>
        <div class="project-progress-wrap" title="${escapeHtml(progressInfo.label)}">
            <div class="project-progress-head">
                <span>${escapeHtml(progressInfo.label)}</span>
                <strong>${Math.round(progressInfo.progress)}%</strong>
            </div>
            <div class="project-progress-track">
                <div class="project-progress-fill" style="width: ${Math.round(progressInfo.progress)}%"></div>
            </div>
        </div>
        <div class="project-card-footer">
            <span class="project-card-date"><i class="far fa-calendar"></i> ${new Date(project.created_at).toLocaleDateString(state.lang === 'ar' ? 'ar-EG' : 'en-US')}</span>
            <div class="project-card-actions">
                <span class="doc-count-badge"><i class="fas fa-file-alt"></i> ${docCount}</span>
                <button class="delete-project-btn icon-btn" style="width: 30px; height: 30px; color: var(--error);" data-id="${project.id}" title="${state.lang === 'ar' ? 'حذف المشروع' : 'Delete Project'}">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        </div>
        <div class="project-card-quick-actions">
            <button class="btn btn-primary btn-sm project-interview-btn">
                <i class="fas fa-comments"></i>
                <span>${state.lang === 'ar' ? 'مقابلة' : 'Interview'}</span>
            </button>
            <button class="btn btn-outline btn-sm project-srs-btn">
                <i class="fas fa-file-signature"></i>
                <span>${state.lang === 'ar' ? 'عرض المتطلبات' : 'View SRS'}</span>
            </button>
        </div>
    `;

    card.onclick = (e) => {
        if (e.target.closest('.delete-project-btn')) {
            e.stopPropagation();
            handleDeleteProject(project.id, project.name);
            return;
        }

        if (e.target.closest('.project-interview-btn')) {
            state.interviewMode = true;
            state.pendingProjectSelect = project.id;
            switchView('chat');
            return;
        }
        if (e.target.closest('.project-srs-btn')) {
            state.pendingProjectSelect = project.id;
            switchView('srs');
            return;
        }
        // Default card click: open interview
        state.interviewMode = true;
        state.pendingProjectSelect = project.id;
        switchView('chat');
    };

    return card;
}

function createDocItem(doc) {
    const item = document.createElement('div');
    item.className = 'doc-item';
    let statusClass = 'status-processing';
    let statusIcon = 'fa-spinner fa-spin';
    if (doc.status === 'completed') {
        statusClass = 'status-done';
        statusIcon = 'fa-check-circle';
    } else if (doc.status === 'failed') {
        statusClass = 'status-error';
        statusIcon = 'fa-exclamation-circle';
    }
    const meta = doc.extra_metadata || {};
    const totalChunks = Number.isFinite(meta.total_chunks) ? meta.total_chunks : null;
    const processedChunks = Number.isFinite(meta.processed_chunks) ? meta.processed_chunks : null;
    const progressValue = Number.isFinite(meta.progress) ? meta.progress : null;
    const showProgress = doc.status === 'processing' && totalChunks && totalChunks > 0;
    let progressPercent;
    if (progressValue == null) {
        progressPercent = Math.round((processedChunks || 0) / totalChunks * 100);
    } else {
        progressPercent = Math.max(0, Math.min(100, progressValue));
    }

    const statusText = {
        completed: state.lang === 'ar' ? 'مكتمل' : 'Completed',
        failed: state.lang === 'ar' ? 'فشل' : 'Failed',
        processing: state.lang === 'ar' ? 'جاري المعالجة' : 'Processing'
    };

    item.innerHTML = `
        <div class="doc-info">
            <i class="fas fa-file-pdf"></i>
            <div class="doc-details">
                <span class="doc-name">${escapeHtml(doc.original_filename)}</span>
                <span class="doc-size">${(doc.file_size / 1024).toFixed(1)} KB</span>
            </div>
        </div>
        <div class="doc-status ${statusClass}">
            <i class="fas ${statusIcon}"></i>
            <span>${statusText[doc.status] || doc.status}</span>
        </div>
        ${showProgress ? `
            <div class="doc-progress">
                <div class="doc-progress-header">
                    <span>${i18n[state.lang].processing_label}</span>
                    <span>${processedChunks || 0}/${totalChunks}</span>
                </div>
                <div class="doc-progress-track">
                    <div class="doc-progress-bar" style="width: ${progressPercent}%;"></div>
                </div>
            </div>
        ` : ''}
    `;

    return item;
}

function renderDocsList(docs) {
    const docsList = document.getElementById('project-docs-list');
    if (!docsList) return;
    docsList.innerHTML = '';

    if (docs.length === 0) {
        docsList.innerHTML = `
            <div class="empty-state" style="padding: 24px 0;">
                <div class="empty-state-icon"><i class="fas fa-file-circle-plus"></i></div>
                <h3>${state.lang === 'ar' ? 'لا توجد ملفات بعد' : 'No files yet'}</h3>
                <p>${state.lang === 'ar' ? 'ارفع مستند نص المقابلة أو ملف مرجعي لمساعدة الذكاء الاصطناعي' : 'Upload an interview transcript or reference document to help the AI'}</p>
            </div>
        `;
        return;
    }

    docs.forEach(doc => {
        docsList.appendChild(createDocItem(doc));
    });
}

function startDocPolling(projectId, docs) {
    if (state.docPoller) {
        clearTimeout(state.docPoller);
        state.docPoller = null;
    }

    const hasProcessing = docs.some(doc => doc.status === 'processing');
    if (!hasProcessing) return;

    const baseDelayMs = 10000;
    const maxDelayMs = 60000;
    let attempt = 0;

    const pollOnce = async () => {
        if (state.currentView !== 'chat') {
            clearTimeout(state.docPoller);
            state.docPoller = null;
            return;
        }

        try {
            const updated = await api.get(`/projects/${projectId}/documents`);
            renderDocsList(updated);
            const stillProcessing = updated.some(doc => doc.status === 'processing');
            if (!stillProcessing) {
                clearTimeout(state.docPoller);
                state.docPoller = null;
                return;
            }
            attempt += 1;
        } catch (error) {
            console.error('Docs Poll Error:', error);
            attempt += 1;
        }

        const nextDelay = Math.min(baseDelayMs * (2 ** attempt), maxDelayMs);
        state.docPoller = setTimeout(pollOnce, nextDelay);
    };

    state.docPoller = setTimeout(pollOnce, baseDelayMs);
}

const _activeToasts = [];
const _maxToasts = 3;

function showNotification(message, type = 'info') {
    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-circle-exclamation',
        warning: 'fa-triangle-exclamation',
        info: 'fa-circle-info'
    };

    // Remove oldest if at max
    while (_activeToasts.length >= _maxToasts) {
        const oldest = _activeToasts.shift();
        oldest.classList.remove('show');
        setTimeout(() => oldest.remove(), 400);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fas ${iconMap[type] || iconMap.info} toast-icon"></i><span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);
    _activeToasts.push(toast);

    // Stack toasts bottom-to-top
    _repositionToasts();

    setTimeout(() => toast.classList.add('show'), 50);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
            const idx = _activeToasts.indexOf(toast);
            if (idx !== -1) _activeToasts.splice(idx, 1);
            _repositionToasts();
        }, 400);
    }, 3000);
}

function _repositionToasts() {
    let offset = 32;
    for (let i = _activeToasts.length - 1; i >= 0; i--) {
        _activeToasts[i].style.bottom = offset + 'px';
        offset += 60;
    }
}

function applyTranslations() {
    const t = i18n[state.lang];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (t[key]) el.textContent = t[key];
    });

    // Update placeholders
    if (document.getElementById('new-project-name')) {
        document.getElementById('new-project-name').placeholder = t.project_name_ph;
        document.getElementById('new-project-desc').placeholder = t.project_desc_ph;
    }

    // Update Lang Button
    elements.langToggle.querySelector('.lang-code').textContent = state.lang === 'ar' ? 'EN' : 'AR';

    // Update Dir
    document.documentElement.dir = state.lang === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = state.lang;

    // Update search placeholder
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) searchInput.placeholder = t.search_placeholder;

    const exportFormat = document.getElementById('srs-export-format');
    if (exportFormat) {
        updateExportButtonLabel(exportFormat.value || 'pdf');
    }

    // Update back button icon direction
    const backBtn = document.getElementById('back-to-projects');
    if (backBtn) {
        const icon = backBtn.querySelector('i');
        if (icon) icon.className = state.lang === 'ar' ? 'fas fa-arrow-right' : 'fas fa-arrow-left';
    }
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.body.classList.toggle('light-theme', state.theme === 'light');
    document.body.classList.toggle('dark-theme', state.theme === 'dark');

    const icon = elements.themeToggle.querySelector('i');
    icon.className = state.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';

    safeStorageSet('theme', state.theme);
}

function toggleLang() {
    state.lang = state.lang === 'ar' ? 'en' : 'ar';
    safeStorageSet('lang', state.lang);
    applyTranslations();
    switchView(state.currentView, state.selectedProject ? state.selectedProject.id : null);
}

// --- Event Handlers ---

async function switchView(viewName, params = null) {
    if (ADMIN_ONLY_VIEWS.has(viewName) && !isAdminUser()) {
        showNotification(state.lang === 'ar' ? 'هذه الصفحة متاحة للمسؤول فقط' : 'This page is admin-only', 'warning');
        viewName = 'projects';
    }

    if (!views[viewName]) {
        viewName = 'projects';
    }

    if (state.docPoller) {
        clearTimeout(state.docPoller);
        state.docPoller = null;
    }
    state.currentView = viewName;

    // Update Nav
    elements.navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Render View
    if (views[viewName]) {
        await views[viewName]();
    }
}

async function handleNewProject(defaultTemplateId = '') {
    const t = i18n[state.lang];
    const langKey = state.lang === 'ar' ? 'ar' : 'en';

    elements.modalTitle.textContent = t.start_idea_title;
    elements.modalBody.innerHTML = `
        <div class="form-group">
            <label>${state.lang === 'ar' ? 'اسم الفكرة / المشروع' : 'Idea / Project Name'}</label>
            <input type="text" id="new-project-name" class="form-control" placeholder="${t.idea_name_ph}">
        </div>
        <div class="form-group">
            <label>${state.lang === 'ar' ? 'الوصف (اختياري)' : 'Description (optional)'}</label>
            <textarea id="new-project-desc" class="form-control" placeholder="${t.project_desc_ph}"></textarea>
        </div>
        <button id="save-project-btn" class="btn btn-primary w-100 mt-4">
            <i class="fas fa-lightbulb"></i> ${t.start_idea_submit}
        </button>
    `;
    applyTranslations();

    elements.modalOverlay.classList.remove('hidden');

    const descInput = document.getElementById('new-project-desc');
    const nameInput = document.getElementById('new-project-name');

    if (defaultTemplateId && IDEA_TEMPLATES[defaultTemplateId]) {
        const info = IDEA_TEMPLATES[defaultTemplateId][langKey];
        if (!descInput.value.trim()) {
            descInput.value = info.description;
        }
        if (!nameInput.value.trim()) {
            nameInput.value = info.title;
        }
    }

    document.getElementById('save-project-btn').onclick = async () => {
        const name = nameInput.value;
        const descriptionBase = document.getElementById('new-project-desc').value;
        const templatePrompt = defaultTemplateId && IDEA_TEMPLATES[defaultTemplateId]
            ? IDEA_TEMPLATES[defaultTemplateId][langKey].prompt
            : '';
        const description = [descriptionBase, templatePrompt].filter(Boolean).join('\n\n');

        if (!name) {
            showFieldError(nameInput, i18n[state.lang].validation_project_name);
            return;
        }

        const btn = document.getElementById('save-project-btn');
        setButtonLoading(btn, true);
        try {
            const newProject = await api.post('/projects/', { name, description });
            showNotification(i18n[state.lang].success_saved, 'success');
            elements.modalOverlay.classList.add('hidden');

            // Navigate to chat with interview mode ON
            state.interviewMode = true;
            state.pendingProjectSelect = newProject.id;
            state.previousSummary = null;
            state.lastCoverage = null;
            state.lastInterviewSignals = null;
            state.lastLivePatch = null;
            state.lastCycleTrace = null;
                state.lastTopicNavigation = null;
            switchView('chat');
        } catch (error) {
            console.error('Create Project Error:', error);
        } finally {
            setButtonLoading(btn, false);
        }
    };

    // Setup field validation on project name input
    if (nameInput) {
        nameInput.addEventListener('input', () => clearFieldError(nameInput));
    }
}

async function handleDeleteProject(id, projectName = '') {
    const isAr = state.lang === 'ar';
    const safeName = String(projectName || '').trim();
    const confirmMsg = isAr
        ? `هل أنت متأكد من حذف مشروع "${safeName || id}" وكل محتوياته (بما فيها المحادثات والمستندات)؟`
        : `Are you sure you want to delete project "${safeName || id}" and all its contents?`;

    const confirmed = await showConfirmDialog(confirmMsg);
    if (!confirmed) return;

    showLoader();
    try {
        await api.delete(`/projects/${id}`);
        showNotification(isAr ? 'تم حذف المشروع بنجاح' : 'Project deleted successfully', 'success');
        await views.projects();
    } catch (error) {
        console.error('Delete Project Error:', error);
        showNotification(error.message || (isAr ? 'حدث خطأ أثناء الحذف' : 'Error deleting project'), 'error');
    } finally {
        hideLoader();
    }
}

async function handleChatSubmit() {
    const input = document.getElementById('chat-input');
    const projectSelect = document.getElementById('chat-project-select');
    const sendBtn = document.getElementById('send-btn');

    const query = input.value.trim();
    const projectId = projectSelect.value;
    const language = detectMessageLanguage(query, state.lang);

    if (!query) return;

    const validationError = getChatSubmitValidationError(query, projectId);
    if (validationError) {
        showNotification(validationError, 'warning');
        return;
    }

    const pendingSttMetadata = state.pendingSttMeta || null;
    state.pendingSttMeta = null;

    addChatMessage('user', query);
    resetChatInputUi(input, sendBtn);

    const thinkingId = addChatMessage('bot', '', true);

    if (state.interviewMode) {
        await handleInterviewTurn({
            projectId,
            query,
            language,
            thinkingId,
            pendingSttMetadata,
        });
        return;
    }

    try {
        const streamResult = await streamProjectQuery(projectId, query, language, thinkingId);
        await finalizeQueryResult(projectId, query, language, thinkingId, streamResult, pendingSttMetadata);

    } catch (error) {
        console.warn('Stream failed, falling back to non-streaming:', error.message);
        await handleQueryFallback(projectId, query, language, thinkingId, pendingSttMetadata);
    }
}

function detectMessageLanguage(text, fallback = 'ar') {
    const value = String(text || '');
    const arabicCount = (value.match(/[\u0600-\u06FF]/g) || []).length;
    const latinCount = (value.match(/[A-Za-z]/g) || []).length;

    if (arabicCount === 0 && latinCount === 0) {
        return fallback === 'en' ? 'en' : 'ar';
    }

    return arabicCount >= latinCount ? 'ar' : 'en';
}

function getChatSubmitValidationError(query, projectId) {
    if (!query) return null;
    if (state.interviewMode && normalizeInterviewText(query) === normalizeInterviewText(state.lastUserInterviewAnswer)) {
        return i18n[state.lang].interview_duplicate_guard;
    }
    if (!projectId) {
        return state.lang === 'ar' ? 'يرجى اختيار مشروع أولاً' : 'Select a project first';
    }
    return null;
}

function resetChatInputUi(input, sendBtn) {
    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;
}

async function streamProjectQuery(projectId, query, language, thinkingId) {
    const payload = { query, language };
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}/query/stream`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
    });
    await throwIfNotOk(response);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const streamState = {
        buffer: '',
        fullAnswer: '',
        sources: null,
        indicatorRemoved: false,
    };

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        consumeStreamChunk(streamState, decoder.decode(value, { stream: true }), thinkingId);
    }

    return {
        answer: streamState.fullAnswer,
        sources: streamState.sources,
    };
}

function consumeStreamChunk(streamState, chunk, thinkingId) {
    streamState.buffer += chunk;
    const lines = streamState.buffer.split('\n');
    streamState.buffer = lines.pop();

    for (const line of lines) {
        processStreamLine(streamState, line, thinkingId);
    }
}

function processStreamLine(streamState, line, thinkingId) {
    if (!line.startsWith('data: ')) return;
    const dataStr = line.slice(6).trim();
    if (dataStr === '[DONE]') return;

    try {
        const evt = JSON.parse(dataStr);
        applyStreamEvent(streamState, evt, thinkingId);
    } catch (error_) {
        console.warn('Malformed stream event ignored.', error_);
    }
}

function applyStreamEvent(streamState, evt, thinkingId) {
    if (evt.type === 'sources') {
        streamState.sources = evt.sources;
        return;
    }
    if (evt.type === 'token') {
        removeThinkingIndicatorOnce(streamState, thinkingId);
        streamState.fullAnswer += evt.token;
        renderStreamingAnswer(thinkingId, streamState.fullAnswer);
        return;
    }
    if (evt.type === 'error') {
        streamState.fullAnswer = evt.message || i18n[state.lang].error_generic;
    }
}

function removeThinkingIndicatorOnce(streamState, thinkingId) {
    if (streamState.indicatorRemoved) return;
    const ind = document.querySelector(`#msg-${thinkingId} .typing-indicator-pro`);
    if (ind) ind.remove();
    streamState.indicatorRemoved = true;
}

function renderStreamingAnswer(thinkingId, fullAnswer) {
    const textEl = document.querySelector(`#msg-${thinkingId} .msg-text`);
    if (textEl) {
        textEl.classList.add('streaming');
        textEl.innerHTML = formatAnswerHtml(fullAnswer) || escapeHtml(fullAnswer);
        textEl.dir = detectTextDirection(fullAnswer);
    }
    const container = document.getElementById('chat-messages');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

async function finalizeQueryResult(projectId, query, language, thinkingId, result, pendingSttMetadata) {
    finalizeBotMessage(thinkingId, result.answer, result.sources);
    await logChatMessages(projectId, query, result.answer, result.sources, pendingSttMetadata);
    await refreshLivePatchPanel(projectId, language);
}

async function handleQueryFallback(projectId, query, language, thinkingId, pendingSttMetadata) {
    try {
        const payload = { query, language };
        const result = await api.post(`/projects/${projectId}/query`, payload);
        removeThinkingIndicator(thinkingId);
        await finalizeQueryResult(projectId, query, language, thinkingId, { answer: result.answer, sources: result.sources }, pendingSttMetadata);
    } catch (error_) {
        removeThinkingIndicator(thinkingId);
        console.warn('Fallback non-streaming query failed:', error_);
        finalizeBotMessage(thinkingId, i18n[state.lang].error_generic, null);
    }
}

function removeThinkingIndicator(thinkingId) {
    const ind = document.querySelector(`#msg-${thinkingId} .typing-indicator-pro`);
    if (ind) ind.remove();
}

async function handleInterviewTurn({ projectId, query, language, thinkingId, pendingSttMetadata }) {
    const timeoutMs = 30000;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        state.lastUserInterviewAnswer = query;
        const userMessageMetadata = {};
        if (state.pendingInterviewSelectionMeta && typeof state.pendingInterviewSelectionMeta === 'object') {
            Object.assign(userMessageMetadata, state.pendingInterviewSelectionMeta);
        }
        if (pendingSttMetadata && typeof pendingSttMetadata === 'object') {
            Object.assign(userMessageMetadata, pendingSttMetadata);
        }
        state.pendingInterviewSelectionMeta = null;
        await api.post(`/projects/${projectId}/messages`, {
            messages: [{ role: 'user', content: query, metadata: Object.keys(userMessageMetadata).length ? userMessageMetadata : undefined }]
        });

        const interviewPayload = { language };
        // Do NOT send summary or coverage anymore; backend is source of truth

        const next = await api.post(
            `/projects/${projectId}/interview/next`,
            interviewPayload,
            false,
            { signal: controller.signal },
        );
        await refreshInterviewTelemetry(projectId);

        const questionText = next.question || (state.lang === 'ar'
            ? 'هل يمكن توضيح النقطة الأخيرة بمثال؟'
            : 'Could you clarify the last point with an example?');

        let finalQuestionText = questionText;
        if (normalizeInterviewText(questionText) === normalizeInterviewText(state.lastAssistantQuestion)) {
            finalQuestionText = state.lang === 'ar'
                ? 'تمام، خلّينا نوضّح النقطة دي بسرعة: إيه التفصيلة الأهم اللي تحب نعتمدها الآن كقرار واضح؟'
                : 'Understood — let’s clarify this quickly: what is the single most important detail we should lock now as a clear decision?';
        }
        state.lastAssistantQuestion = finalQuestionText;
        finalizeBotMessage(thinkingId, finalQuestionText, null);

        if (next.coverage) {
            state.lastCoverage = next.coverage;
        }
        state.lastInterviewSignals = next.signals || null;
        state.lastLivePatch = next.live_patch || null;
        state.lastCycleTrace = next.cycle_trace || null;
        state.lastTopicNavigation = next.topic_navigation || null;
        state.interviewStage = next.stage || state.interviewStage;
        updateInterviewProgress(next.coverage, next.done, next.topic_navigation);
        updateInterviewAssistBar(next.coverage);
        if (next.summary) {
            updateLiveDoc(next.summary, next.stage);
        }

        const warningText = Array.isArray(next?.live_patch?.warnings) ? next.live_patch.warnings[0] : '';
        if (warningText) {
            showNotification(warningText, 'warning');
        }

        await saveInterviewDraft(Number.parseInt(projectId, 10));

        await api.post(`/projects/${projectId}/messages`, {
            messages: [{ role: 'assistant', content: finalQuestionText, metadata: { stage: next.stage || '' } }]
        });

        if (next.done) {
            showNotification(i18n[state.lang].interview_completed, 'success');
            await openInterviewReviewModal(Number.parseInt(projectId, 10), language, next);
        }
    } catch (error) {
        console.error('Interview Error:', error);
        const aborted = error?.name === 'AbortError';
        const timeoutMsg = state.lang === 'ar' ? 'انتهت مهلة الطلب. حاول مرة أخرى.' : 'Request timed out. Please try again.';
        const failedMsg = state.lang === 'ar' ? 'تعذر إكمال المقابلة الآن' : 'Interview failed. Try again.';
        const msg = aborted ? timeoutMsg : failedMsg;
        finalizeBotMessage(thinkingId, msg, null);
        showNotification(msg, 'error');
    } finally {
        clearTimeout(timeoutId);
    }
}

async function openInterviewReviewModal(projectId, language, interviewResult) {
    const t = i18n[state.lang];
    const summary = interviewResult?.summary || state.previousSummary || {};
    const coverage = interviewResult?.coverage || state.lastCoverage || {};

    elements.modalTitle.textContent = state.lang === 'ar' ? 'مراجعة نهائية قبل الإرسال' : 'Final review before submit';
    elements.modalBody.innerHTML = `
        <div class="interview-review-box">
            <p class="chat-disclaimer">${escapeHtml(t.interview_privacy)}</p>
            ${INTERVIEW_AREAS.map((area) => {
                const label = i18n[state.lang][`stage_${area}`] || area;
                const items = Array.isArray(summary[area]) ? summary[area] : [];
                const percent = Math.round(Number(coverage[area] || 0));
                return `
                    <div class="form-group">
                        <label>${escapeHtml(label)} (${percent}%)</label>
                        <textarea class="form-control interview-review-area" data-area="${area}" rows="4" placeholder="${state.lang === 'ar' ? 'كل سطر = نقطة متطلب' : 'Each line = one requirement item'}">${escapeHtml(items.join('\n'))}</textarea>
                    </div>
                `;
            }).join('')}
            <p class="chat-disclaimer">${escapeHtml(t.interview_next_step)}</p>
            <button id="interview-final-submit" class="btn btn-primary w-100 mt-4">
                <i class="fas fa-check-circle"></i>
                <span>${state.lang === 'ar' ? 'إرسال وإنهاء المقابلة' : 'Submit and finish interview'}</span>
            </button>
        </div>
    `;
    elements.modalOverlay.classList.remove('hidden');

    const submitBtn = document.getElementById('interview-final-submit');
    if (!submitBtn) return;

    submitBtn.onclick = async () => {
        setButtonLoading(submitBtn, true);
        try {
            const editedSummary = {};
            document.querySelectorAll('.interview-review-area').forEach((input) => {
                const area = input.dataset.area;
                const lines = String(input.value || '')
                    .split('\n')
                    .map((line) => line.trim())
                    .filter(Boolean);
                editedSummary[area] = lines;
            });

            state.previousSummary = editedSummary;
            await saveInterviewDraft(projectId);

            await api.post(`/projects/${projectId}/messages`, {
                messages: [
                    {
                        role: 'assistant',
                        content: state.lang === 'ar' ? 'تمت مراجعة الملخص النهائي واعتماده من المستخدم.' : 'Final interview summary reviewed and approved by user.',
                        metadata: { summary: editedSummary, stage: state.interviewStage || 'features' }
                    }
                ]
            });

            state.srsRefreshing = true;
            await api.post(`/projects/${projectId}/srs/refresh`, { language });
            state.srsRefreshing = false;

            await clearInterviewDraft(projectId);
            elements.modalOverlay.classList.add('hidden');
            state.selectedProject = { id: projectId };
            showNotification(state.lang === 'ar' ? 'تم الإرسال بنجاح.' : 'Submitted successfully.', 'success');
            setTimeout(() => switchView('srs'), 700);
        } catch (error) {
            state.srsRefreshing = false;
            console.error('Final interview submit failed:', error);
            showNotification(i18n[state.lang].error_generic, 'error');
        } finally {
            setButtonLoading(submitBtn, false);
        }
    };
}

/**
 * Finalize a bot message after streaming completes:
 * render final formatted text, attach sources and copy button.
 */
function finalizeBotMessage(id, text, sources) {
    const msgDiv = document.getElementById(`msg-${id}`);
    if (!msgDiv) return;

    const textEl = msgDiv.querySelector('.msg-text');
    textEl.classList.remove('streaming');
    textEl.innerHTML = formatAnswerHtml(text) || escapeHtml(text);
    textEl.dir = detectTextDirection(text);

    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'msg-sources-pro';
        sourcesDiv.innerHTML = `
            <div class="sources-header">
                <i class="fas fa-book-open"></i>
                <span>${state.lang === 'ar' ? 'المصادر المستخدمة' : 'Sources Used'}</span>
            </div>
        `;
        const list = document.createElement('ul');
        sources.slice(0, 5).forEach(s => {
            const li = document.createElement('li');
            const docName = s.document_name || s.name || '';
            const score = typeof s.similarity === 'number' ? `<span class="source-score">${(s.similarity * 100).toFixed(0)}%</span>` : '';
            li.innerHTML = `
                <i class="fas fa-file-alt"></i>
                <span>${escapeHtml(docName)}</span>
                ${score}
            `;
            list.appendChild(li);
        });
        sourcesDiv.appendChild(list);
        msgDiv.querySelector('.msg-body').appendChild(sourcesDiv);
    }

    // Copy button
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'msg-actions';
    actionsDiv.innerHTML = `
        <button class="msg-action-btn copy-msg-btn" title="${i18n[state.lang].copy_btn}">
            <i class="fas fa-copy"></i> ${i18n[state.lang].copy_btn}
        </button>
    `;
    actionsDiv.querySelector('.copy-msg-btn').onclick = () => {
        const plainText = textEl.innerText || textEl.textContent;
        navigator.clipboard.writeText(plainText).then(() => {
            const btn = actionsDiv.querySelector('.copy-msg-btn');
            btn.classList.add('copied');
            btn.innerHTML = `<i class="fas fa-check"></i> ${i18n[state.lang].copied_btn}`;
            setTimeout(() => {
                btn.classList.remove('copied');
                btn.innerHTML = `<i class="fas fa-copy"></i> ${i18n[state.lang].copy_btn}`;
            }, 2000);
        });
    };
    msgDiv.querySelector('.msg-body').appendChild(actionsDiv);

    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}

function addChatMessage(role, text, isThinking = false) {
    const messagesContainer = document.getElementById('chat-messages');
    const welcome = messagesContainer.querySelector('.welcome-msg-pro');
    if (welcome) welcome.remove();

    const id = `m${Date.now()}-${++_msgIdCounter}`;
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg-pro ${role}-msg-pro`;
    msgDiv.id = `msg-${id}`;
    
    const isUser = role === 'user';
    const userName = state.lang === 'ar' ? 'أنت' : 'You';
    const authorName = isUser ? userName : 'Tawasul';
    const thinkingStageLabel = state.lang === 'ar' ? 'يحلل إجابتك · يركز على' : 'Analyzing your answer · focusing on';
    const stageValue = i18n[state.lang]['stage_' + state.interviewStage] || state.interviewStage;
    const thinkingStageHtml = state.interviewMode && state.interviewStage
        ? `<div class="thinking-stage-label"><i class="fas fa-brain"></i> ${thinkingStageLabel} <strong>${stageValue}</strong></div>`
        : '';
    
    // Detect text direction
    const textDir = detectTextDirection(text);
    
    msgDiv.innerHTML = `
        <div class="msg-inner">
            <div class="msg-avatar-pro">
                ${isUser ? 'U' : '<i class="fas fa-robot"></i>'}
            </div>
            <div class="msg-body">
                <div class="msg-author">${authorName}</div>
                <div class="msg-text" dir="${textDir}">${isUser ? escapeHtml(text) : ''}</div>
                ${isThinking ? `<div class="typing-indicator-pro"><span></span><span></span><span></span></div>${thinkingStageHtml}` : ''}
            </div>
        </div>
    `;
    
    if (!isUser && !isThinking) {
        const msgText = msgDiv.querySelector('.msg-text');
        msgText.innerHTML = formatAnswerHtml(text) || escapeHtml(text);
        msgText.dir = textDir;
    }
    
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return id;
}

function escapeHtml(value) {
    if (value == null) return '';
    return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function detectTextDirection(text) {
    if (!text) return 'auto';
    // Check for Arabic/Hebrew/Persian characters
    const rtlChars = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0590-\u05FF]/;
    const firstChars = text.trim().substring(0, 50);
    return rtlChars.test(firstChars) ? 'rtl' : 'ltr';
}

function deepCloneValue(value) {
    if (value == null || typeof value !== 'object') {
        return value;
    }
    if (Array.isArray(value)) {
        return value.map(item => deepCloneValue(item));
    }
    const cloned = {};
    Object.keys(value).forEach((key) => {
        cloned[key] = deepCloneValue(value[key]);
    });
    return cloned;
}

function formatAnswerHtml(text) {
    if (!text) return '';

    let cleaned = String(text).replaceAll('\r\n', '\n').trim();
    cleaned = cleaned.replaceAll(/\s*(Source|Sources|المصدر|المصادر)\s*:.*/gi, '').trim();
    cleaned = cleaned.replaceAll(/\s+\*\s+/g, '\n* ');
    cleaned = cleaned.replaceAll(/\s+-\s+/g, '\n- ');
    if (!cleaned.includes('\n') && cleaned.length > 220) {
        cleaned = cleaned.replaceAll(/([.!؟?])\s+(?=[^\n])/g, '$1\n');
    }

    const lines = cleaned.split('\n').map(line => line.trim()).filter(Boolean);
    if (lines.length === 0) return '';

    const parts = [];
    let bulletBuffer = [];
    let numberedBuffer = [];

    const isHeadingLine = (line) => {
        if (!line) return false;
        if (/^#{1,4}\s+/.test(line)) return true;
        if (/^(العنوان|ملخص|Summary|Overview|Key Points|النقاط الرئيسية)\s*[:：]?$/i.test(line)) return true;
        return /^\*\*[^*]{3,}\*\*\s*:?$/.test(line);
    };

    const isQuestionLine = (line) => /[؟?]\s*$/.test(line);
    const isNoteLine = (line) => /^(note|important|tip|warning|ملاحظة|تنبيه|مهم)\s*[:-]/i.test(line);

    const flushBullets = () => {
        if (bulletBuffer.length === 0) return;
        const items = bulletBuffer
            .map(item => `<li>${formatInlineMarkdown(item)}</li>`)
            .join('');
        parts.push(`<ul class="answer-list-plain">${items}</ul>`);
        bulletBuffer = [];
    };

    const flushNumbered = () => {
        if (numberedBuffer.length === 0) return;
        const items = numberedBuffer
            .map(item => `<li>${formatInlineMarkdown(item)}</li>`)
            .join('');
        parts.push(`<ol class="answer-ordered-list-plain">${items}</ol>`);
        numberedBuffer = [];
    };

    lines.forEach(line => {
        if (/^\d+[).-]\s+/.test(line)) {
            flushBullets();
            numberedBuffer.push(line.replace(/^\d+[).-]\s+/, ''));
            return;
        }

        if (/^[*-]\s+/.test(line)) {
            flushNumbered();
            bulletBuffer.push(line.replace(/^[*-]\s+/, ''));
            return;
        }

        flushBullets();
        flushNumbered();

        if (isHeadingLine(line)) {
            const headingText = line.replace(/^#{1,4}\s+/, '').replace(/^\*\*(.+)\*\*\s*:?$/, '$1');
            parts.push(`<h4 class="answer-heading-line">${formatInlineMarkdown(headingText)}</h4>`);
            return;
        }

        if (isNoteLine(line)) {
            parts.push(`<p class="answer-note-line">${formatInlineMarkdown(line)}</p>`);
            return;
        }

        if (isQuestionLine(line)) {
            parts.push(`<p class="answer-question-line">${formatInlineMarkdown(line)}</p>`);
            return;
        }

        parts.push(`<p class="answer-line">${formatInlineMarkdown(line)}</p>`);
    });

    flushBullets();
    flushNumbered();
    return parts.join('');
}

function formatInlineMarkdown(value) {
    const escaped = escapeHtml(value);
    return escaped
    .replaceAll(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replaceAll(/`([^`]+)`/g, '<code>$1</code>');
}

let _resizeRafId = null;
function autoResizeTextarea(textarea) {
    if (_resizeRafId) cancelAnimationFrame(_resizeRafId);
    _resizeRafId = requestAnimationFrame(() => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
        _resizeRafId = null;
    });
}

// --- Animated Counter ---
function animateCounter(elementId, target) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const duration = 600;
    const start = performance.now();
    const from = 0;

    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // ease-out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(from + (target - from) * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}

// --- Empty State ---
function createEmptyState(icon, titleKey, descKey) {
    const t = i18n[state.lang];
    return `
        <div class="empty-state">
            <div class="empty-state-icon"><i class="fas ${icon}"></i></div>
            <h3>${t[titleKey] || ''}</h3>
            <p>${t[descKey] || ''}</p>
        </div>
    `;
}

// --- Search ---
function handleSearch(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
        // Restore current view
        switchView(state.currentView, state.selectedProject ? state.selectedProject.id : null);
        return;
    }
    const filtered = state.projects.filter(p =>
        p.name?.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q)
    );
    // Render inline results in current view container
    const list = document.getElementById('all-projects-list') || document.getElementById('recent-projects-list-dashboard');
    if (list) {
        list.innerHTML = '';
        if (filtered.length === 0) {
            list.innerHTML = createEmptyState('fa-search', 'empty_projects', 'empty_projects_desc');
        } else {
            filtered.forEach(p => list.appendChild(createProjectCard(p)));
        }
    }
}

// --- Mobile Sidebar ---
function openMobileSidebar() {
    document.querySelector('.sidebar').classList.add('open');
    const overlay = document.getElementById('sidebar-overlay');
    overlay.style.display = 'block';
    requestAnimationFrame(() => overlay.classList.add('active'));
    const hamburger = document.getElementById('mobile-hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'true');
}

function closeMobileSidebar() {
    document.querySelector('.sidebar').classList.remove('open');
    const overlay = document.getElementById('sidebar-overlay');
    overlay.classList.remove('active');
    setTimeout(() => { overlay.style.display = 'none'; }, 300);
    const hamburger = document.getElementById('mobile-hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
}

function setupUploadZone(projectId) {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');

    zone.onclick = () => input.click();

    zone.ondragover = (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    };

    zone.ondragleave = () => zone.classList.remove('dragover');

    zone.ondrop = (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files, projectId);
    };

    input.onchange = () => handleFiles(input.files, projectId);
}

async function handleFiles(files, projectId) {
    const unsupportedTypeText = state.lang === 'ar'
        ? 'نوع الملف غير مدعوم. الملفات المدعومة: PDF, TXT, DOCX'
        : 'Unsupported file type. Supported: PDF, TXT, DOCX';
    let uploadedAny = false;
    for (const file of files) {
        if (!isSupportedUploadFile(file)) {
            showNotification(unsupportedTypeText, 'warning');
            continue;
        }
        const uploadSucceeded = await uploadSingleFile(projectId, file);
        uploadedAny = uploadedAny || uploadSucceeded;
    }

    if (uploadedAny) {
        await refreshDocumentsAfterUpload(projectId);
    }
}

function isSupportedUploadFile(file) {
    const lowerName = file.name.toLowerCase();
    return lowerName.endsWith('.pdf') || lowerName.endsWith('.txt') || lowerName.endsWith('.docx');
}

async function uploadSingleFile(projectId, file) {
    const lowerName = file.name.toLowerCase();
    showNotification(`${state.lang === 'ar' ? 'جاري رفع' : 'Uploading'} ${file.name}...`, 'info');

    try {
        const presign = await api.post(`/projects/${projectId}/documents/presign`, {
            filename: file.name,
            file_size: file.size,
            content_type: file.type || 'application/octet-stream',
        });

        const uploadResp = await fetch(presign.upload_url, {
            method: 'PUT',
            headers: {
                'Content-Type': presign.content_type || file.type || 'application/octet-stream',
            },
            body: file,
        });
        if (!uploadResp.ok) {
            throw new Error(state.lang === 'ar' ? 'فشل الرفع إلى التخزين السحابي' : 'Failed uploading to object storage');
        }

        await api.post(`/projects/${projectId}/documents/complete`, {
            unique_filename: presign.unique_filename,
            original_filename: file.name,
            file_key: presign.file_key,
            file_size: file.size,
            file_type: lowerName.split('.').pop() || '',
        });
        showNotification(`${state.lang === 'ar' ? 'تم رفع' : 'Uploaded'} ${file.name}`, 'success');
        return true;
    } catch (error) {
        console.error('Upload Error:', error);
        return false;
    }
}

async function refreshDocumentsAfterUpload(projectId) {
    try {
        const docs = await api.get(`/projects/${projectId}/documents`);
        renderDocsList(docs);
        startDocPolling(projectId, docs);
    } catch (error) {
        console.error('Documents refresh after upload failed:', error);
        const refreshError = state.lang === 'ar'
            ? 'تم الرفع ولكن تعذر تحديث قائمة الملفات'
            : 'Upload succeeded but document list refresh failed';
        showNotification(error?.message || refreshError, 'warning');
    }
}

// --- Upload Modal (from chat) ---

function openUploadModal(projectId) {
    const t = i18n[state.lang];
    elements.modalTitle.textContent = t.upload_reference_docs || (state.lang === 'ar' ? 'رفع مستندات مرجعية' : 'Upload Reference Documents');
    elements.modalBody.innerHTML = `
        <p class="config-desc">${state.lang === 'ar'
            ? 'ارفع مستندات مرجعية لمساعدة الذكاء الاصطناعي في فهم مشروعك بشكل أفضل. هذه الخطوة اختيارية.'
            : 'Upload reference documents to help the AI better understand your project. This step is optional.'}</p>
        <div class="upload-zone" id="modal-upload-zone">
            <i class="fas fa-cloud-upload-alt"></i>
            <p>${t.upload_desc}</p>
            <span class="hint">${state.lang === 'ar' ? 'يدعم PDF, TXT, DOCX' : 'Supports PDF, TXT, DOCX'}</span>
            <input type="file" id="modal-file-input" multiple hidden accept=".pdf,.txt,.docx">
        </div>
    `;

    elements.modalOverlay.classList.remove('hidden');

    const zone = document.getElementById('modal-upload-zone');
    const input = document.getElementById('modal-file-input');

    zone.onclick = () => input.click();

    zone.ondragover = (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    };

    zone.ondragleave = () => zone.classList.remove('dragover');

    zone.ondrop = (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files, projectId);
    };

    input.onchange = () => handleFiles(input.files, projectId);
}

// --- Booking Modal ---

function openBookingModal() {
    const t = i18n[state.lang];
    elements.modalTitle.textContent = t.book_meeting_title;
    elements.modalBody.innerHTML = `
        <div class="booking-form">
            <div class="form-group">
                <label>${t.book_name} *</label>
                <input type="text" id="book-name" class="form-control" required>
            </div>
            <div class="form-group">
                <label>${t.book_email} *</label>
                <input type="email" id="book-email" class="form-control" required>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>${t.book_date} *</label>
                    <input type="date" id="book-date" class="form-control" min="${new Date().toISOString().split('T')[0]}" required>
                </div>
                <div class="form-group">
                    <label>${t.book_time} *</label>
                    <select id="book-time" class="form-control">
                        <option value="09:00">09:00 AM</option>
                        <option value="10:00">10:00 AM</option>
                        <option value="11:00">11:00 AM</option>
                        <option value="12:00">12:00 PM</option>
                        <option value="13:00">01:00 PM</option>
                        <option value="14:00">02:00 PM</option>
                        <option value="15:00">03:00 PM</option>
                        <option value="16:00">04:00 PM</option>
                        <option value="17:00">05:00 PM</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>${t.book_notes}</label>
                <textarea id="book-notes" class="form-control" rows="3"></textarea>
            </div>
            <button id="book-submit-btn" class="btn btn-primary w-100 mt-4">
                <i class="fas fa-calendar-check"></i> ${t.book_submit}
            </button>
        </div>
    `;

    elements.modalOverlay.classList.remove('hidden');

    document.getElementById('book-submit-btn').onclick = async () => {
        const name = document.getElementById('book-name').value.trim();
        const email = document.getElementById('book-email').value.trim();
        const date = document.getElementById('book-date').value;
        const time = document.getElementById('book-time').value;
        const notes = document.getElementById('book-notes').value.trim();

        if (!name || !email || !date) {
            showNotification(t.book_fill_required, 'warning');
            return;
        }

        const submitBtn = document.getElementById('book-submit-btn');
        submitBtn.disabled = true;

        try {
            const projectId = state.selectedProject ? state.selectedProject.id : null;
            if (projectId) {
                await api.post(`/projects/${projectId}/handoff`, {
                    client_name: name,
                    client_email: email,
                    preferred_date: date,
                    preferred_time: time,
                    notes
                });
            }
            showNotification(t.book_success, 'success');
            elements.modalOverlay.classList.add('hidden');
        } catch (error) {
            console.error('Booking Error:', error);
        } finally {
            submitBtn.disabled = false;
        }
    };
}

// --- Voice Recording (STT) ---

async function startRecording() {
    if (navigator.mediaDevices?.getUserMedia == null) {
        showNotification(i18n[state.lang].mic_no_support, 'warning');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        const chunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(track => track.stop());
            const blob = new Blob(chunks, { type: 'audio/webm' });
            await transcribeAudio(blob);
        };

        state.mediaRecorder = mediaRecorder;
        state.isRecording = true;
        mediaRecorder.start();
        updateMicButton(true);
        showNotification(i18n[state.lang].mic_recording, 'info');
    } catch (error) {
        console.error('Mic access error:', error);
        showNotification(i18n[state.lang].mic_error, 'error');
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.isRecording) {
        state.mediaRecorder.stop();
        state.isRecording = false;
        updateMicButton(false);
    }
}

async function transcribeAudio(blob) {
    const micBtn = document.getElementById('mic-btn');
    if (micBtn) {
        micBtn.disabled = true;
        micBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    try {
        const language = state.lang === 'ar' ? 'ar' : 'en';

        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');
        formData.append('language', language);

        const response = await fetch(`${API_BASE_URL}/stt/transcribe`, {
            method: 'POST',
            headers: authHeaders(),
            body: formData
        });

        await throwIfNotOk(response, 'Transcription failed');

        const result = await response.json();
        if (result.success && result.text) {
            await applyTranscriptResult(result);
        }
    } catch (error) {
        console.error('STT Error:', error);
        showNotification(error.message, 'error');
    } finally {
        if (micBtn) {
            micBtn.disabled = false;
            micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    }
}

function getUnavailableConfidenceText() {
    return state.lang === 'ar' ? 'غير متاح' : 'N/A';
}

function buildTranscriptConfirmationText(resultText, confidencePct, warningSuffix) {
    if (state.lang === 'ar') {
        return `مراجعة نص التفريغ قبل اعتماده:\n\n${resultText}\n\nدرجة الثقة: ${confidencePct}${warningSuffix}\n\nهل تؤكد هذا النص؟`;
    }
    return `Please review the transcript before using it:\n\n${resultText}\n\nConfidence: ${confidencePct}${warningSuffix}\n\nDo you confirm this text?`;
}

function applyTranscriptToInput(text) {
    const chatInput = document.getElementById('chat-input');
    if (!chatInput) return;
    chatInput.value += (chatInput.value ? ' ' : '') + text;
    chatInput.oninput();
    chatInput.focus();
}

function notifyTranscriptReviewState(requiresConfirmation, warningList) {
    if (!(requiresConfirmation || warningList.length > 0)) return;
    showNotification(
        state.lang === 'ar'
            ? 'تم اعتماد النص بعد مراجعة بشرية. يُرجى التحقق من المصطلحات الحساسة.'
            : 'Transcript confirmed by human review. Please re-check sensitive terms.',
        'info'
    );
}

async function applyTranscriptResult(result) {
    const confidence = Number.isFinite(result.confidence) ? result.confidence : null;
    const warningList = Array.isArray(result.quality_warnings) ? result.quality_warnings : [];
    const confidencePct = confidence == null ? getUnavailableConfidenceText() : `${Math.round(confidence * 100)}%`;
    const warningSuffix = warningList.length ? `\n\n${warningList.slice(0, 2).join('\n')}` : '';
    const confirmText = buildTranscriptConfirmationText(result.text, confidencePct, warningSuffix);
    const confirmed = globalThis.confirm(confirmText);

    if (!confirmed) {
        showNotification(state.lang === 'ar' ? 'تم إلغاء إدراج التفريغ الصوتي' : 'Transcript insertion cancelled', 'warning');
        return;
    }

    state.pendingSttMeta = {
        source: 'stt',
        transcript_confirmed: true,
        stt_confidence: confidence,
        quality_warnings: warningList,
    };

    applyTranscriptToInput(result.text);
    notifyTranscriptReviewState(result.requires_confirmation, warningList);
}

function updateMicButton(recording) {
    const micBtn = document.getElementById('mic-btn');
    if (!micBtn) return;
    if (recording) {
        micBtn.classList.add('recording');
        micBtn.innerHTML = '<i class="fas fa-stop"></i>';
    } else {
        micBtn.classList.remove('recording');
        micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
}

// --- Interview Progress ---

function updateInterviewProgress(coverage, done, topicNavigation = null) {
    const progressBar = document.getElementById('interview-progress');
    const liveDocPanel = document.getElementById('live-doc-panel');
    const assistBar = document.getElementById('interview-assist-bar');

    if (!state.interviewMode || done) {
        if (progressBar) progressBar.style.display = 'none';
        if (liveDocPanel) liveDocPanel.style.display = 'none';
        if (assistBar) assistBar.style.display = 'none';
        return;
    }

    if (progressBar) {
        progressBar.style.display = 'block';
        const areas = INTERVIEW_AREAS;
        const stageLabels = {
            discovery: i18n[state.lang].stage_discovery,
            scope: i18n[state.lang].stage_scope,
            users: i18n[state.lang].stage_users,
            features: i18n[state.lang].stage_features,
            constraints: i18n[state.lang].stage_constraints
        };
        const activeArea = getActiveCoverageArea(coverage, areas);

        areas.forEach((area, index) => {
            const pct = coverage ? (coverage[area] || 0) : 0;
            updateCoverageProgressItem(progressBar, area, index, pct, stageLabels, activeArea);
        });
    }

    if (liveDocPanel) {
        applySummaryDrawerState();
    }

    if (assistBar) {
        assistBar.style.display = 'block';
    }
}

function getActiveCoverageArea(coverage, areas) {
    if (!coverage) return null;
    let minCoverage = Infinity;
    let activeArea = null;
    for (const area of areas) {
        const pct = coverage[area] || 0;
        if (pct < 70 && pct < minCoverage) {
            minCoverage = pct;
            activeArea = area;
        }
    }
    return activeArea;
}

function updateCoverageProgressItem(progressBar, area, index, pct, stageLabels, activeArea) {
    const fillEl = document.getElementById(`coverage-${area}`);
    const pctEl = document.getElementById(`coverage-pct-${area}`);
    const itemEl = progressBar.querySelector(`[data-area="${area}"]`);
    const roundedPct = Math.round(pct);

    if (fillEl) {
        fillEl.textContent = String(index + 1);
        fillEl.dataset.pct = `${roundedPct}%`;
        fillEl.setAttribute('aria-label', `${stageLabels[area] || area} ${roundedPct}%`);
    }
    if (pctEl) pctEl.textContent = `${roundedPct}%`;

    if (!itemEl) return;
    itemEl.classList.remove('active-area', 'complete-area');
    if (pct >= 70) {
        itemEl.classList.add('complete-area');
    } else if (area === activeArea) {
        itemEl.classList.add('active-area');
    }
    itemEl.title = `${stageLabels[area] || area} ${roundedPct}%`;
}

function updateLiveDoc(summary, stage) {
    const content = document.getElementById('live-doc-content');
    if (!content || !summary) return;

    const areaIcons = {
        discovery: 'fa-compass',
        scope: 'fa-bullseye',
        users: 'fa-users',
        features: 'fa-puzzle-piece',
        constraints: 'fa-shield-halved'
    };

    const stageLabels = {
        discovery: i18n[state.lang].stage_discovery,
        scope: i18n[state.lang].stage_scope,
        users: i18n[state.lang].stage_users,
        features: i18n[state.lang].stage_features,
        constraints: i18n[state.lang].stage_constraints
    };

    if (isStructuredSummary(summary)) {
        renderStructuredLiveDoc(content, summary, areaIcons, stageLabels);
        return;
    }

    renderLegacyLiveDoc(content, summary, stageLabels, stage);
}

function isStructuredSummary(summary) {
    return typeof summary === 'object' && !Array.isArray(summary);
}

function renderStructuredLiveDoc(content, summary, areaIcons, stageLabels) {
    const model = buildLiveDocRenderModel(summary);
    const htmlParts = [];

    const alertsHtml = buildLiveDocAlertsHtml(model.alerts);
    if (alertsHtml) htmlParts.push(alertsHtml);

    const planHtml = buildLiveDocPlanHtml(model.plan);
    if (planHtml) htmlParts.push(planHtml);

    const traceHtml = buildLiveDocTraceHtml(model.trace);
    if (traceHtml) htmlParts.push(traceHtml);

    const removedHtml = buildLiveDocRemovedHtml(model.removedEvents);
    if (removedHtml) htmlParts.push(removedHtml);

    htmlParts.push(buildLiveDocSectionsHtml(summary, model, areaIcons, stageLabels));

    content.innerHTML = htmlParts.join('') || `
        <div class="live-doc-empty">
            <i class="fas fa-pencil-alt"></i>
            <p>${i18n[state.lang].live_doc_empty}</p>
        </div>
    `;

    state.previousSummary = deepCloneValue(summary);
    scrollToLatestLiveDocItem(content);
}

function buildLiveDocRenderModel(summary) {
    const patch = state.lastLivePatch || null;
    const patchEvents = Array.isArray(patch?.events) ? patch.events : [];
    return {
        prevSummary: state.previousSummary || {},
        focusArea: patch?.focus_area || null,
        patchMap: new Map((patch?.changed_areas || []).map((item) => [item.area, item])),
        eventMap: new Map(patchEvents.map((event) => [String(event?.field_path || ''), String(event?.op || '')])),
        removedEvents: patchEvents.filter((event) => String(event?.op || '') === 'removed'),
        alerts: Array.isArray(patch?.alerts) ? patch.alerts : [],
        plan: patch?.next_plan || null,
        trace: state.lastCycleTrace || null,
        summary,
    };
}

function buildLiveDocAlertsHtml(alerts) {
    if (!alerts.length) return '';
    return `
        <div class="live-doc-alerts">
            ${alerts.map((alert) => {
                const severity = String(alert?.severity || 'info');
                const title = escapeHtml(String(alert?.title || 'Alert'));
                const msg = escapeHtml(String(alert?.message || ''));
                return `
                    <div class="live-doc-alert live-doc-alert-${severity}">
                        <div class="live-doc-alert-title">${title}</div>
                        <div class="live-doc-alert-text">${msg}</div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function buildLiveDocPlanHtml(plan) {
    if (!(plan?.target_stage || plan?.question_style)) return '';
    const stageKey = plan?.target_stage ? `stage_${plan.target_stage}` : '';
    const stageLabel = stageKey ? (i18n[state.lang][stageKey] || plan.target_stage) : '';
    const styleText = escapeHtml(String(plan?.question_style || ''));
    const hintText = escapeHtml(String(plan?.prompt_hint || ''));
    return `
        <div class="live-doc-plan">
            <div class="live-doc-plan-row"><strong>${state.lang === 'ar' ? 'التركيز القادم:' : 'Next focus:'}</strong> ${escapeHtml(stageLabel)}</div>
            <div class="live-doc-plan-row"><strong>${state.lang === 'ar' ? 'نمط السؤال:' : 'Question style:'}</strong> ${styleText}</div>
            ${hintText ? `<div class="live-doc-plan-row">${hintText}</div>` : ''}
        </div>
    `;
}

function buildLiveDocTraceHtml(trace) {
    if (!(trace?.steps && Array.isArray(trace.steps))) return '';
    const scoreCoverage = Number(trace?.score?.coverage || 0);
    const scoreConfidence = Number(trace?.score?.confidence || 0);
    const riskLevel = escapeHtml(String(trace?.score?.risk_level || 'low'));
    return `
        <div class="live-doc-trace">
            <div class="live-doc-trace-head">
                <strong>${state.lang === 'ar' ? 'دورة التفكير' : 'Cognitive loop'}</strong>
                <span>${state.lang === 'ar' ? 'تغطية' : 'Coverage'}: ${Math.round(scoreCoverage)}%</span>
                <span>${state.lang === 'ar' ? 'ثقة' : 'Confidence'}: ${Math.round(scoreConfidence * 100)}%</span>
                <span>${state.lang === 'ar' ? 'مخاطرة' : 'Risk'}: ${riskLevel}</span>
            </div>
            <div class="live-doc-trace-steps">
                ${trace.steps.map((step, idx) => {
                    const name = escapeHtml(String(step?.name || `step-${idx + 1}`));
                    const text = escapeHtml(String(step?.summary || ''));
                    return `
                        <div class="live-doc-trace-step">
                            <div class="live-doc-trace-step-name">${idx + 1}. ${name}</div>
                            <div class="live-doc-trace-step-text">${text}</div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

function buildLiveDocRemovedHtml(removedEvents) {
    if (!removedEvents.length) return '';
    return `
        <div class="live-doc-plan">
            <div class="live-doc-plan-row"><strong>${state.lang === 'ar' ? 'حقول تمت إزالتها:' : 'Removed fields:'}</strong></div>
            ${removedEvents.slice(0, 5).map((event) => {
                const path = escapeHtml(String(event?.field_path || ''));
                const value = escapeHtml(String(event?.value || ''));
                return `<div class="live-doc-plan-row live-doc-removed-item">${path}: ${value}</div>`;
            }).join('')}
        </div>
    `;
}

function buildLiveDocSectionsHtml(summary, model, areaIcons, stageLabels) {
    let html = '';
    for (const [area, items] of Object.entries(summary)) {
        if (!Array.isArray(items) || items.length === 0) continue;
        html += buildLiveDocAreaHtml(area, items, model, areaIcons, stageLabels);
    }
    return html;
}

function buildLiveDocAreaHtml(area, items, model, areaIcons, stageLabels) {
    const prevItems = model.prevSummary[area] || [];
    const icon = areaIcons[area] || 'fa-circle-dot';
    const label = stageLabels[area] || area;
    const isFocus = model.focusArea && model.focusArea === area;
    const areaPatch = model.patchMap.get(area);
    const delta = Number(areaPatch?.coverage_delta || 0);

    return `
        <div class="live-doc-srs-section ${isFocus ? 'live-doc-focus-area' : ''}">
            <div class="live-doc-section-header">
                <i class="fas ${icon}"></i>
                <span>${escapeHtml(label)}</span>
                <span class="live-doc-count-badge">${items.length}</span>
                ${delta > 0 ? `<span class="live-doc-delta-badge">+${Math.round(delta)}%</span>` : ''}
            </div>
            <ul class="live-doc-items">
                ${items.map((item, idx) => buildLiveDocItemHtml(area, idx, item, prevItems, model.eventMap)).join('')}
            </ul>
        </div>
    `;
}

function buildLiveDocItemHtml(area, idx, item, prevItems, eventMap) {
    // Items from the interview service are {id, value} objects; fall back to plain string.
    const text = (typeof item === 'object' && item !== null)
        ? String(item.value || '')
        : String(item ?? '');
    const itemId = (typeof item === 'object' && item !== null) ? String(item.id || '') : '';
    const isNew = !prevItems.some((p) => {
        if (typeof p === 'object' && p !== null) {
            return (itemId && p.id === itemId) || p.value === text;
        }
        return String(p) === text;
    });
    const fieldPath = `${area}.${idx}`;
    const op = eventMap.get(fieldPath);
    const updatedClass = op === 'updated' ? 'live-doc-updated-item' : '';
    const addedClass = op === 'added' ? 'live-doc-new-item' : '';
    return `<li class="${isNew ? 'live-doc-new-item' : ''} ${addedClass} ${updatedClass}">${escapeHtml(text)}</li>`;
}

function scrollToLatestLiveDocItem(content) {
    const newItems = content.querySelectorAll('.live-doc-new-item');
    if (newItems.length > 0) {
        newItems[newItems.length - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function renderLegacyLiveDoc(content, summary, stageLabels, stage) {
    const stageLabel = stageLabels[stage] || stage;
    content.innerHTML = `
        <div class="live-doc-section">
            <div class="live-doc-stage-badge">
                <i class="fas fa-circle-dot"></i> ${escapeHtml(stageLabel)}
            </div>
            <div class="live-doc-text" dir="${detectTextDirection(String(summary))}">${formatAnswerHtml(String(summary)) || escapeHtml(String(summary))}</div>
        </div>
    `;
}

// --- Authentication ---

async function autoLogin() {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: 'admin@tawasul.com', password: 'admin123' })
        });
        await throwIfNotOk(res, 'Login failed');
        if (res.ok) {
            const data = await res.json();
            setAuthState(data.token, data.user);
            showApp();
            return;
        }
    } catch (e) {
        console.warn('Auto-login unavailable; showing auth screen.', e);
    }
    showAuthScreen();
}

function showAuthScreen() {
    document.getElementById('auth-screen').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';

    // Tab switching
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const isLogin = tab.dataset.tab === 'login';
            document.getElementById('login-form').style.display = isLogin ? 'block' : 'none';
            document.getElementById('register-form').style.display = isLogin ? 'none' : 'block';
            document.getElementById('auth-error').style.display = 'none';
        };
    });

    // Setup field validation for login
    const loginEmailInput = document.getElementById('login-email');
    const loginPasswordInput = document.getElementById('login-password');
    if (loginEmailInput) {
        setupFieldValidation(loginEmailInput, (v) => {
            if (!v.trim()) return i18n[state.lang].validation_required;
            return null;
        });
    }
    if (loginPasswordInput) {
        setupFieldValidation(loginPasswordInput, (v) => {
            if (!v) return i18n[state.lang].validation_required;
            return null;
        });
    }

    // Setup field validation for register
    const regNameInput = document.getElementById('register-name');
    const regEmailInput = document.getElementById('register-email');
    const regPasswordInput = document.getElementById('register-password');
    if (regNameInput) {
        setupFieldValidation(regNameInput, (v) => {
            if (!v.trim()) return i18n[state.lang].validation_required;
            return null;
        });
    }
    if (regEmailInput) {
        setupFieldValidation(regEmailInput, (v) => {
            if (!v.trim()) return i18n[state.lang].validation_required;
            if (!isValidEmail(v)) return i18n[state.lang].validation_email_invalid;
            return null;
        });
    }
    if (regPasswordInput) {
        setupFieldValidation(regPasswordInput, (v) => {
            if (!v) return i18n[state.lang].validation_required;
            if (v.length < 6) return i18n[state.lang].validation_password_min;
            return null;
        });
    }

    // Login
    document.getElementById('login-form').onsubmit = async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('auth-error');
        errorEl.style.display = 'none';

        // Validate fields
        if (!email) {
            showFieldError(document.getElementById('login-email'), i18n[state.lang].validation_required);
            return;
        }
        if (!password) {
            showFieldError(document.getElementById('login-password'), i18n[state.lang].validation_required);
            return;
        }

        const submitBtn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn, true);
        try {
            const res = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            await throwIfNotOk(res, 'Login failed');
            const data = await res.json();
            setAuthState(data.token, data.user);
            showApp();
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
        } finally {
            setButtonLoading(submitBtn, false);
        }
    };

    // Register
    document.getElementById('register-form').onsubmit = async (e) => {
        e.preventDefault();
        const name = document.getElementById('register-name').value.trim();
        const email = document.getElementById('register-email').value.trim();
        const password = document.getElementById('register-password').value;
        const errorEl = document.getElementById('auth-error');
        errorEl.style.display = 'none';

        // Validate fields
        if (!name) {
            showFieldError(document.getElementById('register-name'), i18n[state.lang].validation_required);
            return;
        }
        if (!email || !isValidEmail(email)) {
            showFieldError(document.getElementById('register-email'), i18n[state.lang].validation_email_invalid);
            return;
        }
        if (!password || password.length < 6) {
            showFieldError(document.getElementById('register-password'), i18n[state.lang].validation_password_min);
            return;
        }

        const submitBtn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn, true);
        try {
            const res = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });
            await throwIfNotOk(res, 'Registration failed');
            const data = await res.json();
            setAuthState(data.token, data.user);
            showApp();
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
        } finally {
            setButtonLoading(submitBtn, false);
        }
    };
}

function setAuthState(token, user) {
    state.authToken = token;
    state.currentUser = user;
    safeStorageSet('authToken', token);
    safeStorageSet('currentUser', JSON.stringify(user));
}

function clearAuthState() {
    state.authToken = null;
    state.currentUser = null;
    safeStorageRemove('authToken');
    safeStorageRemove('currentUser');
}

function showApp() {
    document.getElementById('auth-screen').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';

    // Update sidebar user info
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    if (state.currentUser) {
        if (avatarEl) avatarEl.textContent = state.currentUser.name.charAt(0).toUpperCase();
        if (nameEl) nameEl.textContent = state.currentUser.name;
    }

    applyRoleBasedNavigation();

    // Logout handler
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            clearAuthState();
            showAuthScreen();
        };
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    // Check authentication
    if (state.authToken && state.currentUser) {
        showApp();
        // Validate token with a lightweight API call
        api.get('/stats/').catch(() => {
            // Token invalid/expired - redirect to login
            clearAuthState();
            autoLogin();
        });
    } else {
        autoLogin();
    }

    // Nav Clicks
    elements.navItems.forEach(item => {
        item.onclick = () => {
            if (!item.dataset.view) return;
            closeMobileSidebar();
            switchView(item.dataset.view);
        };
    });

    // New Project Click
    elements.newProjectBtn.onclick = handleNewProject;

    // Close Modal
    elements.closeModalBtn.onclick = () => elements.modalOverlay.classList.add('hidden');
    elements.modalOverlay.onclick = (e) => {
        if (e.target === elements.modalOverlay) elements.modalOverlay.classList.add('hidden');
    };

    // Theme & Lang
    elements.themeToggle.onclick = toggleTheme;
    elements.langToggle.onclick = toggleLang;

    // Search Bar
    const searchInput = document.querySelector('.search-bar input');
    let searchTimeout;
    if (searchInput) {
        searchInput.oninput = () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => handleSearch(searchInput.value), 300);
        };
        searchInput.onkeydown = (e) => {
            if (e.key === 'Escape') {
                searchInput.value = '';
                handleSearch('');
                searchInput.blur();
            }
        };
    }

    // Mobile Hamburger
    const hamburger = document.getElementById('mobile-hamburger');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    if (hamburger) hamburger.onclick = openMobileSidebar;
    if (sidebarOverlay) sidebarOverlay.onclick = closeMobileSidebar;

    if (elements.sidebarToggleBtn) {
        elements.sidebarToggleBtn.onclick = toggleSidebarCollapsed;
    }

    // Keyboard Shortcut: Ctrl+K to focus search
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (searchInput) searchInput.focus();
        }
    });

    // Global Escape handler: close modal → close mobile sidebar
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!elements.modalOverlay.classList.contains('hidden')) {
                elements.modalOverlay.classList.add('hidden');
                return;
            }
            const confirmOverlay = document.getElementById('confirm-overlay');
            if (confirmOverlay && !confirmOverlay.classList.contains('hidden')) {
                return; // handled by showConfirmDialog's own handler
            }
            if (document.querySelector('.sidebar.open')) {
                closeMobileSidebar();
            }
        }
    });

    // Sidebar keyboard navigation: Enter/Space triggers switchView
    elements.navItems.forEach(item => {
        item.onkeydown = (e) => {
            if (!item.dataset.view) return;
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                closeMobileSidebar();
                switchView(item.dataset.view);
            }
        };
    });

    // Offline detection
    const offlineBanner = document.getElementById('offline-banner');
    if (offlineBanner) {
        const updateOnlineStatus = () => {
            if (navigator.onLine) {
                offlineBanner.classList.remove('visible');
                return;
            }
            offlineBanner.classList.add('visible');
        };
        globalThis.addEventListener('online', updateOnlineStatus);
        globalThis.addEventListener('offline', updateOnlineStatus);
        updateOnlineStatus();
    }

    // Init State
    if (state.theme === 'light') {
        document.body.classList.add('light-theme');
        document.body.classList.remove('dark-theme');
        elements.themeToggle.querySelector('i').className = 'fas fa-moon';
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        elements.themeToggle.querySelector('i').className = 'fas fa-sun';
    }

    applySidebarCollapsedState();

    // Initial View
    applyTranslations();
    switchView('projects');
});
