document.addEventListener('DOMContentLoaded', () => {
    // ═══════════════════════════════════════
    // CONFIG
    // ═══════════════════════════════════════
    const API_BASE = window.location.origin;
    const API_KEY = "test-api-key-change-me";

    // ═══════════════════════════════════════
    // DOM REFERENCES
    // ═══════════════════════════════════════
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    const queryInput = document.getElementById('queryInput');
    const btnSearch = document.getElementById('btnSearch');
    const loaderWrapper = document.getElementById('loaderWrapper');
    const responseContainer = document.getElementById('responseContainer');
    const answerBox = document.getElementById('answerBox');
    const citationsGrid = document.getElementById('citationsGrid');
    const btnCopy = document.getElementById('btnCopy');
    const rewrittenQueryBox = document.getElementById('rewrittenQueryBox');

    const kbSelect = document.getElementById('kbSelect');
    const uploadKbSelect = document.getElementById('uploadKbSelect');
    const scopeRadios = document.getElementsByName('search_scope');
    const actFilter = document.getElementById('actFilter');
    const toggleReranker = document.getElementById('toggleReranker');
    const toggleRewrite = document.getElementById('toggleRewrite');

    const historyList = document.getElementById('historyList');
    const historyEmpty = document.getElementById('historyEmpty');
    const historySearchInput = document.getElementById('historySearchInput');

    // Source Viewer
    const sourceDot = document.getElementById('sourceDot');
    const sourceMeta = document.getElementById('sourceMeta');
    const sourceEmpty = document.getElementById('sourceEmpty');
    const sourceLoaded = document.getElementById('sourceLoaded');
    const sourceText = document.getElementById('sourceText');
    const sourceActName = document.getElementById('sourceActName');
    const sourceSection = document.getElementById('sourceSection');
    const sourceChapter = document.getElementById('sourceChapter');
    const sourcePage = document.getElementById('sourcePage');
    const sourceRelevance = document.getElementById('sourceRelevance');

    // Modal
    const kbModalOverlay = document.getElementById('kbModalOverlay');
    const btnOpenKbModal = document.getElementById('btnOpenKbModal');
    const btnCloseKbModal = document.getElementById('btnCloseKbModal');
    const kbGrid = document.getElementById('kbGrid');
    const newKbIdInput = document.getElementById('newKbIdInput');
    const newKbNameInput = document.getElementById('newKbNameInput');
    const btnCreateKb = document.getElementById('btnCreateKb');
    const dragDropZone = document.getElementById('dragDropZone');
    const fileInput = document.getElementById('fileInput');
    const dragDropText = document.getElementById('dragDropText');
    const actNameInput = document.getElementById('actNameInput');
    const overwriteCheckbox = document.getElementById('overwriteCheckbox');
    const btnUpload = document.getElementById('btnUpload');

    const legalTooltip = document.getElementById('legalTooltip');
    const tooltipTerm = document.getElementById('tooltipTerm');
    const tooltipDef = document.getElementById('tooltipDef');

    // ═══════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════
    let currentCitations = [];
    let activeCitationIdx = -1;

    // ═══════════════════════════════════════
    // LEGAL GLOSSARY (~35 terms)
    // ═══════════════════════════════════════
    const GLOSSARY = {
        'habeas corpus': 'A legal order requiring a person under arrest to be brought before a court to determine if imprisonment is lawful.',
        'amicus curiae': '"Friend of the court" — a person or organization offering information relevant to a case but not a party to it.',
        'prima facie': 'At first sight; evidence sufficient to establish a fact unless rebutted.',
        'suo motu': 'On its own motion — when a court takes action without any request from parties.',
        'res judicata': 'A matter already judged; a final judgment by a competent court is conclusive.',
        'ultra vires': 'Beyond the powers; an act exceeding legal authority.',
        'inter alia': 'Among other things; indicating a list is not exhaustive.',
        'bona fide': 'In good faith; genuine and without intention to deceive.',
        'de facto': 'In fact; existing in practice but not necessarily established by law.',
        'de jure': 'By law; by right; recognized or established by law.',
        'ex parte': 'On one side only; a proceeding brought by one party without the other present.',
        'in camera': 'In private chambers; a hearing not open to the public.',
        'locus standi': 'The right or capacity to bring an action or appear in court.',
        'mala fide': 'In bad faith; with intent to deceive or defraud.',
        'obiter dictum': 'A remark made in passing by a judge, not essential to the decision.',
        'ratio decidendi': 'The legal principle upon which a court\'s decision is based.',
        'stare decisis': 'To stand by things decided; the doctrine of following precedent.',
        'sub judice': 'Under judicial consideration; not yet decided by court.',
        'caveat emptor': 'Let the buyer beware; the buyer bears risk for the purchase.',
        'mens rea': 'Guilty mind; the criminal intent behind a criminal act.',
        'actus reus': 'Guilty act; the physical component of a crime.',
        'ipso facto': 'By the fact itself; a direct consequence of an action.',
        'mutatis mutandis': 'With necessary changes; applying a principle with modifications.',
        'non obstante': 'Notwithstanding; a clause that overrides other provisions.',
        'pari passu': 'On equal footing; treating parties with equal ranking.',
        'pro bono': 'For the public good; professional work done voluntarily without payment.',
        'quid pro quo': 'Something for something; an exchange of roughly equal value.',
        'sine die': 'Without a fixed day; adjournment with no date for resumption.',
        'writ': 'A formal written order issued by a court commanding an action.',
        'injunction': 'A court order requiring a party to do or refrain from doing a specific act.',
        'affidavit': 'A written statement confirmed by oath, used as evidence in court.',
        'cognizable': 'An offence for which police may arrest without a warrant.',
        'bail': 'Temporary release of an accused awaiting trial, sometimes on monetary guarantee.',
        'jurisdiction': 'The official power to make legal decisions and judgments.',
        'statute': 'A written law passed by a legislative body.',
    };

    // ═══════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════
    const headers = () => ({
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    });

    const formatAnswer = (text) => {
        if (!text) return "";
        let s = text.replace(/\\u([0-9a-fA-F]{4})/g, (_, g) => String.fromCharCode(parseInt(g, 16)));

        const parts = s.split(/(?=###\s+📜)/g);
        if (parts.length > 1) {
            let html = "";
            if (parts[0].trim()) {
                html += `<div style="margin-bottom:0.5rem;color:var(--text-muted);font-size:0.88rem;line-height:1.6;">${parts[0].trim().replace(/\n/g, '<br>')}</div>`;
            }
            for (let i = 1; i < parts.length; i++) {
                const p = parts[i].trim();
                const tm = p.match(/###\s+📜\s*([^\n]+)/);
                const rm = p.match(/\*Relevance:\s*([^\*]+)\*/);
                const title = tm ? tm[1] : "Legal Passage";
                const rel = rm ? rm[1] : "";
                let body = p;
                if (rm) body = p.substring(p.indexOf(rm[0]) + rm[0].length);
                else if (tm) body = p.substring(p.indexOf(tm[0]) + tm[0].length);
                body = body.trim().replace(/\n/g, '<br>');
                html += `
                    <div style="margin-top:0.75rem;background:var(--off-white);border:1px solid var(--border);border-radius:10px;padding:1.15rem;">
                        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:0.35rem;margin-bottom:0.5rem;">
                            <span style="font-weight:700;color:var(--text-gold);font-size:0.9rem;">📜 ${title}</span>
                            ${rel ? `<span style="font-size:0.6rem;background:var(--gold-dim);color:var(--text-gold);border:1px solid var(--border-gold);padding:2px 6px;border-radius:999px;font-weight:700;">Relevance: ${rel}</span>` : ''}
                        </div>
                        <div style="color:var(--text-secondary);font-size:0.85rem;line-height:1.65;">${body}</div>
                    </div>`;
            }
            return html;
        }

        return s
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code style="background:var(--cream);padding:1px 4px;border-radius:3px;font-size:0.85em;">$1</code>')
            .replace(/\n/g, '<br>');
    };

    const annotateLegal = (html) => {
        let result = html;
        const sorted = Object.keys(GLOSSARY).sort((a, b) => b.length - a.length);
        for (const term of sorted) {
            const esc = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const rx = new RegExp(`(?<![<\\w])\\b(${esc})\\b(?![^<]*>)`, 'gi');
            result = result.replace(rx, (m) =>
                `<span class="legal-term" data-term="${term}" data-definition="${GLOSSARY[term].replace(/"/g, '&quot;')}">${m}</span>`
            );
        }
        return result;
    };

    const fmtTime = (iso) => {
        const d = new Date(iso);
        const mins = Math.floor((Date.now() - d) / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins}m`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h`;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    // ═══════════════════════════════════════
    // HISTORY (localStorage)
    // ═══════════════════════════════════════
    const HK = 'legalrag_history';
    const getHist = () => { try { return JSON.parse(localStorage.getItem(HK)) || []; } catch { return []; } };
    const setHist = (h) => localStorage.setItem(HK, JSON.stringify(h));

    const addHist = (query, answer, citations) => {
        const h = getHist();
        const dup = h.length > 0 && h[0].query === query && (Date.now() - new Date(h[0].ts).getTime()) < 60000;
        if (!dup) {
            h.unshift({ id: Date.now().toString(36) + Math.random().toString(36).slice(2, 5), query, answer, citations, ts: new Date().toISOString(), pin: false });
            if (h.length > 50) h.length = 50;
            setHist(h);
        }
        renderHist();
    };

    const togglePin = (id) => {
        const h = getHist();
        const item = h.find(x => x.id === id);
        if (item) { item.pin = !item.pin; setHist(h); renderHist(); }
    };

    const loadHistItem = (id) => {
        const item = getHist().find(x => x.id === id);
        if (!item) return;
        queryInput.value = item.query;
        answerBox.innerHTML = annotateLegal(formatAnswer(item.answer));
        currentCitations = item.citations || [];
        renderCits(currentCitations);
        responseContainer.style.display = 'flex';
        clearSource();
        document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
        const el = document.querySelector(`.history-item[data-id="${id}"]`);
        if (el) el.classList.add('active');
    };

    const renderHist = (filter = '') => {
        let h = getHist();
        const lf = filter.toLowerCase();
        if (lf) h = h.filter(x => x.query.toLowerCase().includes(lf));
        h.sort((a, b) => {
            if (a.pin && !b.pin) return -1;
            if (!a.pin && b.pin) return 1;
            return new Date(b.ts) - new Date(a.ts);
        });

        if (!h.length) {
            historyList.innerHTML = '';
            historyEmpty.style.display = 'block';
            historyEmpty.textContent = filter ? 'No matches' : 'No queries yet';
            return;
        }

        historyEmpty.style.display = 'none';
        historyList.innerHTML = h.map(x => `
            <div class="history-item" data-id="${x.id}" title="${x.query.replace(/"/g, '&quot;')}">
                <div class="history-item-text">${x.query}</div>
                <span class="history-item-time">${fmtTime(x.ts)}</span>
                <button class="history-bookmark ${x.pin ? 'bookmarked' : ''}" data-bid="${x.id}">${x.pin ? '⭐' : '☆'}</button>
            </div>
        `).join('');

        historyList.querySelectorAll('.history-item').forEach(el => {
            el.addEventListener('click', (e) => {
                if (e.target.closest('.history-bookmark')) return;
                loadHistItem(el.dataset.id);
            });
        });
        historyList.querySelectorAll('.history-bookmark').forEach(btn => {
            btn.addEventListener('click', (e) => { e.stopPropagation(); togglePin(btn.dataset.bid); });
        });
    };

    historySearchInput.addEventListener('input', () => renderHist(historySearchInput.value.trim()));

    // ═══════════════════════════════════════
    // SOURCE VIEWER — Fixed
    // ═══════════════════════════════════════
    const clearSource = () => {
        sourceEmpty.style.display = 'flex';
        sourceLoaded.style.display = 'none';
        sourceLoaded.classList.remove('visible');
        sourceMeta.style.display = 'none';
        sourceMeta.classList.remove('visible');
        sourceDot.classList.remove('active');
        activeCitationIdx = -1;
        document.querySelectorAll('.citation-card').forEach(c => c.classList.remove('active-citation'));
    };

    const loadSource = (cit, idx) => {
        // Fill metadata
        sourceActName.textContent = cit.act_name || 'Unknown';
        sourceSection.textContent = cit.section || '—';
        sourceChapter.textContent = cit.chapter || '—';
        sourcePage.textContent = (cit.page && cit.page > 0) ? `Page ${cit.page}` : '—';
        sourceRelevance.textContent = cit.relevance_score
            ? `${(cit.relevance_score * 100).toFixed(0)}% match`
            : 'Source';

        // Fill text
        const qt = cit.quote || cit.text || cit.content || '';
        if (qt) {
            sourceText.innerHTML = `<span class="source-highlight">${qt}</span>`;
        } else {
            sourceText.innerHTML = '<span style="color:var(--text-light);font-style:italic;">No text available for this citation.</span>';
        }

        // Show loaded state (using both style AND class for reliability)
        sourceEmpty.style.display = 'none';
        sourceLoaded.style.display = 'flex';
        sourceLoaded.classList.add('visible');
        sourceMeta.style.display = 'flex';
        sourceMeta.classList.add('visible');
        sourceDot.classList.add('active');

        // Mark active citation
        activeCitationIdx = idx;
        document.querySelectorAll('.citation-card').forEach((c, i) => {
            c.classList.toggle('active-citation', i === idx);
        });
    };

    // ═══════════════════════════════════════
    // CITATIONS
    // ═══════════════════════════════════════
    const renderCits = (cits) => {
        citationsGrid.innerHTML = '';
        currentCitations = cits;

        if (!cits.length) {
            citationsGrid.innerHTML = '<div style="color:var(--text-light);font-size:0.8rem;font-style:italic;">No citations found.</div>';
            return;
        }

        cits.forEach((cit, i) => {
            let hdr = `<strong>${cit.act_name || 'Legal Document'}</strong>`;
            if (cit.section) hdr += ` — §${cit.section}`;
            if (cit.chapter) hdr += ` (${cit.chapter})`;
            if (cit.page && cit.page > 0) hdr += `, p.${cit.page}`;

            const quote = cit.quote || cit.text || cit.content || '';
            const shortQuote = quote.length > 150 ? quote.substring(0, 150) + '…' : quote;

            const card = document.createElement('div');
            card.className = 'citation-card';
            card.innerHTML = `
                <div class="citation-card-header">${hdr}</div>
                <div class="citation-card-quote">"${shortQuote}"</div>
                <div class="citation-view-hint">👁️ View →</div>
            `;
            card.addEventListener('click', () => loadSource(cit, i));
            citationsGrid.appendChild(card);
        });
    };

    // ═══════════════════════════════════════
    // TOOLTIPS
    // ═══════════════════════════════════════
    let ttTimer = null;

    document.addEventListener('mouseover', (e) => {
        const el = e.target.closest('.legal-term');
        if (!el) return;
        clearTimeout(ttTimer);
        tooltipTerm.textContent = `💡 ${el.dataset.term.charAt(0).toUpperCase() + el.dataset.term.slice(1)}`;
        tooltipDef.textContent = el.dataset.definition;
        const r = el.getBoundingClientRect();
        let top = r.bottom + 8, left = r.left;
        if (left + 320 > window.innerWidth) left = window.innerWidth - 330;
        if (left < 8) left = 8;
        if (top + 120 > window.innerHeight) { top = r.top - 8; legalTooltip.style.transform = 'translateY(-100%)'; }
        else { legalTooltip.style.transform = 'translateY(0)'; }
        legalTooltip.style.top = `${top}px`;
        legalTooltip.style.left = `${left}px`;
        legalTooltip.classList.add('visible');
    });

    document.addEventListener('mouseout', (e) => {
        if (!e.target.closest('.legal-term')) return;
        ttTimer = setTimeout(() => legalTooltip.classList.remove('visible'), 80);
    });

    // ═══════════════════════════════════════
    // TAB SWITCHING
    // ═══════════════════════════════════════
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
            if (btn.dataset.tab === 'kbTab') loadKBs();
        });
    });

    // ═══════════════════════════════════════
    // QUERY EXECUTION
    // ═══════════════════════════════════════
    const runQuery = async () => {
        const q = queryInput.value.trim();
        if (!q) return;

        btnSearch.disabled = true;
        loaderWrapper.style.display = 'flex';
        responseContainer.style.display = 'none';
        clearSource();

        let scope = 'global';
        for (const r of scopeRadios) { if (r.checked) { scope = r.value; break; } }
        const actVal = actFilter.value === 'All Acts' ? null : actFilter.value;

        const payload = {
            question: q,
            top_k: 5,
            act_filter: actVal,
            rewrite_query: toggleRewrite.checked,
            stream: false,
            kb_id: kbSelect.value,
            search_scope: scope,
            temperature: 0.0,
            hybrid_alpha: 0.7
        };

        try {
            const res = await fetch(`${API_BASE}/api/v1/search/query`, {
                method: 'POST',
                headers: headers(),
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            answerBox.innerHTML = annotateLegal(formatAnswer(data.answer));

            if (data.rewritten_query && data.rewritten_query !== q) {
                rewrittenQueryBox.style.display = 'block';
                rewrittenQueryBox.innerHTML = `<strong>Rewritten:</strong> <em>"${data.rewritten_query}"</em>`;
            } else {
                rewrittenQueryBox.style.display = 'none';
            }

            const cits = data.citations || [];
            renderCits(cits);
            responseContainer.style.display = 'flex';
            addHist(q, data.answer, cits);
        } catch (err) {
            console.error(err);
            alert(`Query failed: ${err.message}`);
        } finally {
            btnSearch.disabled = false;
            loaderWrapper.style.display = 'none';
        }
    };

    btnSearch.addEventListener('click', runQuery);
    queryInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') runQuery(); });

    btnCopy.addEventListener('click', () => {
        navigator.clipboard.writeText(answerBox.innerText).then(() => {
            const orig = btnCopy.innerHTML;
            btnCopy.innerHTML = '✅ Copied!';
            setTimeout(() => { btnCopy.innerHTML = orig; }, 1500);
        });
    });

    // ═══════════════════════════════════════
    // KB MODAL
    // ═══════════════════════════════════════
    const openModal = () => { kbModalOverlay.classList.add('visible'); loadKBs(); };
    const closeModal = () => { kbModalOverlay.classList.remove('visible'); };

    btnOpenKbModal.addEventListener('click', openModal);
    btnCloseKbModal.addEventListener('click', closeModal);
    document.getElementById('tabKb').addEventListener('click', () => setTimeout(openModal, 120));
    kbModalOverlay.addEventListener('click', (e) => { if (e.target === kbModalOverlay) closeModal(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && kbModalOverlay.classList.contains('visible')) closeModal(); });

    // ═══════════════════════════════════════
    // KB CRUD
    // ═══════════════════════════════════════
    const loadKBs = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/kb/list`, { headers: headers() });
            if (!res.ok) throw new Error();
            const kbs = await res.json();

            const cv1 = kbSelect.value, cv2 = uploadKbSelect.value;
            kbSelect.innerHTML = '';
            uploadKbSelect.innerHTML = '';
            kbs.forEach(kb => {
                const o = document.createElement('option');
                o.value = kb.kb_id; o.textContent = kb.kb_name;
                kbSelect.appendChild(o.cloneNode(true));
                uploadKbSelect.appendChild(o.cloneNode(true));
            });
            if (cv1) kbSelect.value = cv1;
            if (cv2) uploadKbSelect.value = cv2;

            kbGrid.innerHTML = '';
            kbs.forEach(kb => {
                const c = document.createElement('div');
                c.className = 'kb-card';
                const files = kb.files || [];
                let fh = files.map(f => `<div class="kb-card-file-item"><span>📄</span><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f}</span></div>`).join('');
                if (!files.length) fh = '<div style="font-style:italic;color:var(--text-light);">No files</div>';
                const del = kb.kb_id !== 'global' ? `<button class="btn-danger-outline" data-id="${kb.kb_id}">Delete</button>` : '';
                c.innerHTML = `
                    <div class="kb-card-title"><span>📦</span><div><div>${kb.kb_name}</div><span class="kb-card-id">${kb.kb_id}</span></div></div>
                    <div style="font-size:0.6rem;color:var(--text-light);">Created: ${kb.created_at || 'Default'}</div>
                    <div class="kb-card-files"><strong>Files (${files.length}):</strong>${fh}</div>
                    ${del}
                `;
                kbGrid.appendChild(c);
            });

            kbGrid.querySelectorAll('.btn-danger-outline').forEach(btn => {
                btn.addEventListener('click', async () => {
                    if (confirm(`Delete "${btn.dataset.id}"?`)) {
                        try {
                            const r = await fetch(`${API_BASE}/api/v1/kb/delete?kb_id=${btn.dataset.id}`, { method: 'POST', headers: headers() });
                            if (!r.ok) throw new Error();
                            alert((await r.json()).message || 'Deleted!');
                            loadKBs();
                        } catch { alert('Delete failed'); }
                    }
                });
            });
        } catch (err) { console.error('KB load error', err); }
    };

    btnCreateKb.addEventListener('click', async () => {
        const id = newKbIdInput.value.trim().toLowerCase(), name = newKbNameInput.value.trim();
        if (!id || !name) return alert('Fill in both fields.');
        if (!/^[a-z0-9_-]+$/.test(id)) return alert('ID: lowercase, numbers, _ or - only.');
        try {
            const r = await fetch(`${API_BASE}/api/v1/kb/create`, { method: 'POST', headers: headers(), body: JSON.stringify({ kb_id: id, kb_name: name }) });
            if (!r.ok) throw new Error();
            alert((await r.json()).message || 'Created!');
            newKbIdInput.value = ''; newKbNameInput.value = '';
            loadKBs();
        } catch { alert('Create failed'); }
    });

    // File upload
    ['dragenter', 'dragover'].forEach(ev => dragDropZone.addEventListener(ev, (e) => { e.preventDefault(); dragDropZone.classList.add('active'); }));
    ['dragleave', 'drop'].forEach(ev => dragDropZone.addEventListener(ev, (e) => { e.preventDefault(); dragDropZone.classList.remove('active'); }));
    dragDropZone.addEventListener('drop', (e) => { if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; dragDropText.textContent = `✓ ${e.dataTransfer.files[0].name}`; } });
    dragDropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => { if (fileInput.files.length) dragDropText.textContent = `✓ ${fileInput.files[0].name}`; });

    btnUpload.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return alert('Select a file first.');
        btnUpload.disabled = true; btnUpload.textContent = 'Uploading…';
        const fd = new FormData();
        fd.append('file', file);
        fd.append('kb_id', uploadKbSelect.value);
        fd.append('act_name', actNameInput.value.trim());
        fd.append('overwrite', overwriteCheckbox.checked);
        try {
            const r = await fetch(`${API_BASE}/api/v1/ingest/upload`, { method: 'POST', headers: { 'X-API-Key': API_KEY }, body: fd });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            alert((await r.json()).message || 'Done!');
            fileInput.value = ''; dragDropText.textContent = 'Drop PDF/DOCX/TXT or click';
            actNameInput.value = ''; loadKBs();
        } catch (err) { alert(`Upload failed: ${err.message}`); }
        finally { btnUpload.disabled = false; btnUpload.textContent = '📤 Upload & Index'; }
    });

    // ═══════════════════════════════════════
    // LOAD ACTS FILTER
    // ═══════════════════════════════════════
    const loadActs = async () => {
        try {
            const r = await fetch(`${API_BASE}/api/v1/ingest/status`, { headers: headers() });
            if (!r.ok) throw new Error();
            const d = await r.json();
            actFilter.innerHTML = '<option value="All Acts">All Acts</option>';
            Object.keys(d.acts_ingested || {}).forEach(act => {
                if (act) { const o = document.createElement('option'); o.value = act; o.textContent = act; actFilter.appendChild(o); }
            });
        } catch { console.warn('Acts load failed'); }
    };

    // ═══════════════════════════════════════
    // INIT
    // ═══════════════════════════════════════
    renderHist();
    loadKBs();
    loadActs();
});
