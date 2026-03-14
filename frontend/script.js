let currentTopic = "";
let fullVideoKit = null; // unified kit for the active session
let chatHistory = []; // stores {role, content} for the chatbot session
window.currentSessionId = 'session_' + Date.now();

// ======================================================
// REUSABLE API FETCH HELPER
// ======================================================
async function apiFetch(url, body) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'API Error: ' + res.status);
        }
        return await res.json();
    } catch (err) {
        console.error('apiFetch error:', err);
        throw err;
    }
}

/**
 * Tab Switching Logic
 */
function switchToTab(tabName) {
    document.querySelectorAll('.view-wrapper').forEach(el => el.classList.add('view-hidden'));
    const view = document.getElementById(`view-${tabName}`);
    if (view) view.classList.remove('view-hidden');

    document.querySelectorAll('.sidebar-item').forEach(el => {
        el.classList.remove('sidebar-item-active', 'bg-primary/10', 'text-primary');
        el.classList.add('text-slate-400');
    });
    const activeNav = document.getElementById(`nav-${tabName}`);
    if (activeNav) {
        activeNav.classList.add('sidebar-item-active', 'bg-primary/10', 'text-primary');
        activeNav.classList.remove('text-slate-400');
    }



    if (fullVideoKit) {
        // NOTE: voiceover-copy (SEO page) is intentionally NOT auto-populated —
        // boxes only fill when user clicks "Generate SEO Data"
        if (tabName === 'thumbnail') populateThumbnailPage();
        if (tabName === 'scenes') populateScenesPage();
    }

}

function goToWizardStep(step) {
    if (step !== 1) return;
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('view-hidden'));
    const stepEl = document.getElementById('wizard-step-1');
    if (stepEl) stepEl.classList.remove('view-hidden');
    loadContentResearchTopics();
}

