// ============================================================
// NOVA UI INTERACTIVITY - Toast, Aspect Ratio, Profile, etc.
// ============================================================

// =========================
// TOAST NOTIFICATION SYSTEM
// =========================
function showToast(message, icon = 'check_circle') {
    // Remove any existing toast
    document.querySelectorAll('.nova-toast').forEach(t => t.remove());
    const toast = document.createElement('div');
    toast.className = 'nova-toast';
    toast.innerHTML = `<span class="material-symbols-outlined toast-icon">${icon}</span> ${message}`;
    document.body.appendChild(toast);
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 3200);
}

// =========================
// NOVA CANVAS: ASPECT RATIO TOGGLE
// =========================
let currentRatio = '16:9';
function setAspectRatio(ratio, btnEl) {
    currentRatio = ratio;
    const preview = document.getElementById('thumbnail-preview-wrap');
    if (!preview) return;

    // Remove all ratio classes, reset styles
    preview.classList.remove('aspect-16-9', 'aspect-1-1', 'aspect-9-16');
    preview.style.aspectRatio = ''; // clear inline

    if (ratio === '16:9') {
        preview.classList.add('aspect-16-9');
    } else if (ratio === '1:1') {
        preview.classList.add('aspect-1-1');
    } else if (ratio === '9:16') {
        preview.classList.add('aspect-9-16');
    }

    // Update all ratio buttons: remove active, re-add to selected
    document.querySelectorAll('.ratio-btn').forEach(b => {
        b.classList.remove('ratio-btn-active', 'bg-accent-pink', 'text-white', 'border-accent-pink');
        b.classList.add('bg-white/5', 'text-slate-400', 'border-white/10');
    });
    if (btnEl) {
        btnEl.classList.add('ratio-btn-active', 'bg-accent-pink', 'text-white', 'border-accent-pink');
        btnEl.classList.remove('bg-white/5', 'text-slate-400', 'border-white/10');
    }

    // Update label text
    const label = document.querySelector('#view-thumbnail .text-accent-pink.uppercase');
    if (label) {
        const ratioMap = { '16:9': '16:9', '1:1': '1:1', '9:16': '9:16' };
        label.textContent = `Nova Canvas · ${ratioMap[ratio] || '16:9'}`;
    }

    showToast(`Aspect ratio set to ${ratio}`, 'aspect_ratio');
}

// =========================
// NOVA VOICE LAB: PROFILE SELECTION
// =========================
let selectedNovaProfile = 'nova_energetic';
function selectNovaProfile(cardEl, profileId) {
    selectedNovaProfile = profileId;

    // Reset all profile cards
    document.querySelectorAll('[onclick^="selectNovaProfile"]').forEach(c => {
        c.classList.remove('glow-magenta');
        c.style.borderColor = '';
        const badge = c.querySelector('[class*="absolute"]');
        if (badge && badge.classList.contains('top-3')) badge.style.display = 'none';
        c.querySelectorAll('.waveform-bar').forEach(bar => {
            bar.style.background = '#4b5563';
            bar.classList.remove('animate-pulse');
        });
    });

    // Highlight selected
    cardEl.classList.add('glow-magenta');
    cardEl.style.borderColor = 'rgba(217, 70, 239, 0.4)';
    const badge = cardEl.querySelector('[class*="absolute"]');
    if (badge && badge.classList.contains('top-3')) badge.style.display = 'flex';
    cardEl.querySelectorAll('.waveform-bar').forEach(bar => {
        bar.style.background = '#ff9900';
        bar.classList.add('animate-pulse');
    });

    const profileNames = {
        'nova_energetic': 'Nova Energetic',
        'nova_calm': 'Nova Calm',
        'emma_storyteller': 'Emma (Storyteller)',
        'marcus_educational': 'Marcus (Educational)'
    };
    showToast(`Selected: ${profileNames[profileId] || profileId}`, 'record_voice_over');
}


// =========================
// NOVA CANVAS: DOWNLOAD THUMBNAIL
// =========================
function downloadThumbnail() {
    const img = document.getElementById('thumbnail-preview-img');
    if (!img || !img.src || img.classList.contains('hidden')) {
        showToast('No canvas generated yet!', 'warning');
        return;
    }
    const a = document.createElement('a');
    a.href = img.src;
    a.download = 'nova-canvas-thumbnail.jpg';
    a.target = '_blank';
    a.click();
    showToast('Downloading thumbnail...', 'download');
}

// =========================
// NOVA VOICE LAB: SEND TO PRODUCTION
// =========================
function sendToProduction() {
    const btn = document.querySelector('[onclick="sendToProduction()"]');
    if (!btn) return;
    const original = btn.innerHTML;
    btn.innerHTML = '<span class="material-symbols-outlined">check_circle</span> Added to Production Queue!';
    btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
    showToast('Voice sent to production queue!', 'rocket_launch');
    setTimeout(() => {
        btn.innerHTML = original;
        btn.style.background = 'linear-gradient(135deg, #ff9900, #ff6600)';
    }, 3000);
}

