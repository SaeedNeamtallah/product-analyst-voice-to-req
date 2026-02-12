/**
 * RAGMind Web Frontend
 * Main Application Logic
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000';

// Translations
const i18n = {
    ar: {
        nav_dashboard: "لوحة التحكم",
        nav_projects: "المشاريع",
        nav_chat: "المحادثة الذكية",
        interview_mode: "وضع المقابلة",
        nav_srs: "مراجعة المتطلبات",
        nav_bot: "إعدادات البوت",
        nav_ai_config: "إعدادات الذكاء الاصطناعي",
        stat_projects: "إجمالي المشاريع",
        stat_docs: "المستندات",
        stat_chunks: "القطع النصية",
        recent_projects: "المشاريع الأخيرة",
        view_all: "عرض الكل",
        your_projects: "مشاريعك",
        welcome_title: "مرحباً بك في RAGMind",
        project_name_ph: "مثلاً: أبحاث الذكاء الاصطناعي",
        project_desc_ph: "وصف مختصر للمشروع...",
        create_project_btn: "إنشاء المشروع",
        upload_title: "رفع مستندات جديدة",
        upload_desc: "اسحب الملفات هنا أو اضغط للاختيار",
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
        stage_chunking: "تجزئة النص",
        stage_embedding: "تضمين النص",
        stage_indexing: "فهرسة المتجهات",
        ai_settings_title: "إعدادات النماذج",
        ai_settings_desc: "اختر مزود التوليد ومزود التضمين.",
        retrieval_top_k_label: "عدد المقاطع المسترجعة",
        retrieval_top_k_desc: "عدد المقاطع المستخدمة للإجابة.",
        chunk_strategy_label: "استراتيجية التجزئة",
        chunk_strategy_parent: "أب/ابن (من الصغير للكبير)",
        chunk_strategy_simple: "بسيطة",
        chunk_size_label: "حجم المقطع",
        chunk_overlap_label: "تداخل المقاطع",
        parent_chunk_size_label: "حجم المقطع الأب",
        parent_chunk_overlap_label: "تداخل المقطع الأب",
        retrieval_candidate_k_label: "عدد المرشحين الأولي",
        hybrid_enabled_label: "البحث الهجين",
        hybrid_alpha_label: "وزن الدلالي",
        rewrite_enabled_label: "إعادة صياغة الاستعلام",
        rerank_enabled_label: "إعادة الترتيب",
        rerank_top_k_label: "عدد إعادة الترتيب",
        gen_provider_label: "مزود التوليد",
        embed_provider_label: "مزود التضمين",
        select_project_ph: "اختر مشروعاً...",
        delete_confirm: "هل أنت متأكد؟",
        success_saved: "تم الحفظ بنجاح",
        error_generic: "حدث خطأ ما",
        vector_db_label: "قاعدة المتجهات",
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
        start_idea_submit: "ابدأ الآن"
    },
    en: {
        nav_dashboard: "Dashboard",
        nav_projects: "Projects",
        nav_chat: "Smart Chat",
        interview_mode: "Interview mode",
        nav_srs: "SRS Review",
        nav_bot: "Bot Settings",
        nav_ai_config: "AI Settings",
        stat_projects: "Total Projects",
        stat_docs: "Documents",
        stat_chunks: "Text Chunks",
        recent_projects: "Recent Projects",
        view_all: "View All",
        your_projects: "Your Projects",
        welcome_title: "Welcome to RAGMind",
        project_name_ph: "Ex: AI Research",
        project_desc_ph: "Short description...",
        create_project_btn: "Create Project",
        upload_title: "Upload New Documents",
        upload_desc: "Drag files here or click to select",
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
        stage_chunking: "Chunking",
        stage_embedding: "Embedding",
        stage_indexing: "Indexing",
        ai_settings_title: "Model Settings",
        ai_settings_desc: "Select generation and embedding providers.",
        retrieval_top_k_label: "Retrieved chunks",
        retrieval_top_k_desc: "Number of chunks used to answer.",
        chunk_strategy_label: "Chunking strategy",
        chunk_strategy_parent: "Parent/child (small-to-big)",
        chunk_strategy_simple: "Simple",
        chunk_size_label: "Chunk size",
        chunk_overlap_label: "Chunk overlap",
        parent_chunk_size_label: "Parent chunk size",
        parent_chunk_overlap_label: "Parent overlap",
        retrieval_candidate_k_label: "Candidate pool",
        hybrid_enabled_label: "Hybrid search",
        hybrid_alpha_label: "Dense weight",
        rewrite_enabled_label: "Query rewriting",
        rerank_enabled_label: "Reranking",
        rerank_top_k_label: "Rerank top K",
        gen_provider_label: "Generation Provider",
        embed_provider_label: "Embedding Provider",
        select_project_ph: "Select a project...",
        delete_confirm: "Are you sure?",
        success_saved: "Saved successfully",
        error_generic: "Something went wrong",
        vector_db_label: "Vector Database",
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
        start_idea_submit: "Start Now"
    }
};

// State Management
const state = {
    currentView: 'dashboard',
    projects: [],
    stats: null,
    selectedProject: null,
    chatMessages: [],
    isUploading: false,
    retrievalTopK: null,
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
    authToken: localStorage.getItem('authToken') || null,
    currentUser: JSON.parse(localStorage.getItem('currentUser') || 'null'),
    lang: localStorage.getItem('lang') || 'ar',
    theme: localStorage.getItem('theme') || 'light'
};

function getFallbackSrsDraft() {
    return {
        status: state.lang === 'ar' ? 'مسودة أولية' : 'First Draft',
        updated: state.lang === 'ar' ? 'آخر تحديث: اليوم' : 'Last updated: today',
        summary: state.lang === 'ar'
            ? 'لا توجد مسودة بعد. حدّث المحادثة أولاً ثم اضغط تحديث المسودة.'
            : 'No draft yet. Start a chat and click refresh to generate one.',
        metrics: [],
        sections: [],
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
    langToggle: document.getElementById('lang-toggle')
};

// --- API Client ---

const api = {
    async get(endpoint) {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`API Get Error (${endpoint}):`, error);
            showNotification(state.lang === 'ar' ? 'خطأ في الاتصال بالسيرفر' : 'Server Connection Error', 'error');
            throw error;
        }
    },

    async post(endpoint, data, isFormData = false) {
        try {
            const options = {
                method: 'POST',
                body: isFormData ? data : JSON.stringify(data)
            };
            if (!isFormData) {
                options.headers = { 'Content-Type': 'application/json' };
            }

            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error');
            }
            return await response.json();
        } catch (error) {
            console.error(`API Post Error (${endpoint}):`, error);
            showNotification(error.message, 'error');
            throw error;
        }
    },

    async delete(endpoint) {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Delete failed');
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
            animateCounter('stat-projects', stats.projects);
            animateCounter('stat-docs', stats.documents);
            animateCounter('stat-chunks', stats.chunks);

            // Render recent projects
            const list = document.getElementById('recent-projects-list');
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
            const projects = await api.get('/projects/');
            state.projects = projects;

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

    async projectDetail(projectId) {
        renderTemplate('project-detail-template');
        showLoader();

        try {
            const project = await api.get(`/projects/${projectId}`);
            const docs = await api.get(`/projects/${projectId}/documents`);

            state.selectedProject = project;

            document.getElementById('project-name-title').textContent = project.name;

            renderDocsList(docs);
            startDocPolling(projectId, docs);

            // Setup Upload Zone
            setupUploadZone(projectId);

            document.getElementById('back-to-projects').onclick = () => switchView('projects');
            applyTranslations();
        } catch (error) {
            console.error('Project Detail Load Error:', error);
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
            loadChatHistory(state.pendingProjectSelect);
            state.pendingProjectSelect = null;
        } else if (state.chatProjectId) {
            select.value = state.chatProjectId;
            loadChatHistory(state.chatProjectId);
        }

        // Load chat history when switching projects
        select.onchange = () => {
            if (select.value) {
                state.chatProjectId = parseInt(select.value);
                loadChatHistory(state.chatProjectId);
            }
        };

        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        const clearBtn = document.getElementById('clear-chat-btn');
        const interviewToggle = document.getElementById('chat-interview-toggle');

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
                updateInterviewProgress(null, false);
                const hint = state.lang === 'ar'
                    ? 'وضع المقابلة: الأسئلة ستكون موجّهة لاستخراج المتطلبات.'
                    : 'Interview mode: guided questions to capture requirements.';
                showNotification(hint, 'info');
            };
        }

        // Init interview progress bar state
        updateInterviewProgress(null, false);

        // Live doc close button
        const liveDocClose = document.getElementById('live-doc-close');
        if (liveDocClose) {
            liveDocClose.onclick = () => {
                const panel = document.getElementById('live-doc-panel');
                if (panel) panel.style.display = 'none';
            };
        }

        // Upload reference docs button
        const uploadRefBtn = document.getElementById('chat-upload-ref-btn');
        if (uploadRefBtn) {
            uploadRefBtn.onclick = () => {
                const projectId = select.value;
                if (!projectId) {
                    showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                    return;
                }
                openUploadModal(parseInt(projectId));
            };
        }

        // Clear chat handler
        if (clearBtn) {
            clearBtn.onclick = () => {
                const messagesContainer = document.getElementById('chat-messages');
                messagesContainer.innerHTML = `
                    <div class="welcome-msg-pro">
                        <div class="welcome-icon">
                            <i class="fas fa-robot"></i>
                        </div>
                        <h2>${state.lang === 'ar' ? 'كيف يمكنني مساعدتك اليوم؟' : 'How can I help you today?'}</h2>
                        <p>${state.lang === 'ar' ? 'اختر مشروعاً من الأعلى وابدأ في طرح الأسئلة حول مستنداتك.' : 'Select a project from above and start asking questions.'}</p>
                    </div>
                `;
            };
        }

        // Suggestion chips handler
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.onclick = () => {
                chatInput.value = chip.textContent;
                chatInput.oninput();
                chatInput.focus();
            };
        });

        applyTranslations();
    },

    async srs() {
        renderTemplate('srs-template');
        showLoader();

        try {
            const projects = await api.get('/projects/');
            const select = document.getElementById('srs-project-select');
            const refreshBtn = document.getElementById('srs-refresh-btn');
            const exportBtn = document.getElementById('srs-export-btn');
            const bookBtn = document.getElementById('srs-book-btn');

            projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                select.appendChild(opt);
            });

            if (state.selectedProject && select) {
                select.value = state.selectedProject.id;
            }

            refreshBtn.onclick = async () => {
                if (!select.value) {
                    showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                    return;
                }
                refreshBtn.disabled = true;
                await loadSrsDraft(select.value, true);
                refreshBtn.disabled = false;
            };
            exportBtn.onclick = async () => {
                if (!select.value) {
                    showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                    return;
                }
                await downloadSrsPdf(select.value);
            };
            bookBtn.onclick = () => openBookingModal();

            const confirmBtn = document.getElementById('srs-confirm-btn');
            if (confirmBtn) {
                confirmBtn.onclick = async () => {
                    if (!select.value) {
                        showNotification(state.lang === 'ar' ? 'اختر مشروعاً أولاً' : 'Select a project first', 'warning');
                        return;
                    }
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

    async 'bot-config'() {
        renderTemplate('bot-config-template');
        showLoader();

        try {
            const [projects, config] = await Promise.all([
                api.get('/projects/'),
                api.get('/bot/config')
            ]);

            const select = document.getElementById('bot-active-project');
            projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                if (config.active_project_id == p.id) opt.selected = true;
                select.appendChild(opt);
            });

            document.getElementById('save-bot-config-btn').onclick = async () => {
                const projectId = select.value;
                if (!projectId) return;
                try {
                    await api.post('/bot/config', { active_project_id: parseInt(projectId) });
                    showNotification(i18n[state.lang].success_saved, 'success');
                } catch (e) {
                    console.error(e);
                }
            };

            document.getElementById('update-bot-profile-btn').onclick = async () => {
                const name = document.getElementById('bot-name-input').value;
                if (!name) return;
                const formData = new FormData();
                formData.append('name', name);
                try {
                    await api.post('/bot/profile', formData, true);
                    showNotification(i18n[state.lang].success_saved, 'success');
                } catch (e) {
                    console.error(e);
                }
            };

            applyTranslations();
        } catch (error) {
            console.error('Bot Config Error:', error);
        } finally {
            hideLoader();
        }
    },

    async 'ai-config'() {
        renderTemplate('ai-config-template');
        showLoader();

        try {
            const config = await api.get('/config/providers');
            const genSelect = document.getElementById('ai-gen-provider');
            const embedSelect = document.getElementById('ai-embed-provider');
            const vectorDbSelect = document.getElementById('vector-db-provider');
            const embeddingSizeSelect = document.getElementById('embedding-size');
            const retrievalInput = document.getElementById('retrieval-top-k');
            const chunkStrategySelect = document.getElementById('chunk-strategy');
            const chunkSizeInput = document.getElementById('chunk-size');
            const chunkOverlapInput = document.getElementById('chunk-overlap');
            const parentChunkSizeInput = document.getElementById('parent-chunk-size');
            const parentChunkOverlapInput = document.getElementById('parent-chunk-overlap');
            const candidateInput = document.getElementById('retrieval-candidate-k');
            const hybridEnabledInput = document.getElementById('retrieval-hybrid-enabled');
            const hybridAlphaInput = document.getElementById('retrieval-hybrid-alpha');
            const rewriteEnabledInput = document.getElementById('query-rewrite-enabled');
            const rerankEnabledInput = document.getElementById('retrieval-rerank-enabled');
            const rerankTopKInput = document.getElementById('retrieval-rerank-top-k');

            const genProviders = config.available?.llm || [];
            const embedProviders = config.available?.embedding || [];
            const vectorProviders = config.available?.vector_db || [];


            const labelMap = {
                gemini: 'Gemini 2.5 Flash',
                'gemini-2.5-lite-flash': 'Gemini 2.5 Lite Flash',
                'openrouter-gemini-2.0-flash': 'OpenRouter: Gemini 2.0 Flash',
                'openrouter-free': 'OpenRouter: Free',
                'groq-llama-3.3-70b-versatile': 'Groq: Llama 3.3 70B Versatile',
                'groq-gpt-oss-120b': 'Groq: GPT-oss 120B',
                'cerebras-llama-3.3-70b': 'Cerebras: Llama 3.3 70B',
                'cerebras-llama-3.1-8b': 'Cerebras: Llama 3.1 8B',
                'cerebras-gpt-oss-120b': 'Cerebras: GPT-oss 120B',
                cohere: 'Cohere',
                voyage: 'Voyage AI',
                'bge-m3': 'BAAI/bge-m3 (local)',
                pgvector: 'pgvector',
                qdrant: 'Qdrant'
            };

            genProviders.forEach((name) => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.textContent = labelMap[name] || name;
                if (config.llm_provider === name) opt.selected = true;
                genSelect.appendChild(opt);
            });

            embedProviders.forEach((name) => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.textContent = labelMap[name] || name;
                if (config.embedding_provider === name) opt.selected = true;
                embedSelect.appendChild(opt);
            });

            vectorProviders.forEach((name) => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.textContent = labelMap[name] || name;
                if (config.vector_db_provider === name) opt.selected = true;
                vectorDbSelect.appendChild(opt);
            });

            if (typeof config.retrieval_top_k === 'number') {
                retrievalInput.value = String(config.retrieval_top_k);
                state.retrievalTopK = config.retrieval_top_k;
            }

            if (typeof config.voyage_output_dimension === 'number') {
                embeddingSizeSelect.value = String(config.voyage_output_dimension);
            }

            if (config.chunk_strategy) chunkStrategySelect.value = config.chunk_strategy;
            if (typeof config.chunk_size === 'number') chunkSizeInput.value = String(config.chunk_size);
            if (typeof config.chunk_overlap === 'number') chunkOverlapInput.value = String(config.chunk_overlap);
            if (typeof config.parent_chunk_size === 'number') parentChunkSizeInput.value = String(config.parent_chunk_size);
            if (typeof config.parent_chunk_overlap === 'number') parentChunkOverlapInput.value = String(config.parent_chunk_overlap);
            if (typeof config.retrieval_candidate_k === 'number') candidateInput.value = String(config.retrieval_candidate_k);
            if (typeof config.retrieval_hybrid_enabled === 'boolean') hybridEnabledInput.checked = config.retrieval_hybrid_enabled;
            if (typeof config.retrieval_hybrid_alpha === 'number') hybridAlphaInput.value = String(config.retrieval_hybrid_alpha);
            if (typeof config.query_rewrite_enabled === 'boolean') rewriteEnabledInput.checked = config.query_rewrite_enabled;
            if (typeof config.retrieval_rerank_enabled === 'boolean') rerankEnabledInput.checked = config.retrieval_rerank_enabled;
            if (typeof config.retrieval_rerank_top_k === 'number') rerankTopKInput.value = String(config.retrieval_rerank_top_k);

            document.getElementById('save-ai-config-btn').onclick = async () => {
                try {
                    const retrievalValue = parseInt(retrievalInput.value, 10);
                    const embeddingSizeValue = parseInt(embeddingSizeSelect.value, 10);
                    const chunkSizeValue = parseInt(chunkSizeInput.value, 10);
                    const chunkOverlapValue = parseInt(chunkOverlapInput.value, 10);
                    const parentChunkSizeValue = parseInt(parentChunkSizeInput.value, 10);
                    const parentChunkOverlapValue = parseInt(parentChunkOverlapInput.value, 10);
                    const candidateValue = parseInt(candidateInput.value, 10);
                    const hybridAlphaValue = parseFloat(hybridAlphaInput.value);
                    const rerankTopKValue = parseInt(rerankTopKInput.value, 10);
                    await api.post('/config/providers', {
                        llm_provider: genSelect.value,
                        embedding_provider: embedSelect.value,
                        vector_db_provider: vectorDbSelect.value,
                        retrieval_top_k: Number.isFinite(retrievalValue) ? retrievalValue : undefined,
                        voyage_output_dimension: Number.isFinite(embeddingSizeValue) ? embeddingSizeValue : undefined,
                        chunk_strategy: chunkStrategySelect.value,
                        chunk_size: Number.isFinite(chunkSizeValue) ? chunkSizeValue : undefined,
                        chunk_overlap: Number.isFinite(chunkOverlapValue) ? chunkOverlapValue : undefined,
                        parent_chunk_size: Number.isFinite(parentChunkSizeValue) ? parentChunkSizeValue : undefined,
                        parent_chunk_overlap: Number.isFinite(parentChunkOverlapValue) ? parentChunkOverlapValue : undefined,
                        retrieval_candidate_k: Number.isFinite(candidateValue) ? candidateValue : undefined,
                        retrieval_hybrid_enabled: hybridEnabledInput.checked,
                        retrieval_hybrid_alpha: Number.isFinite(hybridAlphaValue) ? hybridAlphaValue : undefined,
                        query_rewrite_enabled: rewriteEnabledInput.checked,
                        retrieval_rerank_enabled: rerankEnabledInput.checked,
                        retrieval_rerank_top_k: Number.isFinite(rerankTopKValue) ? rerankTopKValue : undefined
                    });
                    if (Number.isFinite(retrievalValue)) {
                        state.retrievalTopK = retrievalValue;
                    }
                    showNotification(i18n[state.lang].success_saved, 'success');
                } catch (e) {
                    console.error(e);
                }
            };

            applyTranslations();
        } catch (error) {
            console.error('AI Config Error:', error);
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

async function loadSrsDraft(projectId, forceRefresh = false) {
    if (state.srsRefreshing) return;
    state.srsRefreshing = true;
    try {
        let draft;
        if (!forceRefresh) {
            try {
                draft = await api.get(`/projects/${projectId}/srs`);
            } catch (error) {
                const msg = error?.message || '';
                if (!msg.includes('404')) throw error;
            }
        }

        if (!draft) {
            draft = await api.post(`/projects/${projectId}/srs/refresh`, {
                language: state.lang
            });
        }

        renderSrsDraft(draft.content, draft);
    } catch (error) {
        console.error('SRS Load Error:', error);
        renderSrsDraft(getFallbackSrsDraft(), null);
        showNotification(state.lang === 'ar' ? 'تعذر تحميل المسودة' : 'Failed to load draft', 'error');
    } finally {
        state.srsRefreshing = false;
    }
}

function renderSrsDraft(content, draftMeta) {
    const draft = content || getFallbackSrsDraft();
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
        updatedEl.textContent = draftMeta?.created_at
            ? `${state.lang === 'ar' ? 'آخر تحديث:' : 'Last updated:'} ${new Date(draftMeta.created_at).toLocaleString()}`
            : draft.updated || fallbackTime;
    }
    if (summaryEl) summaryEl.textContent = draft.summary;

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
        sectionsEl.innerHTML = sections.length
            ? sections
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
                        ${section.items.map((item, iIdx) => `<li data-section="${idx}" data-item="${iIdx}">${escapeHtml(item)}</li>`).join('')}
                    </ul>
                </article>
            `)
            .join('')
            : `<div class="empty-state">
                    <div class="empty-state-icon"><i class="fas fa-file-circle-xmark"></i></div>
                    <h3>${state.lang === 'ar' ? 'لا توجد مسودة بعد' : 'No draft yet'}</h3>
                    <p>${state.lang === 'ar' ? 'ابدأ المحادثة ثم اضغط تحديث المسودة.' : 'Start a chat then refresh the draft.'}</p>
                </div>`;

        // Attach inline edit handlers
        sectionsEl.querySelectorAll('.srs-edit-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const sectionIdx = parseInt(btn.dataset.idx);
                const article = sectionsEl.querySelector(`[data-idx="${sectionIdx}"]`);
                if (!article) return;
                const ul = article.querySelector('ul');
                if (!ul || ul.classList.contains('editing')) return;

                ul.classList.add('editing');
                const items = ul.querySelectorAll('li');
                items.forEach(li => {
                    li.contentEditable = 'true';
                    li.classList.add('editable');
                });

                // Change button to save
                btn.innerHTML = `<i class="fas fa-check"></i>`;
                btn.title = state.lang === 'ar' ? 'حفظ' : 'Save';
                btn.classList.add('saving');

                btn.onclick = () => {
                    items.forEach(li => {
                        li.contentEditable = 'false';
                        li.classList.remove('editable');
                    });
                    ul.classList.remove('editing');
                    btn.innerHTML = `<i class="fas fa-pen"></i>`;
                    btn.title = state.lang === 'ar' ? 'تعديل' : 'Edit';
                    btn.classList.remove('saving');
                    showNotification(state.lang === 'ar' ? 'تم حفظ التعديلات' : 'Changes saved', 'success');

                    // Re-attach the edit handler
                    btn.onclick = (e2) => {
                        e2.stopPropagation();
                        btn.click();
                    };
                };
            };
        });
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

async function downloadSrsPdf(projectId) {
    try {
        const response = await fetch(`${API_BASE_URL}/projects/${projectId}/srs/export`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `srs_project_${projectId}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('SRS Export Error:', error);
        showNotification(state.lang === 'ar' ? 'تعذر تصدير SRS' : 'Failed to export SRS', 'error');
    }
}

async function logChatMessages(projectId, userText, assistantText, sources) {
    try {
        await api.post(`/projects/${projectId}/messages`, {
            messages: [
                { role: 'user', content: userText },
                { role: 'assistant', content: assistantText, metadata: { sources: sources || [] } }
            ]
        });
    } catch (error) {
        console.error('Log Messages Error:', error);
    }
}

async function loadChatHistory(projectId) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;

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
        const messages = await api.get(`/projects/${projectId}/messages`);

        // Clear container
        messagesContainer.innerHTML = '';

        if (!messages || messages.length === 0) {
            // Show welcome message if no history
            messagesContainer.innerHTML = `
                <div class="welcome-msg-pro">
                    <div class="welcome-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <h2>${state.lang === 'ar' ? 'كيف يمكنني مساعدتك اليوم؟' : 'How can I help you today?'}</h2>
                    <p>${state.lang === 'ar' ? 'ابدأ في طرح الأسئلة حول مشروعك.' : 'Start asking questions about your project.'}</p>
                </div>
            `;
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
                if (msg.metadata && msg.metadata.sources && msg.metadata.sources.length > 0) {
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
    } catch (error) {
        console.error('Load Chat History Error:', error);
        messagesContainer.innerHTML = `
            <div class="welcome-msg-pro">
                <div class="welcome-icon">
                    <i class="fas fa-robot"></i>
                </div>
                <h2>${state.lang === 'ar' ? 'كيف يمكنني مساعدتك اليوم؟' : 'How can I help you today?'}</h2>
                <p>${state.lang === 'ar' ? 'ابدأ في طرح الأسئلة حول مشروعك.' : 'Start asking questions about your project.'}</p>
            </div>
        `;
    }
}

function createProjectCard(project) {
    const card = document.createElement('div');
    card.className = 'project-card';
    const docCount = project.document_count || 0;
    card.innerHTML = `
        <h3>${escapeHtml(project.name)}</h3>
        <p>${escapeHtml(project.description || (state.lang === 'ar' ? 'لا يوجد وصف' : 'No description'))}</p>
        <div class="project-card-footer">
            <span class="project-card-date"><i class="far fa-calendar"></i> ${new Date(project.created_at).toLocaleDateString(state.lang === 'ar' ? 'ar-EG' : 'en-US')}</span>
            <div class="project-card-actions">
                <span class="doc-count-badge"><i class="fas fa-file-alt"></i> ${docCount}</span>
                <button class="delete-project-btn" data-id="${project.id}"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `;

    card.onclick = (e) => {
        if (e.target.closest('.delete-project-btn')) {
            handleDeleteProject(project.id);
            return;
        }
        state.pendingProjectSelect = project.id;
        switchView('chat');
    };

    return card;
}

function createDocItem(doc) {
    const item = document.createElement('div');
    item.className = 'doc-item';
    const statusClass = doc.status === 'completed' ? 'status-done' : (doc.status === 'failed' ? 'status-error' : 'status-processing');
    const statusIcon = doc.status === 'completed' ? 'fa-check-circle' : (doc.status === 'failed' ? 'fa-exclamation-circle' : 'fa-spinner fa-spin');
    const meta = doc.extra_metadata || {};
    const totalChunks = Number.isFinite(meta.total_chunks) ? meta.total_chunks : null;
    const processedChunks = Number.isFinite(meta.processed_chunks) ? meta.processed_chunks : null;
    const progressValue = Number.isFinite(meta.progress) ? meta.progress : null;
    const stageLabel = getStageLabel(meta.stage);
    const showProgress = doc.status === 'processing' && totalChunks && totalChunks > 0;
    const progressPercent = progressValue != null
        ? Math.max(0, Math.min(100, progressValue))
        : Math.round((processedChunks || 0) / totalChunks * 100);

    const statusText = {
        completed: state.lang === 'ar' ? 'مكتمل' : 'Completed',
        failed: state.lang === 'ar' ? 'فشل' : 'Failed',
        processing: state.lang === 'ar' ? 'جاري المعالجة' : 'Processing'
    };

    item.innerHTML = `
        <div class="doc-info">
            <i class="fas fa-file-pdf"></i>
            <div class="doc-details">
                <span class="doc-name">${doc.original_filename}</span>
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
                    <span>${stageLabel}</span>
                    <span>${processedChunks || 0}/${totalChunks}</span>
                </div>
                <div class="doc-progress-track">
                    <div class="doc-progress-bar" style="width: ${progressPercent}%;"></div>
                </div>
            </div>
        ` : ''}
        <button class="delete-doc-btn" data-id="${doc.id}"><i class="fas fa-trash"></i></button>
    `;

    item.querySelector('.delete-doc-btn').onclick = () => handleDeleteDoc(doc.id);

    return item;
}

function renderDocsList(docs) {
    const docsList = document.getElementById('project-docs-list');
    if (!docsList) return;
    docsList.innerHTML = '';

    if (docs.length === 0) {
        docsList.innerHTML = createEmptyState('fa-file-circle-plus', 'empty_docs', 'empty_docs_desc');
        return;
    }

    docs.forEach(doc => {
        docsList.appendChild(createDocItem(doc));
    });
}

function startDocPolling(projectId, docs) {
    if (state.docPoller) {
        clearInterval(state.docPoller);
        state.docPoller = null;
    }

    const hasProcessing = docs.some(doc => doc.status === 'processing');
    if (!hasProcessing) return;

    state.docPoller = setInterval(async () => {
        if (state.currentView !== 'projectDetail') {
            clearInterval(state.docPoller);
            state.docPoller = null;
            return;
        }

        try {
            const updated = await api.get(`/projects/${projectId}/documents`);
            renderDocsList(updated);
            const stillProcessing = updated.some(doc => doc.status === 'processing');
            if (!stillProcessing) {
                clearInterval(state.docPoller);
                state.docPoller = null;
            }
        } catch (error) {
            console.error('Docs Poll Error:', error);
        }
    }, 3000);
}

function getStageLabel(stage) {
    if (!stage) return '';
    const map = {
        chunking: i18n[state.lang].stage_chunking,
        embedding: i18n[state.lang].stage_embedding,
        indexing: i18n[state.lang].stage_indexing
    };
    return map[stage] || stage;
}

function showNotification(message, type = 'info') {
    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-circle-exclamation',
        warning: 'fa-triangle-exclamation',
        info: 'fa-circle-info'
    };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fas ${iconMap[type] || iconMap.info} toast-icon"></i><span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 50);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
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
    icon.className = state.theme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';

    localStorage.setItem('theme', state.theme);
}

function toggleLang() {
    state.lang = state.lang === 'ar' ? 'en' : 'ar';
    localStorage.setItem('lang', state.lang);
    applyTranslations();
    switchView(state.currentView, state.selectedProject ? state.selectedProject.id : null);
}

// --- Event Handlers ---

async function switchView(viewName, params = null) {
    if (state.docPoller) {
        clearInterval(state.docPoller);
        state.docPoller = null;
    }
    state.currentView = viewName;

    // Update Nav
    elements.navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Render View
    if (viewName === 'projectDetail') {
        await views.projectDetail(params);
    } else if (views[viewName]) {
        await views[viewName]();
    }
}

async function handleNewProject() {
    const t = i18n[state.lang];
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

    document.getElementById('save-project-btn').onclick = async () => {
        const name = document.getElementById('new-project-name').value;
        const description = document.getElementById('new-project-desc').value;

        if (!name) {
            showNotification(state.lang === 'ar' ? 'يرجى إدخال اسم المشروع' : 'Please enter project name', 'warning');
            return;
        }

        try {
            const newProject = await api.post('/projects/', { name, description });
            showNotification(i18n[state.lang].success_saved, 'success');
            elements.modalOverlay.classList.add('hidden');

            // Navigate to chat with interview mode ON
            state.interviewMode = true;
            state.pendingProjectSelect = newProject.id;
            state.previousSummary = null;
            state.lastCoverage = null;
            switchView('chat');
        } catch (error) {
            console.error('Create Project Error:', error);
        }
    };
}

async function handleDeleteProject(id) {
    if (confirm(i18n[state.lang].delete_confirm)) {
        try {
            await api.delete(`/projects/${id}`);
            showNotification(i18n[state.lang].success_saved, 'success');
            switchView(state.currentView);
        } catch (error) {
            console.error('Delete Project Error:', error);
        }
    }
}

async function handleDeleteDoc(id) {
    if (confirm(i18n[state.lang].delete_confirm)) {
        try {
            await api.delete(`/documents/${id}`);
            showNotification(i18n[state.lang].success_saved, 'success');
            if (state.selectedProject) {
                switchView('projectDetail', state.selectedProject.id);
            }
        } catch (error) {
            console.error('Delete Doc Error:', error);
        }
    }
}

async function handleChatSubmit() {
    const input = document.getElementById('chat-input');
    const projectSelect = document.getElementById('chat-project-select');
    const langSelect = document.getElementById('chat-lang');
    const sendBtn = document.getElementById('send-btn');

    const query = input.value.trim();
    const projectId = projectSelect.value;
    const language = langSelect.value;

    if (!query) return;
    if (!projectId) {
        showNotification(state.lang === 'ar' ? 'يرجى اختيار مشروع أولاً' : 'Select a project first', 'warning');
        return;
    }

    addChatMessage('user', query);
    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;

    const thinkingId = addChatMessage('bot', '', true);

    if (state.interviewMode) {
        try {
            await api.post(`/projects/${projectId}/messages`, {
                messages: [{ role: 'user', content: query }]
            });

            const interviewPayload = { language };
            if (state.previousSummary) {
                interviewPayload.last_summary = state.previousSummary;
            }
            if (state.lastCoverage) {
                interviewPayload.last_coverage = state.lastCoverage;
            }

            const next = await api.post(`/projects/${projectId}/interview/next`, interviewPayload);

            const questionText = next.question || (state.lang === 'ar'
                ? 'هل يمكن توضيح النقطة الأخيرة بمثال؟'
                : 'Could you clarify the last point with an example?');

            finalizeBotMessage(thinkingId, questionText, null);

            // Store coverage for next request
            if (next.coverage) {
                state.lastCoverage = next.coverage;
            }
            updateInterviewProgress(next.coverage, next.done);
            if (next.summary) {
                updateLiveDoc(next.summary, next.stage);
            }

            await api.post(`/projects/${projectId}/messages`, {
                messages: [{ role: 'assistant', content: questionText, metadata: { stage: next.stage || '' } }]
            });

            // Auto-generate SRS and navigate when interview completes
            if (next.done) {
                showNotification(
                    state.lang === 'ar'
                        ? 'تم إكمال المقابلة بنجاح! جارٍ إنشاء مستند SRS...'
                        : 'Interview complete! Generating SRS document...',
                    'success'
                );
                state.srsRefreshing = true;
                try {
                    await api.post(`/projects/${projectId}/srs/refresh`, { language });
                } catch (e) {
                    console.error('Auto SRS generation failed:', e);
                } finally {
                    state.srsRefreshing = false;
                }
                state.selectedProject = { id: parseInt(projectId) };
                setTimeout(() => switchView('srs'), 1500);
            }
        } catch (error) {
            console.error('Interview Error:', error);
            const msg = state.lang === 'ar' ? 'تعذر إكمال المقابلة الآن' : 'Interview failed. Try again.';
            finalizeBotMessage(thinkingId, msg, null);
        }
        return;
    }

    try {
        const payload = { query, language };
        if (Number.isInteger(state.retrievalTopK)) {
            payload.top_k = state.retrievalTopK;
        }

        // ── Stream via SSE (fetch + ReadableStream) ──
        const response = await fetch(`${API_BASE_URL}/projects/${projectId}/query/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullAnswer = '';
        let sources = null;

        // Remove typing indicator as soon as first token arrives
        let indicatorRemoved = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep incomplete line in buffer

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const dataStr = line.slice(6).trim();
                if (dataStr === '[DONE]') continue;

                try {
                    const evt = JSON.parse(dataStr);

                    if (evt.type === 'sources') {
                        sources = evt.sources;
                    } else if (evt.type === 'token') {
                        if (!indicatorRemoved) {
                            const ind = document.querySelector(`#msg-${thinkingId} .typing-indicator-pro`);
                            if (ind) ind.remove();
                            indicatorRemoved = true;
                        }
                        fullAnswer += evt.token;
                        // Live-render the accumulated text
                        const textEl = document.querySelector(`#msg-${thinkingId} .msg-text`);
                        if (textEl) {
                            textEl.classList.add('streaming');
                            textEl.innerHTML = formatAnswerHtml(fullAnswer) || escapeHtml(fullAnswer);
                            textEl.dir = detectTextDirection(fullAnswer);
                        }
                        // Auto-scroll
                        const container = document.getElementById('chat-messages');
                        container.scrollTop = container.scrollHeight;
                    } else if (evt.type === 'error') {
                        fullAnswer = evt.message || i18n[state.lang].error_generic;
                    }
                } catch (_) { /* skip malformed JSON */ }
            }
        }

        // Finalize: attach sources + copy button
        finalizeBotMessage(thinkingId, fullAnswer, sources);
        logChatMessages(projectId, query, fullAnswer, sources);

    } catch (error) {
        // Fallback: try non-streaming endpoint
        console.warn('Stream failed, falling back to non-streaming:', error.message);
        try {
            const payload = { query, language };
            if (Number.isInteger(state.retrievalTopK)) {
                payload.top_k = state.retrievalTopK;
            }
            const result = await api.post(`/projects/${projectId}/query`, payload);
            // Remove indicator
            const ind = document.querySelector(`#msg-${thinkingId} .typing-indicator-pro`);
            if (ind) ind.remove();
            finalizeBotMessage(thinkingId, result.answer, result.sources);
            logChatMessages(projectId, query, result.answer, result.sources);
        } catch (fallbackErr) {
            const ind = document.querySelector(`#msg-${thinkingId} .typing-indicator-pro`);
            if (ind) ind.remove();
            finalizeBotMessage(thinkingId, i18n[state.lang].error_generic, null);
        }
    }
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
            li.innerHTML = `
                <i class="fas fa-file-alt"></i>
                <span>${escapeHtml(s.document_name)}</span>
                <span class="source-score">${(s.similarity * 100).toFixed(0)}%</span>
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

    const id = Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg-pro ${role}-msg-pro`;
    msgDiv.id = `msg-${id}`;
    
    const isUser = role === 'user';
    const authorName = isUser 
        ? (state.lang === 'ar' ? 'أنت' : 'You') 
        : 'RAGMind';
    
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
                ${isThinking ? '<div class="typing-indicator-pro"><span></span><span></span><span></span></div>' : ''}
            </div>
        </div>
    `;
    
    if (!isUser && !isThinking) {
        const msgText = msgDiv.querySelector('.msg-text');
        msgText.innerHTML = escapeHtml(text);
        msgText.dir = textDir;
    }
    
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return id;
}

function escapeHtml(value) {
    if (value == null) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function detectTextDirection(text) {
    if (!text) return 'auto';
    // Check for Arabic/Hebrew/Persian characters
    const rtlChars = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0590-\u05FF]/;
    const firstChars = text.trim().substring(0, 50);
    return rtlChars.test(firstChars) ? 'rtl' : 'ltr';
}

function formatAnswerHtml(text) {
    if (!text) return '';

    let cleaned = String(text).replace(/\r\n/g, '\n').trim();
    cleaned = cleaned.replace(/\s*(Source|Sources|المصدر|المصادر)\s*:.*/gi, '').trim();
    cleaned = cleaned.replace(/\s+\*\s+/g, '\n* ');
    cleaned = cleaned.replace(/\s+-\s+/g, '\n- ');

    const lines = cleaned.split('\n').map(line => line.trim()).filter(Boolean);
    if (lines.length === 0) return '';

    const parts = [];
    let listBuffer = [];

    const flushList = () => {
        if (listBuffer.length === 0) return;
        const items = listBuffer
            .map(item => `<li>${formatInlineMarkdown(item)}</li>`)
            .join('');
        parts.push(`<ul class="answer-list">${items}</ul>`);
        listBuffer = [];
    };

    lines.forEach(line => {
        if (/^[*-]\s+/.test(line)) {
            listBuffer.push(line.replace(/^[*-]\s+/, ''));
            return;
        }
        flushList();
        parts.push(`<p class="answer-paragraph">${formatInlineMarkdown(line)}</p>`);
    });

    flushList();
    return parts.join('');
}

function formatInlineMarkdown(value) {
    const escaped = escapeHtml(value);
    return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
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
        (p.name && p.name.toLowerCase().includes(q)) ||
        (p.description && p.description.toLowerCase().includes(q))
    );
    // Render inline results in current view container
    const list = document.getElementById('all-projects-list') || document.getElementById('recent-projects-list');
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
}

function closeMobileSidebar() {
    document.querySelector('.sidebar').classList.remove('open');
    const overlay = document.getElementById('sidebar-overlay');
    overlay.classList.remove('active');
    setTimeout(() => { overlay.style.display = 'none'; }, 300);
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
    for (const file of files) {
        const lowerName = file.name.toLowerCase();
        if (!lowerName.endsWith('.pdf') && !lowerName.endsWith('.txt') && !lowerName.endsWith('.docx')) {
            showNotification(
                state.lang === 'ar'
                    ? 'نوع الملف غير مدعوم. الملفات المدعومة: PDF, TXT, DOCX'
                    : 'Unsupported file type. Supported: PDF, TXT, DOCX',
                'warning'
            );
            continue;
        }
        const formData = new FormData();
        formData.append('file', file);

        showNotification(`${state.lang === 'ar' ? 'جاري رفع' : 'Uploading'} ${file.name}...`, 'info');

        try {
            await api.post(`/projects/${projectId}/documents`, formData, true);
            showNotification(`${state.lang === 'ar' ? 'تم رفع' : 'Uploaded'} ${file.name}`, 'success');
        } catch (error) {
            console.error('Upload Error:', error);
        }
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
        <div id="modal-upload-status" class="mt-4"></div>
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

    document.getElementById('book-submit-btn').onclick = () => {
        const name = document.getElementById('book-name').value.trim();
        const email = document.getElementById('book-email').value.trim();
        const date = document.getElementById('book-date').value;
        const time = document.getElementById('book-time').value;
        const notes = document.getElementById('book-notes').value.trim();

        if (!name || !email || !date) {
            showNotification(t.book_fill_required, 'warning');
            return;
        }

        // Store booking (for now, just notify success - backend integration can be added later)
        console.log('Booking:', { name, email, date, time, notes, project: state.selectedProject?.name });
        showNotification(t.book_success, 'success');
        elements.modalOverlay.classList.add('hidden');
    };
}

// --- Voice Recording (STT) ---

async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
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
        const langSelect = document.getElementById('chat-lang');
        const language = langSelect ? langSelect.value : 'auto';

        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');
        formData.append('language', language);

        const response = await fetch(`${API_BASE_URL}/stt/transcribe`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Transcription failed');
        }

        const result = await response.json();
        if (result.success && result.text) {
            const chatInput = document.getElementById('chat-input');
            if (chatInput) {
                chatInput.value += (chatInput.value ? ' ' : '') + result.text;
                chatInput.oninput();
                chatInput.focus();
            }
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

function updateInterviewProgress(coverage, done) {
    const progressBar = document.getElementById('interview-progress');
    const liveDocPanel = document.getElementById('live-doc-panel');

    if (!state.interviewMode || done) {
        if (progressBar) progressBar.style.display = 'none';
        if (liveDocPanel) liveDocPanel.style.display = 'none';
        return;
    }

    if (progressBar) {
        progressBar.style.display = 'block';
        const areas = ['discovery', 'scope', 'users', 'features', 'constraints'];

        // Find the active area (lowest coverage that is not yet >= 70%)
        let activeArea = null;
        if (coverage) {
            let minCoverage = Infinity;
            for (const area of areas) {
                const pct = coverage[area] || 0;
                if (pct < 70 && pct < minCoverage) {
                    minCoverage = pct;
                    activeArea = area;
                }
            }
        }

        areas.forEach(area => {
            const pct = coverage ? (coverage[area] || 0) : 0;
            const fillEl = document.getElementById(`coverage-${area}`);
            const pctEl = document.getElementById(`coverage-pct-${area}`);
            const itemEl = progressBar.querySelector(`[data-area="${area}"]`);

            if (fillEl) fillEl.style.width = `${Math.min(100, pct)}%`;
            if (pctEl) pctEl.textContent = `${Math.round(pct)}%`;

            if (itemEl) {
                itemEl.classList.remove('active-area', 'complete-area');
                if (pct >= 70) {
                    itemEl.classList.add('complete-area');
                } else if (area === activeArea) {
                    itemEl.classList.add('active-area');
                }
            }
        });
    }

    if (liveDocPanel) {
        liveDocPanel.style.display = 'flex';
    }
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

    // Structured summary (object with arrays)
    if (typeof summary === 'object' && !Array.isArray(summary)) {
        const prevSummary = state.previousSummary || {};
        let html = '';

        for (const [area, items] of Object.entries(summary)) {
            if (!Array.isArray(items) || items.length === 0) continue;

            const prevItems = (prevSummary[area] || []);
            const icon = areaIcons[area] || 'fa-circle-dot';
            const label = stageLabels[area] || area;

            html += `
                <div class="live-doc-srs-section">
                    <div class="live-doc-section-header">
                        <i class="fas ${icon}"></i>
                        <span>${escapeHtml(label)}</span>
                        <span class="live-doc-count-badge">${items.length}</span>
                    </div>
                    <ul class="live-doc-items">
                        ${items.map(item => {
                            const isNew = !prevItems.includes(item);
                            return `<li class="${isNew ? 'live-doc-new-item' : ''}">${escapeHtml(item)}</li>`;
                        }).join('')}
                    </ul>
                </div>
            `;
        }

        content.innerHTML = html || `
            <div class="live-doc-empty">
                <i class="fas fa-pencil-alt"></i>
                <p>${i18n[state.lang].live_doc_empty}</p>
            </div>
        `;

        // Store deep copy for diff tracking
        state.previousSummary = JSON.parse(JSON.stringify(summary));

        // Auto-scroll to newest item
        const newItems = content.querySelectorAll('.live-doc-new-item');
        if (newItems.length > 0) {
            newItems[newItems.length - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        return;
    }

    // Legacy: string summary (backward compatible)
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

    // Login
    document.getElementById('login-form').onsubmit = async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('auth-error');
        errorEl.style.display = 'none';

        try {
            const res = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Login failed');
            }
            const data = await res.json();
            setAuthState(data.token, data.user);
            showApp();
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
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

        try {
            const res = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Registration failed');
            }
            const data = await res.json();
            setAuthState(data.token, data.user);
            showApp();
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
        }
    };
}

function setAuthState(token, user) {
    state.authToken = token;
    state.currentUser = user;
    localStorage.setItem('authToken', token);
    localStorage.setItem('currentUser', JSON.stringify(user));
}

function clearAuthState() {
    state.authToken = null;
    state.currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
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
    } else {
        showAuthScreen();
    }

    // Nav Clicks
    elements.navItems.forEach(item => {
        item.onclick = () => {
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

    // Keyboard Shortcut: Ctrl+K to focus search
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (searchInput) searchInput.focus();
        }
    });

    // Init State
    if (state.theme === 'light') {
        document.body.classList.add('light-theme');
        document.body.classList.remove('dark-theme');
        elements.themeToggle.querySelector('i').className = 'fas fa-sun';
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        elements.themeToggle.querySelector('i').className = 'fas fa-moon';
    }

    // Initial View
    applyTranslations();
    switchView('dashboard');
});