function sidebarScrollToTop() {
    const sidebar = document.getElementById('main-sidebar');
    if (sidebar) sidebar.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========== Content Research (Step 1) ==========

function showTopicsLoading(show) {
    const loading = document.getElementById('topics-grid-loading');
    const grid = document.getElementById('topics-grid');
    if (loading) loading.style.display = show ? 'flex' : 'none';
    if (grid) grid.classList.toggle('hidden', show);
}

function showTopicsEmpty(show) {
    const el = document.getElementById('topics-grid-empty');
    if (el) el.classList.toggle('hidden', !show);
}

function setTopicsSectionLabel(isSearch) {
    const icon = document.getElementById('topics-section-icon');
    const title = document.getElementById('topics-section-title');
    if (icon) icon.textContent = isSearch ? 'search' : 'trending_up';
    if (title) title.textContent = isSearch ? 'Search results' : 'Trending Topics';
}

function renderTopicCards(topics) {
    const grid = document.getElementById('topics-grid');
    const loading = document.getElementById('topics-grid-loading');
    if (!grid) return;
    if (loading) loading.style.display = 'none';
    showTopicsEmpty(!topics || topics.length === 0);
    if (!topics || topics.length === 0) {
        grid.classList.add('hidden');
        return;
    }
    grid.classList.remove('hidden');

    const categoryClass = (cat) =>
        (cat && (cat.toLowerCase().includes('cultural') || cat.toLowerCase().includes('roots')))
            ? 'bg-accent-magenta/90'
            : 'bg-primary/90';
    const btnClass = (cat) =>
        (cat && (cat.toLowerCase().includes('cultural') || cat.toLowerCase().includes('roots')))
            ? 'hover:bg-accent-magenta'
            : 'hover:bg-primary';

    const escapeHtml = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    const escapeAttr = (s) => escapeHtml(s).replace(/'/g, '&#39;');
    grid.innerHTML = topics.map((t) => {
        const cat = t.category || 'Topic';
        const titleSafe = escapeAttr(t.title);
        return `
            <div class="group relative bg-surface-dark border border-slate-800/50 rounded-2xl overflow-hidden hover:border-primary/50 transition-all hover:scale-[1.02] duration-300 shadow-xl">
                <div class="h-40 overflow-hidden relative">
                    <img class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" alt="${titleSafe}" src="${escapeAttr(t.image)}" />
                    <div class="absolute inset-0 bg-gradient-to-t from-surface-dark via-transparent opacity-80"></div>
                    <span class="absolute top-4 left-4 ${categoryClass(cat)} backdrop-blur-md text-[10px] font-bold px-2 py-1 rounded text-white uppercase tracking-wider">${escapeHtml(cat)}</span>
                </div>
                <div class="p-6">
                    <h4 class="text-lg font-bold text-white mb-2">${escapeHtml(t.title)}</h4>
                    <p class="text-sm text-slate-400 mb-6 leading-relaxed">${escapeHtml(t.description)}</p>
                    <button type="button" data-topic="${titleSafe}" onclick="selectTopic(this.getAttribute('data-topic'))" class="topic-btn w-full py-3 bg-slate-800 ${btnClass(cat)} text-slate-300 hover:text-white rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2">
                        Select Topic <span class="material-symbols-outlined text-sm">arrow_forward</span>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function loadContentResearchTopics() {
    const grid = document.getElementById('topics-grid');
    if (!grid) return;
    showTopicsLoading(true);
    showTopicsEmpty(false);
    setTopicsSectionLabel(false);
    try {
        const res = await fetch('/api/get-topics');
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to load topics');
        renderTopicCards(data.topics || []);
    } catch (e) {
        console.error(e);
        showTopicsLoading(false);
        showTopicsEmpty(true);
    }
}

async function searchTopics() {
    const input = document.getElementById('topic-search-input');
    const btn = document.getElementById('topic-search-generate-btn');
    const q = (input && input.value) ? input.value.trim() : '';
    if (!q) {
        loadContentResearchTopics();
        return;
    }
    await generateFullVideoFromTitle(q, btn);
}

async function surpriseMeTopic() {
    const btn = document.getElementById('surprise-me-btn');
    const label = document.getElementById('surprise-me-label');
    if (btn) btn.disabled = true;
    if (label) label.textContent = 'Picking a topic…';
    try {
        const res = await fetch('/api/random-topic');
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed');
        const topic = data.topic && data.topic.title ? data.topic.title : data.topic;
        if (topic) selectTopic(topic);
    } catch (e) {
        console.error(e);
        loadContentResearchTopics();
    } finally {
        if (btn) btn.disabled = false;
        if (label) label.textContent = 'Surprise me with a random topic';
    }
}

async function generateFullVideoFromTitle(title, optButton) {
    currentTopic = title;
    const overlay = document.getElementById('content-research-overlay');
    const btn = optButton || document.getElementById('topic-search-generate-btn');
    if (overlay) overlay.classList.remove('hidden');
    if (btn) { btn.disabled = true; btn.textContent = 'Generating…'; }

    try {
        const res = await fetch('/api/generate-from-title', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, session_id: window.currentSessionId })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Generation failed');
        if (data.session_id) {
            window.currentSessionId = data.session_id;
        }
        fullVideoKit = data;
        populateVoiceoverPage();
        populateThumbnailPage();
        populateScenesPage();
        switchToTab('voiceover-copy');
    } catch (e) {
        alert('Failed to generate video kit. Please try again.');
        console.error(e);
    } finally {
        if (overlay) overlay.classList.add('hidden');
        if (btn) { btn.disabled = false; btn.textContent = 'Generate'; }
    }
}

async function selectTopic(topicName) {
    await generateFullVideoFromTitle(topicName);
}

function populateVoiceoverPage() {
    if (!fullVideoKit) return;
    const set = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text || '—'; };
    const tagsEl = document.getElementById('voiceover-tags');
    const keywordsEl = document.getElementById('voiceover-keywords');
    set('voiceover-title', fullVideoKit.title);
    set('voiceover-description', fullVideoKit.description);
    set('voiceover-script', fullVideoKit.script_content);
    if (tagsEl) {
        const tags = Array.isArray(fullVideoKit.tags) ? fullVideoKit.tags : [];
        tagsEl.innerHTML = tags.length ? tags.map(t => `<span class="px-3 py-1.5 bg-primary/10 border border-primary/20 text-primary text-[11px] font-bold rounded-lg">${String(t).replace(/</g, '&lt;')}</span>`).join('') : '—';
    }
    if (keywordsEl) {
        const kw = Array.isArray(fullVideoKit.keywords) ? fullVideoKit.keywords : [];
        keywordsEl.innerHTML = kw.length ? kw.map(k => `<span class="px-3 py-1.5 bg-white/5 border border-white/10 text-slate-400 text-[11px] font-bold rounded-lg">${String(k).replace(/</g, '&lt;')}</span>`).join('') : '—';
    }
}

function populateThumbnailPage() {
    const img = document.getElementById('thumbnail-preview-img');
    const placeholder = document.getElementById('thumbnail-placeholder');
    const actionsContainer = document.getElementById('thumbnail-actions');
    const hoverOverlay = document.getElementById('thumbnail-hover-overlay');

    if (!img || !placeholder) return;

    if (fullVideoKit && fullVideoKit.thumbnail_url) {
        img.src = fullVideoKit.thumbnail_url;
        img.classList.remove('hidden');
        placeholder.classList.add('hidden');
        if (actionsContainer) actionsContainer.classList.remove('hidden');
        if (hoverOverlay) hoverOverlay.classList.remove('hidden');
    } else {
        img.removeAttribute('src');
        img.classList.add('hidden');
        placeholder.classList.remove('hidden');
        if (actionsContainer) actionsContainer.classList.add('hidden');
        if (hoverOverlay) hoverOverlay.classList.add('hidden');
    }
}

// ========== Scenes (Step 3) ==========

function populateScenesPage() {
    // Sync script from script writer if available
    const scriptInput = document.getElementById('scenes-script-input');
    if (scriptInput && fullVideoKit && fullVideoKit.script_content) {
        if (!scriptInput.value) scriptInput.value = fullVideoKit.script_content;
    }
    updateScenesChatGrid();
}

function copySpecificData(elementId) {
    const el = document.getElementById(elementId);
    if (!el || el.textContent === '—') return;

    // Copy the text content directly since it's just raw text
    const textToCopy = el.textContent;

    navigator.clipboard.writeText(textToCopy).then(() => {
        // Find the button (next sibling to the paragraph or div element we passed in)
        const btn = el.nextElementSibling;
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<span class="material-symbols-outlined text-[18px] text-green-400">check</span>';
            setTimeout(() => { btn.innerHTML = originalHTML; }, 2000);
        }
    }).catch(() => alert('Copy failed.'));
}

function copySpecificTagKeywordData(elementId) {
    const el = document.getElementById(elementId);
    if (!el || el.textContent === '—') return;

    // For Tags and Keywords, they are inside span tags, so we map their text content
    const spans = el.querySelectorAll('span');
    let textToCopy = "";
    if (spans.length > 0) {
        textToCopy = Array.from(spans).map(span => span.textContent).join(elementId.includes('tags') ? ' ' : ', ');
    } else {
        textToCopy = el.textContent; // Fallback
    }

    navigator.clipboard.writeText(textToCopy).then(() => {
        const btn = el.nextElementSibling;
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<span class="material-symbols-outlined text-[18px] text-green-400">check</span>';
            setTimeout(() => { btn.innerHTML = originalHTML; }, 2000);
        }
    }).catch(() => alert('Copy failed.'));
}

async function regenerateThumbnail(style) {
    if (!fullVideoKit || !fullVideoKit.title) return;
    const btn = document.getElementById('regenerate-thumbnail-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="material-symbols-outlined animate-spin">progress_activity</span> Regenerating…'; }
    try {
        const res = await fetch('/api/regenerate-thumbnail', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: fullVideoKit.title, style: style || 'cinematic' })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed');
        fullVideoKit.thumbnail_url = data.thumbnail_url;
        populateThumbnailPage();
        document.querySelectorAll('.thumbnail-style-btn').forEach(b => {
            b.classList.remove('bg-primary', 'text-white');
            b.classList.add('bg-white/10', 'text-slate-300');
        });
        const clicked = document.querySelector(`[onclick="regenerateThumbnail('${style}')"]`);
        if (clicked) { clicked.classList.add('bg-primary', 'text-white'); clicked.classList.remove('bg-white/10', 'text-slate-300'); }
    } catch (e) {
        console.error(e);
        alert('Regenerate failed.');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<span class="material-symbols-outlined">auto_awesome</span> Regenerate thumbnail'; }
    }
}

// Default View
document.addEventListener("DOMContentLoaded", () => {
    switchToTab('dashboard');
    startNewChat();
    loadChatHistory();

    // Add scroll event listener to chat history for floating button
    const chatHistoryEl = document.getElementById('chat-history');
    if (chatHistoryEl) {
        chatHistoryEl.addEventListener('scroll', () => {
            const scrollBtn = document.getElementById('scroll-bottom-btn');
            if (!scrollBtn) return;
            // If user scrolled up by at least 100px from the bottom, show the button
            if (chatHistoryEl.scrollHeight - chatHistoryEl.scrollTop - chatHistoryEl.clientHeight > 100) {
                scrollBtn.classList.remove('opacity-0', 'translate-y-4', 'pointer-events-none');
                scrollBtn.classList.add('opacity-100', 'translate-y-0', 'pointer-events-auto');
            } else {
                scrollBtn.classList.remove('opacity-100', 'translate-y-0', 'pointer-events-auto');
                scrollBtn.classList.add('opacity-0', 'translate-y-4', 'pointer-events-none');
            }
        });
    }
});

/**
 * Chat Hub Logic
 */
let currentChatMode = 'text';
let videoData = { title: '', voice: '', image: '' };
let attachedFile = null;
let isMicActive = false;

function toggleChatModeMenu() {
    const menu = document.getElementById('chat-mode-menu');
    if (menu) {
        if (menu.classList.contains('hidden')) {
            menu.classList.remove('hidden');
            menu.classList.add('flex');
        } else {
            menu.classList.add('hidden');
            menu.classList.remove('flex');
        }
    }
}

// ---------------------------
// Action Handlers
// ---------------------------
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        attachedFile = file.name;
        document.getElementById('attachment-name').textContent = attachedFile;
        document.getElementById('attachment-preview').classList.remove('hidden');
    }
}

function removeAttachment() {
    attachedFile = null;
    document.getElementById('hidden-file-upload').value = '';
    document.getElementById('attachment-preview').classList.add('hidden');
}

function toggleMic() {
    const micBtn = document.getElementById('mic-btn');
    const chatInput = document.getElementById('chat-input');

    isMicActive = !isMicActive;

    if (isMicActive) {
        micBtn.classList.add('text-accent-pink', 'animate-pulse');
        micBtn.classList.remove('text-slate-400');
        chatInput.placeholder = "Listening...";
        chatInput.disabled = true;

        // Simulate listening completion
        setTimeout(() => {
            chatInput.value = "Tell me a fascinating fact about black holes.";
            toggleMic();
            chatInput.focus();
        }, 2500);
    } else {
        micBtn.classList.remove('text-accent-pink', 'animate-pulse');
        micBtn.classList.add('text-slate-400');
        chatInput.placeholder = "Message Nova...";
        chatInput.disabled = false;
    }
}

function setChatMode(mode, label) {
    currentChatMode = mode;
    const indicator = document.getElementById('current-chat-mode-indicator');
    if (indicator) indicator.textContent = label;
    toggleChatModeMenu();

    // Focus back on input
    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.focus();
}

function saveVoiceSelection(voiceId) {
    videoData.voice = voiceId;
    alert("Voice saved to project settings: " + voiceId);

    // Automatically show Script Studio if possible
    if (videoData.title) {
        switchToTab('content-research');
        goToWizardStep(2);
    }
}

function saveImageSelection(url) {
    videoData.image = url;
    alert("Concept Image saved to project assets!");

    if (videoData.title) {
        switchToTab('content-research');
        goToWizardStep(2);
    }
}

function sendChatMessage(msg) {
    if (!msg.trim() && !attachedFile) return;
    const chatMessages = document.getElementById('chat-history');

    // Add user message with attachment if any
    const userDiv = document.createElement('div');
    userDiv.className = 'flex gap-4 justify-end';

    let fileHtml = '';
    if (attachedFile) {
        fileHtml = `
            <div class="mb-2 p-2 bg-black/20 rounded border border-white/5 flex items-center gap-2">
                <span class="material-symbols-outlined text-sm text-primary">description</span>
                <span class="text-xs text-white font-medium">${attachedFile}</span>
            </div>
        `;
    }

    userDiv.innerHTML = `
        <div class="glass-panel bg-primary/10 border-primary/20 p-5 rounded-2xl rounded-tr-sm max-w-[80%] text-left">
            ${fileHtml}
            ${msg ? `<p class="text-white text-sm leading-relaxed">${msg}</p>` : ''}
        </div>
        <div class="size-10 rounded-full bg-slate-800 overflow-hidden ring-2 ring-primary/20 flex-shrink-0 border border-slate-700">
            <img class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBJ9sdm8_244EoCnYJGQNIq1QM6yLvnHim83dPKAjOVzgawj7Pr0T6G_PnXs4gabeWBvusAwjvuwPrIukX6r_jtK_MuDu9U7DcBUaZeSnXlS8zToT0IJJ8Mm6qKq5xZFczAaT4yJ2w5V7v0TVMmulw6UtioQ4QOr56kaACJb2h6kGZx7OnilP0j6nx1HFkd1bFYfU7Na802QLZb6e48__ceZq5x7VKYZHl5fg9R3IlqAWrqbz9nKpIROtuo-86-znip51rAdTL1sjw"/>
        </div>
    `;
    chatMessages.appendChild(userDiv);

    // Capture state & clear input
    const submittedFile = attachedFile;
    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.value = '';
    removeAttachment(); // Clear attachment state
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Show "Typing" indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'flex gap-4';
    typingDiv.innerHTML = `
        <div class="size-10 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 glow-blue border border-primary/30 mt-1">
            <span class="material-symbols-outlined text-primary text-xl">auto_awesome</span>
        </div>
        <div class="glass-panel p-5 rounded-2xl rounded-tl-sm max-w-2xl glow-blue flex items-center gap-2">
            <div class="size-2 rounded-full bg-slate-400 animate-bounce"></div>
            <div class="size-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0.1s"></div>
            <div class="size-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0.2s"></div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Call Nova AI Chat API
    apiFetch('/api/chat', { 
        message: msg, 
        history: chatHistory, 
        session_id: window.currentSessionId 
    }).then(data => {
        chatMessages.removeChild(typingDiv);

        // Add to history for context
        chatHistory.push({ role: 'user', content: msg });
        chatHistory.push({ role: 'assistant', content: data.reply });
        // Keep last 10 messages to avoid context overflow
        if (chatHistory.length > 10) chatHistory = chatHistory.slice(-10);

        const aiDiv = document.createElement('div');
        aiDiv.className = 'flex gap-4';

        // Sanitize reply and convert newlines to <br>
        const safeReply = data.reply
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>');

        aiDiv.innerHTML = `
            <div class="size-10 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 glow-magenta border border-accent-magenta/30 mt-1">
                <span class="material-symbols-outlined text-accent-magenta text-xl">auto_awesome</span>
            </div>
            <div class="glass-panel p-5 rounded-2xl rounded-tl-sm max-w-2xl glow-magenta text-left">
                <p class="text-white text-sm leading-relaxed">${safeReply}</p>
            </div>
        `;
        chatMessages.appendChild(aiDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Refresh sidebar
        loadChatHistory();
        
    }).catch(err => {
        chatMessages.removeChild(typingDiv);
        const errDiv = document.createElement('div');
        errDiv.className = 'flex gap-4';
        errDiv.innerHTML = `
            <div class="size-10 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0 border border-red-500/30 mt-1">
                <span class="material-symbols-outlined text-red-400 text-xl">error</span>
            </div>
            <div class="glass-panel p-5 rounded-2xl rounded-tl-sm max-w-2xl border-red-500/20">
                <p class="text-red-300 text-sm">AWS throttling or connection error, please wait.</p>
            </div>
        `;
        chatMessages.appendChild(errDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

// ----------------------------------------------------
// CHAT HISTORY & SIDEBAR FUNCTIONS
// ----------------------------------------------------

async function loadChatHistory() {
    const container = document.getElementById('sidebar-chat-history');
    if (!container) return;
    try {
        const res = await fetch('/api/chat-history');
        const data = await res.json();
        const grouped = data.grouped || {};
        
        container.innerHTML = '';
        let hasItems = false;
        
        // Check if there are any items
        for (const items of Object.values(grouped)) {
            if (items && items.length > 0) hasItems = true;
        }

        if(!hasItems) {
            container.innerHTML = '<p class="text-xs text-slate-500 pl-2">No previous chats.</p>';
            return;
        }

        let html = '';
        for (const [groupTitle, items] of Object.entries(grouped)) {
            if (!items || items.length === 0) continue;
            html += `<div class="mb-4">
                <h4 class="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2 mb-2">${groupTitle}</h4>
                <div class="space-y-1">
            `;
            html += items.map(item => `
                <div class="group relative flex items-center justify-between px-3 py-2 rounded-lg hover:bg-white/5 cursor-pointer text-slate-400 hover:text-white transition-colors" onclick="loadOldConversation('${item.session_id}')">
                    <span class="text-xs truncate pr-8 pointer-events-none w-full">${escapeHtml(item.snippet)}</span>
                    <button onclick="deleteConversation(event, '${item.session_id}')" title="Delete Chat" class="absolute right-2 p-1.5 bg-slate-800 hover:bg-red-500/20 rounded transition-all text-slate-500 hover:text-red-400 z-10 flex items-center justify-center opacity-40 group-hover:opacity-100 shadow-sm border border-slate-700/50">
                        <span class="material-symbols-outlined text-[14px]">delete</span>
                    </button>
                </div>
            `).join('');
            html += `</div></div>`;
        }
        container.innerHTML = html;
        
    } catch (e) {
        console.error('Failed to load chat history:', e);
    }
}

async function loadOldConversation(session_id) {
    switchToTab('dashboard');
    try {
        const res = await fetch(`/api/chat-session/${session_id}`);
        const data = await res.json();
        if(!data.messages) return;
        
        window.currentSessionId = session_id;
        chatHistory = [];
        
        const chatMessages = document.getElementById('chat-history');
        if (chatMessages) {
            // retain only the first welcome message
            const firstChild = chatMessages.firstElementChild;
            chatMessages.innerHTML = '';
            if (firstChild) chatMessages.appendChild(firstChild);
            
            data.messages.forEach(msg => {
                chatHistory.push({ role: msg.role, content: msg.message });
                const div = document.createElement('div');
                div.className = msg.role === 'user' ? 'flex gap-4 justify-end' : 'flex gap-4';
                
                const safeReply = (msg.message || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
                
                if (msg.role === 'user') {
                    div.innerHTML = `
                        <div class="glass-panel bg-primary/10 border-primary/20 p-5 rounded-2xl rounded-tr-sm max-w-[80%] text-left">
                            <p class="text-white text-sm leading-relaxed">${safeReply}</p>
                        </div>
                        <div class="size-10 rounded-full bg-slate-800 overflow-hidden ring-2 ring-primary/20 flex-shrink-0 border border-slate-700">
                            <img class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBJ9sdm8_244EoCnYJGQNIq1QM6yLvnHim83dPKAjOVzgawj7Pr0T6G_PnXs4gabeWBvusAwjvuwPrIukX6r_jtK_MuDu9U7DcBUaZeSnXlS8zToT0IJJ8Mm6qKq5xZFczAaT4yJ2w5V7v0TVMmulw6UtioQ4QOr56kaACJb2h6kGZx7OnilP0j6nx1HFkd1bFYfU7Na802QLZb6e48__ceZq5x7VKYZHl5fg9R3IlqAWrqbz9nKpIROtuo-86-znip51rAdTL1sjw"/>
                        </div>
                    `;
                } else {
                    div.innerHTML = `
                        <div class="size-10 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 glow-magenta border border-accent-magenta/30 mt-1">
                            <span class="material-symbols-outlined text-accent-magenta text-xl">auto_awesome</span>
                        </div>
                        <div class="glass-panel p-5 rounded-2xl rounded-tl-sm max-w-2xl glow-magenta text-left">
                            <p class="text-white text-sm leading-relaxed">${safeReply}</p>
                        </div>
                    `;
                }
                chatMessages.appendChild(div);
            });
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    } catch (e) {
        console.error('Failed to load chat:', e);
        alert("Failed to load conversation from history.");
    }
}

async function deleteConversation(event, session_id) {
    if(event) event.stopPropagation();
    try {
        await fetch(`/api/chat-session/${session_id}`, { method: 'DELETE' });
        loadChatHistory();
        if (session_id === window.currentSessionId) {
            startNewChat();
        }
    } catch (e) {
        console.error('Failed to delete chat:', e);
    }
}

function startNewChat() {
    window.currentSessionId = 'session_' + Date.now();
    chatHistory = [];
    switchToTab('dashboard'); // ensure we're looking at the chat
    
    const chatMessages = document.getElementById('chat-history');
    if (chatMessages) {
        // clear all except the very first welcome message bubble
        const firstChild = chatMessages.firstElementChild;
        chatMessages.innerHTML = '';
        if (firstChild) chatMessages.appendChild(firstChild);
    }
}

function proceedWithTitle(title) {
    videoData.title = title;
    // Switch to Script Studio 
    switchToTab('content-research');
    goToWizardStep(2);

    // Inject Title into the UI
    const projectTitleEl = document.getElementById('project-title-name');
    if (projectTitleEl) projectTitleEl.textContent = title;

    const editorVisual = document.getElementById('script-editor-visual');
    if (editorVisual) {
        const h2El = editorVisual.querySelector('h2');
        if (h2El) h2El.textContent = "Title: " + title;
    }

}

function submitChat() {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) sendChatMessage(chatInput.value);
}

function handleChatKeyPress(event) {
    // In textarea: Shift+Enter → new line, Enter → send.
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // stop adding a new line
        submitChat();
    }
}

function scrollToBottom() {
    const chatHistory = document.getElementById('chat-history');
    if (chatHistory) {
        chatHistory.scrollTo({
            top: chatHistory.scrollHeight,
            behavior: 'smooth'
        });
    }
}

// ----------------------------------------------------
// AI GENERATION FROM SCRIPT WRITER
// ----------------------------------------------------
async function generateScriptOnly(event) {
    const promptInput = document.getElementById('script-writer-prompt');
    const prompt = promptInput ? promptInput.value.trim() : "";
    if (!prompt) {
        alert("Please enter a video prompt or idea first!");
        return;
    }

    // Get selected tone
    const activeToneBtn = document.querySelector('.tone-btn.active-tone');
    const tone = (activeToneBtn && activeToneBtn.dataset.tone) ? activeToneBtn.dataset.tone : 'Educational';

    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin">cyclone</span> Generating Script...`;
    btn.disabled = true;

    try {
        const data = await apiFetch('/api/generate-script', { topic: prompt, tone, length_words: 250 });
        const textarea = document.getElementById('generated-script-textarea');
        if (textarea && data.script_content) {
            textarea.value = data.script_content;
        }
        // Store result in fullVideoKit for downstream tools
        if (!fullVideoKit) fullVideoKit = {};
        if (data.title) fullVideoKit.title = data.title;
        if (data.script_content) fullVideoKit.script_content = data.script_content;
    } catch (e) {
        alert('Script generation failed. AWS throttling, please wait.');
        console.error(e);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ----------------------------------------------------
// AI GENERATION FROM TITLE & SEO BOX
// ----------------------------------------------------
async function generateSeoDataOnly(event) {
    const promptInput = document.getElementById('seo-writer-prompt');
    const prompt = promptInput ? promptInput.value.trim() : "";
    if (!prompt) {
        alert("Please enter a topic to generate SEO data!");
        return;
    }

    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin">cyclone</span> Generating SEO Data...`;
    btn.disabled = true;

    // Show loading state in boxes
    const titleEl = document.getElementById('voiceover-title');
    const descEl = document.getElementById('voiceover-description');
    const tagsEl = document.getElementById('voiceover-tags');
    const kwEl = document.getElementById('voiceover-keywords');
    if (titleEl) titleEl.textContent = '⏳ Generating...';
    if (descEl) descEl.textContent = '⏳ Generating description...';
    if (tagsEl) tagsEl.innerHTML = '<span class="text-slate-500 text-sm">Generating tags...</span>';
    if (kwEl) kwEl.innerHTML = '<span class="text-slate-500 text-sm">Generating keywords...</span>';

    try {
        const data = await apiFetch('/api/generate-seo', { topic: prompt });

        // ── Fill the EXISTING HTML boxes directly ──────────────────────
        // Title box: show viral title + SEO title
        if (titleEl) {
            titleEl.innerHTML = `
                <span class="text-white text-xl font-black block mb-2">${escapeHtml(data.viral_title || '')}</span>
                <span class="text-xs font-bold text-primary uppercase tracking-wider">SEO Title</span>
                <span class="text-slate-300 text-base font-semibold block mt-1">${escapeHtml(data.seo_title || '')}</span>
            `;
        }

        // Description box: full 200+ word description
        if (descEl) {
            descEl.textContent = data.description || '';
        }

        // Tags box: pill badges for all 20 tags
        if (tagsEl) {
            const tags = Array.isArray(data.tags) ? data.tags : [];
            tagsEl.innerHTML = tags.map(t =>
                `<span class="px-3 py-1 bg-primary/10 border border-primary/20 text-primary text-xs font-bold rounded-lg">${escapeHtml(String(t))}</span>`
            ).join('');
        }

        // Keywords box: pill badges for all 20 keywords
        if (kwEl) {
            const kws = Array.isArray(data.keywords) ? data.keywords : [];
            kwEl.innerHTML = kws.map(k =>
                `<span class="px-3 py-1 bg-white/5 border border-white/10 text-slate-400 text-xs font-bold rounded-lg">${escapeHtml(String(k))}</span>`
            ).join('');
        }

        // Store in fullVideoKit for downstream tools
        if (!fullVideoKit) fullVideoKit = {};
        fullVideoKit.title = data.viral_title;
        fullVideoKit.description = data.description;
        fullVideoKit.tags = data.tags;
        fullVideoKit.keywords = data.keywords;

        // Scroll to show the results
        if (titleEl) titleEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (e) {
        alert('SEO generation failed: ' + (e.message || 'Check your connection and try again.'));
        console.error(e);
        if (titleEl) titleEl.textContent = '—';
        if (descEl) descEl.textContent = '—';
        if (tagsEl) tagsEl.textContent = '—';
        if (kwEl) kwEl.textContent = '—';
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function escapeHtml(text) {
    return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}



// ----------------------------------------------------
// AI GENERATION FROM THUMBNAIL
// ----------------------------------------------------
async function generateThumbnailDataOnly(event) {
    const promptInput = document.getElementById('thumbnail-writer-prompt');
    const prompt = promptInput ? promptInput.value.trim() : "";
    const styleSelect = document.getElementById('thumbnail-style-select');
    const style = styleSelect ? styleSelect.value : 'cinematic';

    if (!prompt) {
        alert("Please enter a visual idea for the thumbnail first!");
        return;
    }

    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin">cyclone</span> Generating Thumbnail...`;
    btn.disabled = true;

    try {
        const data = await apiFetch('/api/regenerate-thumbnail', { title: prompt, style });
        if (!fullVideoKit) fullVideoKit = {};
        fullVideoKit.thumbnail_url = data.thumbnail_url;
        populateThumbnailPage();
    } catch (e) {
        alert('Failed to generate thumbnail. AWS throttling, please wait.');
        console.error(e);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ----------------------------------------------------
// AI GENERATION FROM VOICE GENERATOR
// ----------------------------------------------------
async function generateVoiceover(event) {
    const promptInput = document.getElementById('voice-generator-script');
    const text = promptInput ? promptInput.value.trim() : "";

    if (!text) {
        alert("Please paste a script to generate a voiceover first!");
        return;
    }

    const btn = event.currentTarget;
    const outputArea = document.getElementById('vg-output-area');
    const audioPlayer = document.getElementById('vg-audio-player');

    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin">cyclone</span> Generating Voiceover...`;
    btn.disabled = true;

    if (outputArea) outputArea.classList.remove('hidden');

    // Determine Voice ID based on Language and Profile Selection
    const langSelect = document.querySelector('#view-voice-generator select');
    const lang = langSelect ? langSelect.value : 'en';
    
    let voice_id = 'Joanna'; // Default

    // If a non-English language is selected, force the corresponding native voice
    if (lang !== 'en' && lang !== 'en-gb') {
        const voiceMap = {
            'es': 'Lupe',       // Spanish
            'fr': 'Celine',     // French
            'de': 'Marlene',    // German
            'hi': 'Aditi'       // Hindi
        };
        voice_id = voiceMap[lang] || 'Lupe';
    } else {
        // Find selected profile from index.html / nova_funcs.js
        // nova_funcs.js stores it in a global 'selectedNovaProfile'
        const profile = typeof selectedNovaProfile !== 'undefined' ? selectedNovaProfile : 'nova_energetic';
        
        if (lang === 'en-gb') {
            voice_id = 'Amy'; // Force UK voice
        } else {
            // Map the custom UI profiles to actual AWS Polly voices
            const profileMap = {
                'nova_energetic': 'Justin',
                'nova_calm': 'Stephen',
                'emma_storyteller': 'Joanna',
                'marcus_educational': 'Matthew'
            };
            voice_id = profileMap[profile] || 'Joanna';
        }
    }

    try {
        const data = await apiFetch('/api/generate-audio', { text, voice_id });

        if (data.audio_base64 && audioPlayer) {
            audioPlayer.src = 'data:audio/mp3;base64,' + data.audio_base64;
            audioPlayer.load();
            
            // Set up event listeners for the custom player UI
            audioPlayer.onloadedmetadata = () => {
                document.getElementById('vg-time-total').textContent = formatTime(audioPlayer.duration);
            };
            audioPlayer.ontimeupdate = () => {
                document.getElementById('vg-time-current').textContent = formatTime(audioPlayer.currentTime);
                // Avoid divide by zero if duration is 0
                if (audioPlayer.duration > 0) {
                    const percent = (audioPlayer.currentTime / audioPlayer.duration) * 100;
                    document.getElementById('vg-progress-bar').style.width = `${percent}%`;
                }
            };
            audioPlayer.onended = () => {
                const playIcon = document.getElementById('vg-play-icon');
                if (playIcon) playIcon.textContent = 'play_arrow';
                // Stop animation
                if (window.waveformInterval) clearInterval(window.waveformInterval);
                const waveformBars = document.querySelectorAll('#vg-waveform .waveform-bar');
                const heights = [40,70,55,90,45,75,60,100,50,80,65,40,85,55,70,95,60,75,45,88];
                waveformBars.forEach((bar, i) => { 
                    bar.style.height = (heights[i % heights.length]) + '%'; 
                });
            };

            // Reset UI state
            document.getElementById('vg-progress-bar').style.width = '0%';
            document.getElementById('vg-time-current').textContent = '0:00';
            const playIcon = document.getElementById('vg-play-icon');
            if (playIcon) playIcon.textContent = 'play_arrow';
            
            if (window.waveformInterval) clearInterval(window.waveformInterval);
            const waveformBars = document.querySelectorAll('#vg-waveform .waveform-bar');
            const heights = [40,70,55,90,45,75,60,100,50,80,65,40,85,55,70,95,60,75,45,88];
            waveformBars.forEach((bar, i) => { bar.style.height = (heights[i % heights.length]) + '%'; });

            // Output summary info text
            const infoText = document.querySelector('#vg-output-area p.text-slate-400');
            if (infoText) {
                const langLabel = langSelect ? langSelect.options[langSelect.selectedIndex].text : 'English (US)';
                const actualProfile = typeof selectedNovaProfile !== 'undefined' ? selectedNovaProfile : 'nova_energetic';
                const profileLabel = actualProfile.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                infoText.innerHTML = `${profileLabel} &bull; ${langLabel} &bull; Ready`;
            }

            // Store for download later
            window._lastAudioB64 = data.audio_base64;
        }

        btn.innerHTML = `<span class="material-symbols-outlined">restart_alt</span> Regenerate Voiceover`;
        btn.disabled = false;

        if (outputArea) {
            outputArea.classList.remove('hidden');
            outputArea.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    } catch (e) {
        alert('Voiceover generation failed. AWS throttling, please wait.');
        console.error(e);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Custom Player Controls
window.waveformInterval = null;

function toggleVoicePlay() {
    const audioPlayer = document.getElementById('vg-audio-player');
    const playIcon = document.getElementById('vg-play-icon');
    
    if (!audioPlayer) {
        alert('No audio player found!');
        return;
    }
    
    if (!audioPlayer.src || audioPlayer.src === window.location.href) {
        alert('Please generate a voiceover first!');
        return;
    }
    
    if (audioPlayer.paused) {
        audioPlayer.play().then(() => {
            if (playIcon) playIcon.textContent = 'pause';
        }).catch(err => {
            console.error('Play failed:', err);
            alert('Could not play audio: ' + err.message);
        });
    } else {
        audioPlayer.pause();
        if (playIcon) playIcon.textContent = 'play_arrow';
    }
}

function seekVoicePlay(event) {
    const audioPlayer = document.getElementById('vg-audio-player');
    const container = document.getElementById('vg-progress-container');
    
    if (!audioPlayer || !audioPlayer.src || !audioPlayer.duration) return;

    const rect = container.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const width = rect.width;
    const percent = clickX / width;
    
    audioPlayer.currentTime = percent * audioPlayer.duration;
}

function formatTime(seconds) {
    if (isNaN(seconds)) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function downloadVoiceover() {
    // Download real audio if we have it, else fallback
    if (window._lastAudioB64) {
        const a = document.createElement('a');
        a.href = 'data:audio/mp3;base64,' + window._lastAudioB64;
        a.download = 'Nova_Voiceover.mp3';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } else {
        alert('No voiceover generated yet. Please generate one first.');
    }

    const btn = document.getElementById('vg-download-btn');
    if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '<span class="material-symbols-outlined text-[20px] text-green-400">check</span>';
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
    }
}

// ----------------------------------------------------
// AI GENERATION FROM SCENES PAGE - Chat Interface
// ----------------------------------------------------
let scenesChatHistory = [];
let localScenesCount = 0;

function clearScenesChat() {
    scenesChatHistory = [];
    localScenesCount = 0;
    if(fullVideoKit) fullVideoKit.scenes = [];
    
    document.getElementById('scenes-chat-window').innerHTML = `
        <div class="flex gap-4">
            <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-blue-500 flex items-center justify-center shrink-0 shadow-lg">
                <span class="material-symbols-outlined text-white text-[18px]">smart_toy</span>
            </div>
            <div class="bg-slate-700/30 border border-slate-600/50 text-slate-200 px-5 py-3.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed shadow-sm max-w-[90%]">
                <p class="mb-2 font-medium">Hi! I'm your AI Scene Director. 🎬</p>
                <p>Tell me what kind of cinematic scene you want to generate. For example:</p>
                <p class="text-slate-400 italic mt-2 text-xs">"Generate a dark cinematic establishing shot of a futuristic cyberpunk city raining at night."</p>
            </div>
        </div>
    `;
    updateScenesChatGrid();
}

async function generateScenesFromScript() {
    const inputEl = document.getElementById('scenes-script-input');
    const btn = document.getElementById('generate-scenes-btn');
    const script = inputEl ? inputEl.value.trim() : "";

    if (!script) {
        alert("Please paste your script or lyrics first!");
        return;
    }

    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin">cyclone</span> Analyzing Script...`;
    btn.disabled = true;

    // Clear grid and show loading state
    const grid = document.getElementById('scenes-chat-grid');
    grid.innerHTML = `
        <div class="w-full py-20 flex flex-col items-center justify-center border-2 border-dashed border-primary/30 rounded-2xl bg-primary/5">
            <span class="material-symbols-outlined text-6xl text-primary mb-4 animate-spin">cyclone</span>
            <h3 class="text-xl font-bold text-white">Generating Scenes...</h3>
            <p class="text-sm text-slate-400 mt-2">AI is analyzing your script and rendering cinematic shots.</p>
        </div>
    `;

    try {
        const data = await apiFetch('/api/generate-scenes', { script });
        
        if (data.scenes && data.scenes.length > 0) {
            if (!fullVideoKit) fullVideoKit = {};
            fullVideoKit.scenes = data.scenes;
            updateScenesChatGrid();
            
            // Show success message if there's a chat or toast system, otherwise just update grid
            console.log("Scenes generated successfully!");
        } else {
            alert("No scenes were generated. Please try again.");
            updateScenesChatGrid();
        }
    } catch (err) {
        console.error(err);
        alert("Error generating scenes. AWS might be throttled. Please try again in 30 seconds.");
        updateScenesChatGrid();
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}


function updateScenesChatGrid() {
    const grid = document.getElementById('scenes-chat-grid');
    if(!grid) return;
    
    if(!fullVideoKit || !fullVideoKit.scenes || fullVideoKit.scenes.length === 0) {
        grid.innerHTML = `
            <div id="scenes-empty-state" class="w-full py-20 flex flex-col items-center justify-center border-2 border-dashed border-slate-700/50 rounded-2xl bg-slate-800/20">
                <span class="material-symbols-outlined text-6xl text-slate-600 mb-4 animate-pulse">image</span>
                <h3 class="text-xl font-bold text-slate-400">No Scenes Yet</h3>
                <p class="text-sm text-slate-500 mt-2">Enter your script on the left and click "Generate Matching Scenes".</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = fullVideoKit.scenes.map((scene, i) => `
        <div class="flex flex-col md:flex-row gap-6 bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 hover:border-primary/30 transition-all group shadow-sm">
            <div class="relative w-full md:w-80 shrink-0 aspect-video rounded-lg overflow-hidden border border-slate-700/50 shadow-inner bg-black">
                <img src="${scene.img}" class="w-full h-full object-cover" onerror="this.src='https://picsum.photos/1280/720?random=${i}'">
                <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center p-3">
                    <button onclick="downloadSpecificScene('${scene.img}', ${i})" class="bg-primary/90 hover:bg-primary text-white text-xs font-bold py-1.5 px-3 rounded-lg backdrop-blur shadow-lg flex items-center gap-1">
                        <span class="material-symbols-outlined text-[14px]">download</span> Download
                    </button>
                </div>
            </div>
            <div class="flex flex-col flex-1 justify-between">
                <div>
                    <div class="flex justify-between items-start mb-2">
                        <span class="inline-flex items-center gap-1.5 text-xs font-bold bg-slate-900/50 border border-slate-700 text-slate-300 px-2.5 py-1 rounded-full uppercase tracking-wider">
                            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span> Scene ${scene.id || (i+1)}
                        </span>
                        <div class="flex gap-2">
                            <button onclick="regenerateSpecificScene(${i})" class="w-8 h-8 rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600 hover:text-white flex items-center justify-center transition" title="Regenerate">
                                <span class="material-symbols-outlined text-[16px]">refresh</span>
                            </button>
                            <button onclick="deleteSpecificScene(${i})" class="w-8 h-8 rounded-lg bg-slate-700 text-slate-300 hover:bg-red-500/20 hover:text-red-400 flex items-center justify-center transition" title="Delete">
                                <span class="material-symbols-outlined text-[16px]">delete</span>
                            </button>
                        </div>
                    </div>
                    <p class="text-sm text-slate-300 leading-relaxed font-medium mt-3 border-l-2 border-primary/50 pl-4 py-1 italic">
                        "${scene.text}"
                    </p>
                </div>
            </div>
        </div>
    `).join('');
}

function downloadSpecificScene(base64Data, index) {
    if (!base64Data.startsWith('data:')) {
        window.open(base64Data, '_blank');
        return;
    }
    const a = document.createElement('a');
    a.href = base64Data;
    a.download = `Nova_Scene_${index+1}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

async function regenerateSpecificScene(index) {
    if(!fullVideoKit || !fullVideoKit.scenes || !fullVideoKit.scenes[index]) return;
    
    const sceneObj = fullVideoKit.scenes[index];
    const prompt = sceneObj.text;
    
    // Save original image to restore if failure
    const originalImg = sceneObj.img;
    sceneObj.img = 'https://i.ibb.co/L5hY5M0/loading-Placeholder.gif'; // Temporary loading graphic
    updateScenesChatGrid();

    try {
        const data = await apiFetch('/api/generate-scenes', { script: prompt });
        if(data && data.scenes && data.scenes.length > 0) {
            fullVideoKit.scenes[index].img = data.scenes[0].img;
        } else {
            fullVideoKit.scenes[index].img = originalImg;
            alert('Regeneration empty. Original restored.');
        }
    } catch(err) {
        console.error(err);
        fullVideoKit.scenes[index].img = originalImg;
        alert('Regeneration failed. Original restored.');
    }
    updateScenesChatGrid();
}

function deleteSpecificScene(index) {
    if(confirm('Are you sure you want to delete this scene?')) {
        fullVideoKit.scenes.splice(index, 1);
        updateScenesChatGrid();
    }
}