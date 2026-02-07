/**
 * Gödel Tab: Single log of core choices (perception → options → chosen → rationale → outcome).
 * Shows whether mindX is a Gödel machine. Data from startup_agent (Ollama when no API)
 * and mindXagent↔Ollama (chosen inference/model). Also shows Startup Agent↔Host and
 * mindXagent↔Ollama dialogue.
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
                fetch(`${base}/mindxagent/startup`).then(r => r.ok ? r.json() : {}).catch(() => ({})),
                fetch(`${base}/mindxagent/ollama/conversation?limit=30`).then(r => r.ok ? r.json() : {}).catch(() => ({})),
                fetch(`${base}/godel/choices?limit=50`).then(async (r) => {
                    if (!r.ok) return { choices: [], total: 0, error: r.statusText || 'Request failed' };
                    try { return await r.json(); } catch (_) { return { choices: [], total: 0, error: 'Invalid response' }; }
                }).catch((e) => ({ choices: [], total: 0, error: e && e.message ? e.message : 'Network error' }))
            ]);
            this.startupData = startupRes;
            this.conversationData = convRes;
            this.choicesData = choicesRes && typeof choicesRes === 'object' ? choicesRes : { choices: [], total: 0 };
            this.renderDiagnostics(container);
            container.setAttribute('data-godel-complete', 'true');
        } catch (e) {
            container.innerHTML = '<p class="godel-error">Failed to load diagnostics. <button type="button" class="control-btn godel-inline-refresh">Refresh</button></p>';
            const btn = container.querySelector('.godel-inline-refresh');
            if (btn) btn.addEventListener('click', () => this.loadDiagnostics());
        }
    }

    renderDiagnostics(container) {
        const frag = document.createDocumentFragment();

        // 1. Core choices audit first: single log (perception → options → chosen → rationale → outcome)
        const secChoices = document.createElement('section');
        secChoices.className = 'godel-section godel-section-choices';
        secChoices.innerHTML = '<h2 class="godel-section-title">Core choices audit</h2><p class="godel-section-desc">Single log: <strong>perception → options → chosen → rationale → outcome</strong>. Data from startup_agent (Ollama when no API) and mindXagent↔Ollama (chosen inference/model).</p>';
        const choicesOut = document.createElement('div');
        choicesOut.className = 'godel-diagnostics-block godel-choices-block';
        choicesOut.appendChild(this.renderRecentChoices());
        secChoices.appendChild(choicesOut);
        frag.appendChild(secChoices);

        // 2. Startup Agent ↔ Host
        const sec1 = document.createElement('section');
        sec1.className = 'godel-section';
        sec1.innerHTML = '<h2 class="godel-section-title">Startup Agent ↔ Host</h2>';
        const hostOut = document.createElement('div');
        hostOut.className = 'godel-diagnostics-block godel-host-block';
        hostOut.appendChild(this.renderStartupDiagnostics());
        sec1.appendChild(hostOut);
        frag.appendChild(sec1);

        // 3. mindXagent ↔ Ollama dialogue
        const sec2 = document.createElement('section');
        sec2.className = 'godel-section';
        sec2.innerHTML = '<h2 class="godel-section-title">mindXagent ↔ Ollama</h2>';
        const ollamaOut = document.createElement('div');
        ollamaOut.className = 'godel-diagnostics-block godel-ollama-block';
        ollamaOut.appendChild(this.renderOllamaDialogue());
        sec2.appendChild(ollamaOut);
        frag.appendChild(sec2);

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
        const err = d.error;

        if (err) {
            wrap.innerHTML = '<p class="godel-error">Could not load core choices: ' + escapeText(err) + '. Ensure backend is running and <button type="button" class="control-btn godel-inline-refresh">Refresh</button>.</p>';
            const btn = wrap.querySelector('.godel-inline-refresh');
            if (btn) btn.addEventListener('click', () => this.loadDiagnostics());
            return wrap;
        }

        if (!choices.length) {
            wrap.innerHTML = '<p class="godel-muted godel-empty-desc">No core choices recorded yet. Choices appear when: startup_agent runs (Ollama bootstrap/improvement when no API), and mindXagent selects inference or model (e.g. Ollama). Run a directive or wait for startup to log choices.</p>';
            return wrap;
        }

        const list = document.createElement('div');
        list.className = 'godel-choices-list';
        choices.forEach((c, i) => {
            const card = document.createElement('div');
            card.className = 'godel-choice-card';
            const t = c.timestamp_utc || c.timestamp || '';
            const timeLabel = t ? new Date(t).toLocaleString() : '—';
            const src = escapeText(c.source_agent || '—');
            const typ = escapeText(c.choice_type || '—');
            const perception = escapeText((c.perception_summary != null ? String(c.perception_summary) : '').slice(0, 400));
            const options = c.options_considered;
            const optionsStr = Array.isArray(options) ? options.map(o => escapeText(String(o).slice(0, 80))).join(', ') : escapeText(String(options || '').slice(0, 200));
            const chosen = escapeText((c.chosen_option != null ? String(c.chosen_option) : '—').slice(0, 300));
            const rationale = escapeText((c.rationale != null ? String(c.rationale) : '').slice(0, 400));
            const outcome = escapeText((c.outcome != null ? String(c.outcome) : '').slice(0, 200));
            const llm = c.llm_model ? escapeText(String(c.llm_model)) : '';

            card.innerHTML =
                '<div class="godel-choice-meta">' +
                    '<span class="godel-choice-time">' + timeLabel + '</span> ' +
                    '<span class="godel-choice-source">' + src + '</span> ' +
                    '<span class="godel-choice-type">' + typ + '</span>' +
                    (llm ? ' <span class="godel-choice-llm">' + llm + '</span>' : '') +
                '</div>' +
                (perception ? '<div class="godel-choice-row"><span class="godel-choice-label">Perception</span><div class="godel-choice-value">' + perception + '</div></div>' : '') +
                (optionsStr ? '<div class="godel-choice-row"><span class="godel-choice-label">Options considered</span><div class="godel-choice-value">' + optionsStr + '</div></div>' : '') +
                '<div class="godel-choice-row"><span class="godel-choice-label">Chosen</span><div class="godel-choice-value">' + chosen + '</div></div>' +
                (rationale ? '<div class="godel-choice-row"><span class="godel-choice-label">Rationale</span><div class="godel-choice-value">' + rationale + '</div></div>' : '') +
                (outcome ? '<div class="godel-choice-row"><span class="godel-choice-label">Outcome</span><div class="godel-choice-value">' + outcome + '</div></div>' : '');
            list.appendChild(card);
        });
        wrap.appendChild(list);
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

if (typeof window !== 'undefined') {
    window.GodelTab = GodelTab;
}
