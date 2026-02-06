/**
 * Gödel Tab: Diagnostics for startup_agent ↔ host and mindXagent ↔ Ollama
 *
 * Displays on screen:
 * - Startup Agent ↔ Host: sequence, terminal log, Ollama connection input/response
 * - mindXagent ↔ Ollama: conversation dialogue and inference status
 *
 * @module GodelTab
 */

class GodelTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'godel',
            label: 'Gödel',
            group: 'main',
            refreshInterval: 8000,
            autoRefresh: true,
            ...config
        });
        this.startupData = null;
        this.conversationData = null;
        this.choicesData = null;
    }

    async initialize() {
        await super.initialize();
        this.setupEventListeners();
        console.log('✅ GodelTab initialized');
        return true;
    }

    async onActivate() {
        await super.onActivate();
        await this.loadDiagnostics();
        return true;
    }

    setupEventListeners() {
        const refreshBtn = document.getElementById('godel-diagnostics-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadDiagnostics());
        }
    }

    async loadDiagnostics() {
        const base = window.__MINDX_API_BASE__ || '';
        const container = document.getElementById('godel-diagnostics-output');
        if (!container) return;
        container.innerHTML = '<p class="godel-loading">Loading diagnostics…</p>';
        try {
            const [startupRes, convRes, choicesRes] = await Promise.all([
                fetch(`${base}/mindxagent/startup`).then(r => r.json()).catch(() => ({})),
                fetch(`${base}/mindxagent/ollama/conversation?limit=30`).then(r => r.json()).catch(() => ({})),
                fetch(`${base}/godel/choices?limit=50`).then(r => r.json()).catch(() => ({}))
            ]);
            this.startupData = startupRes;
            this.conversationData = convRes;
            this.choicesData = choicesRes;
            this.renderDiagnostics(container);
        } catch (e) {
            container.innerHTML = '<p class="godel-error">Failed to load diagnostics.</p>';
        }
    }

    renderDiagnostics(container) {
        const frag = document.createDocumentFragment();

        // 1. Startup Agent ↔ Host
        const sec1 = document.createElement('section');
        sec1.className = 'godel-section';
        sec1.innerHTML = '<h2 class="godel-section-title">Startup Agent ↔ Host</h2>';
        const hostOut = document.createElement('div');
        hostOut.className = 'godel-diagnostics-block godel-host-block';
        hostOut.appendChild(this.renderStartupDiagnostics());
        sec1.appendChild(hostOut);
        frag.appendChild(sec1);

        // 2. mindXagent ↔ Ollama dialogue
        const sec2 = document.createElement('section');
        sec2.className = 'godel-section';
        sec2.innerHTML = '<h2 class="godel-section-title">mindXagent ↔ Ollama</h2>';
        const ollamaOut = document.createElement('div');
        ollamaOut.className = 'godel-diagnostics-block godel-ollama-block';
        ollamaOut.appendChild(this.renderOllamaDialogue());
        sec2.appendChild(ollamaOut);
        frag.appendChild(sec2);

        // 3. Core choices audit log (perception, options, chosen, why, outcome)
        const sec3 = document.createElement('section');
        sec3.className = 'godel-section';
        sec3.innerHTML = '<h2 class="godel-section-title">Core choices audit</h2><p class="godel-section-desc">Single log: what was perceived, options considered, chosen, why, outcome.</p>';
        const choicesOut = document.createElement('div');
        choicesOut.className = 'godel-diagnostics-block godel-choices-block';
        choicesOut.appendChild(this.renderRecentChoices());
        sec3.appendChild(choicesOut);
        frag.appendChild(sec3);

        container.innerHTML = '';
        container.appendChild(frag);
    }

    renderStartupDiagnostics() {
        const wrap = document.createElement('div');
        const d = this.startupData || {};
        const seq = d.startup_sequence || [];
        const rec = d.startup_record || {};
        const ollamaIO = d.ollama_input_response || {};
        const term = d.terminal_log || {};
        const info = d.startup_info || {};

        let html = '<div class="godel-subsection"><h3>Startup sequence</h3><pre class="godel-pre">';
        if (seq.length) {
            seq.forEach(s => {
                html += `${s.step || ''} ${s.name || ''}: ${s.status || ''}\n`;
            });
        } else {
            html += 'No sequence data yet.';
        }
        html += '</pre></div>';

        html += '<div class="godel-subsection"><h3>Ollama connection (startup_agent → host)</h3><pre class="godel-pre">';
        html += `Connected: ${ollamaIO.connected !== undefined ? ollamaIO.connected : 'N/A'}\n`;
        html += `Base URL: ${ollamaIO.base_url || '—'}\n`;
        html += `Models: ${(ollamaIO.models && ollamaIO.models.length) ? ollamaIO.models.join(', ') : (ollamaIO.models_count || '—')}\n`;
        if (ollamaIO.reason) html += `Reason: ${ollamaIO.reason}\n`;
        html += '</pre></div>';

        html += '<div class="godel-subsection"><h3>mindXagent startup_info (from startup_agent)</h3><pre class="godel-pre">';
        html += `Ollama connected: ${info.ollama_connected !== undefined ? info.ollama_connected : 'N/A'}\n`;
        html += `Base URL: ${info.ollama_base_url || '—'}\n`;
        html += `Models count: ${info.models_count ?? '—'}\n`;
        if (info.terminal_log_summary) {
            html += `Terminal log: exists=${info.terminal_log_summary.log_exists}, errors=${info.terminal_log_summary.errors_count ?? 0}, warnings=${info.terminal_log_summary.warnings_count ?? 0}\n`;
        }
        html += '</pre></div>';

        if (term.log_exists && term.last_lines && term.last_lines.length) {
            html += '<div class="godel-subsection"><h3>Terminal startup log (last lines)</h3><pre class="godel-pre godel-log">';
            html += term.last_lines.slice(-25).map(l => escapeText(l)).join('');
            html += '</pre></div>';
        }

        wrap.innerHTML = html;
        return wrap;
    }

    renderOllamaDialogue() {
        const wrap = document.createElement('div');
        const d = this.conversationData || {};
        const messages = d.messages || d.conversation || [];
        let html = '<div class="godel-subsection"><h3>Conversation (mindXagent ↔ Ollama)</h3>';
        if (!messages.length) {
            html += '<p class="godel-muted">No conversation messages yet.</p>';
        } else {
            html += '<div class="godel-conversation">';
            messages.slice(-20).forEach(m => {
                const role = (m.role || m.type || 'user');
                const content = (m.content || m.text || m.message || JSON.stringify(m)).slice(0, 800);
                html += `<div class="godel-msg godel-msg-${role}"><span class="godel-msg-role">${escapeText(role)}</span><pre class="godel-msg-content">${escapeText(content)}</pre></div>`;
            });
            html += '</div>';
        }
        html += '</div>';
        wrap.innerHTML = html;
        return wrap;
    }

    renderRecentChoices() {
        const wrap = document.createElement('div');
        const d = this.choicesData || {};
        const choices = d.choices || [];
        let html = '<pre class="godel-pre">';
        if (!choices.length) {
            html += 'No core choices recorded yet.';
        } else {
            choices.forEach(c => {
                const t = c.timestamp_utc || c.timestamp || '';
                const src = c.source_agent || '';
                const typ = c.choice_type || '';
                const opt = (c.chosen_option != null ? String(c.chosen_option) : '').slice(0, 60);
                html += `[${t}] ${src} | ${typ} | ${escapeText(opt)}\n`;
            });
        }
        html += '</pre>';
        wrap.innerHTML = html;
        return wrap;
    }
}

function escapeText(s) {
    if (s == null) return '';
    const t = String(s);
    return t
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