// =========================
// SCRIPT WRITER: TONE SELECTION
// =========================
function selectScriptTone(btnEl, tone) {
    // Reset all tone buttons
    document.querySelectorAll('.tone-btn').forEach(btn => {
        btn.classList.remove('bg-primary/20', 'text-primary', 'border-primary');
        btn.classList.add('bg-slate-800', 'text-slate-400', 'border-transparent');
    });
    // Set active style
    btnEl.classList.add('bg-primary/20', 'text-primary', 'border-primary');
    btnEl.classList.remove('bg-slate-800', 'text-slate-400', 'border-transparent');
    showToast(`Tone set to: ${tone}`, 'style');
}

// =========================
// SCRIPT WRITER: COPY SCRIPT
// =========================
function copyScript() {
    const textarea = document.getElementById('generated-script-textarea');
    if (!textarea || !textarea.value.trim()) {
        showToast('Nothing to copy!', 'warning');
        return;
    }
    navigator.clipboard.writeText(textarea.value).then(() => {
        showToast('Script copied to clipboard!', 'content_copy');
    }).catch(err => {
        console.error('Copy failed', err);
        showToast('Failed to copy', 'error');
    });
}

// =========================
// SCRIPT WRITER: CLEAR SCRIPT
// =========================
function clearScript() {
    const textarea = document.getElementById('generated-script-textarea');
    if (textarea) {
        textarea.value = '';
        showToast('Script cleared', 'delete');
    }
}

// ============================================================
// GLOBAL INTERACTIVITY INIT (runs on page load)
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Nova AI Studio - UI Interactivity Loaded');

    // ---- Set Dashboard as active tab on load ----
    const dashNav = document.getElementById('nav-dashboard');
    if (dashNav) {
        dashNav.classList.add('sidebar-item-active', 'bg-primary/10', 'text-primary');
        dashNav.classList.remove('text-slate-400');
    }

    // ---- Make ratio buttons functional ----
    const ratioBtns = document.querySelectorAll('#view-thumbnail .ratio-btn');
    // If no .ratio-btn class, find them by content text
    if (ratioBtns.length === 0) {
        document.querySelectorAll('#view-thumbnail button').forEach(btn => {
            const text = btn.textContent.trim();
            if (text.includes('16:9')) {
                btn.classList.add('ratio-btn', 'ratio-btn-active');
                btn.addEventListener('click', () => setAspectRatio('16:9', btn));
            } else if (text.includes('1:1')) {
                btn.classList.add('ratio-btn');
                btn.addEventListener('click', () => setAspectRatio('1:1', btn));
            } else if (text.includes('9:16')) {
                btn.classList.add('ratio-btn');
                btn.addEventListener('click', () => setAspectRatio('9:16', btn));
            }
        });
    }

    // ---- Add click feedback to all generic buttons without explicit onclick ----
    document.querySelectorAll('button').forEach(btn => {
        if (!btn.hasAttribute('onclick') && !btn.dataset.hasListener) {
            btn.dataset.hasListener = 'true';
            btn.addEventListener('click', () => {
                const btnText = btn.textContent.trim().substring(0, 40);
                if (btnText) {
                    console.log(`[Nova UI] Button clicked: "${btnText}"`);
                }
            });
        }
    });

    // ---- Gender Filter Toggle (Voice Lab) ----
    const genderContainer = document.querySelector('#view-voice-generator .flex.bg-surface-dark');
    if (genderContainer) {
        genderContainer.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                genderContainer.querySelectorAll('button').forEach(b => {
                    b.classList.remove('bg-accent-magenta/20', 'text-white');
                    b.classList.add('text-slate-400');
                });
                btn.classList.add('bg-accent-magenta/20', 'text-white');
                btn.classList.remove('text-slate-400');
                showToast(`Filter: ${btn.textContent.trim()}`, 'filter_alt');
            });
        });
    }

    // ---- Style Preset change toast ----
    const styleSelect = document.getElementById('thumbnail-style-select');
    if (styleSelect) {
        styleSelect.addEventListener('change', () => {
            const v = styleSelect.options[styleSelect.selectedIndex].text;
            showToast(`Style: ${v}`, 'palette');
        });
    }

    // ---- Language select toast (Voice Lab) ----
    document.querySelectorAll('#view-voice-generator select').forEach(sel => {
        sel.addEventListener('change', () => {
            showToast(`Language: ${sel.options[sel.selectedIndex].text}`, 'translate');
        });
    });

    console.log('✅ All UI interactivity handlers attached');
});
