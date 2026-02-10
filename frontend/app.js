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
        copied_btn: "تم النسخ!"
    },
    en: {
        nav_dashboard: "Dashboard",
        nav_projects: "Projects",
        nav_chat: "Smart Chat",
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
        copied_btn: "Copied!"
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
    lang: localStorage.getItem('lang') || 'ar',
    theme: localStorage.getItem('theme') || 'dark'
};

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

        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        const clearBtn = document.getElementById('clear-chat-btn');

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
        switchView('projectDetail', project.id);
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
    elements.modalTitle.textContent = i18n[state.lang].create_project_btn;
    elements.modalBody.innerHTML = `
        <div class="form-group">
            <label>${state.lang === 'ar' ? 'اسم المشروع' : 'Project Name'}</label>
            <input type="text" id="new-project-name" class="form-control">
        </div>
        <div class="form-group">
            <label>${state.lang === 'ar' ? 'الوصف' : 'Description'}</label>
            <textarea id="new-project-desc" class="form-control"></textarea>
        </div>
        <button id="save-project-btn" class="btn btn-primary w-100 mt-4">${i18n[state.lang].create_project_btn}</button>
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
            await api.post('/projects/', { name, description });
            showNotification(i18n[state.lang].success_saved, 'success');
            elements.modalOverlay.classList.add('hidden');
            switchView(state.currentView); // Refresh current view
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
            switchView('projectDetail', projectId); // Refresh list
        } catch (error) {
            console.error('Upload Error:', error);
        }
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
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
    }

    // Initial View
    applyTranslations();
    switchView('dashboard');
});
