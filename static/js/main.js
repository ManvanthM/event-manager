/**
 * Event Manager – Client-side JavaScript
 * Handles: particles, sidebar toggle, section switching,
 *          search filter, modals, edit pre-fill.
 */

/* ═══════════════════════════════════════════════
   Particle background (login page)
   ═══════════════════════════════════════════════ */
function createParticles() {
    const container = document.getElementById('particles');
    if (!container) return;
    const count = 40;
    for (let i = 0; i < count; i++) {
        const dot = document.createElement('span');
        dot.className = 'dot';
        dot.style.left = Math.random() * 100 + '%';
        dot.style.top = (100 + Math.random() * 20) + '%';  // start below viewport
        dot.style.animationDuration = (6 + Math.random() * 10) + 's';
        dot.style.animationDelay = (Math.random() * 8) + 's';
        dot.style.width = dot.style.height = (2 + Math.random() * 3) + 'px';
        container.appendChild(dot);
    }
}

/* ═══════════════════════════════════════════════
   Dashboard initialisation
   ═══════════════════════════════════════════════ */
function initDashboard() {
    setupSidebar();
    setupNavLinks();
    setupSearch();
}

/* ─── Sidebar toggle (mobile) ─── */
function setupSidebar() {
    const toggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    if (!toggle || !sidebar) return;

    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    function openSidebar() {
        sidebar.classList.add('open');
        overlay.classList.add('active');
    }
    function closeSidebar() {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
    }

    toggle.addEventListener('click', openSidebar);
    overlay.addEventListener('click', closeSidebar);
}

/* ─── Sidebar navigation (section switching) ─── */
function setupNavLinks() {
    const links = document.querySelectorAll('.nav-link[data-section]');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.dataset.section + '-section';

            // Toggle active link
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Toggle active section
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active-section'));
            const target = document.getElementById(targetId);
            if (target) target.classList.add('active-section');

            // Close sidebar on mobile
            const sidebar = document.getElementById('sidebar');
            if (sidebar) sidebar.classList.remove('open');
            const overlay = document.querySelector('.sidebar-overlay');
            if (overlay) overlay.classList.remove('active');
        });
    });
}

/* ─── Table search filter ─── */
function setupSearch() {
    const input = document.getElementById('searchEvents');
    const table = document.getElementById('eventsTable');
    if (!input || !table) return;

    input.addEventListener('input', () => {
        const q = input.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(q) ? '' : 'none';
        });
    });
}

/* ═══════════════════════════════════════════════
   Modal helpers
   ═══════════════════════════════════════════════ */
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('open');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('open');
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    }
});

// Close modal on outside click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
    }
});

/* ═══════════════════════════════════════════════
   Edit Event – pre-fill modal and set form action
   ═══════════════════════════════════════════════ */
function openEditModal(id, title, description, date, time) {
    document.getElementById('editTitle').value = title;
    document.getElementById('editDesc').value = description;
    document.getElementById('editDate').value = date;
    document.getElementById('editTime').value = time;
    document.getElementById('editEventForm').action = '/edit_event/' + id;
    openModal('editEventModal');
}
