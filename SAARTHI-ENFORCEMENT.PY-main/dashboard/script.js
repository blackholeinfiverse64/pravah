const logsContainer = document.getElementById('logsContainer');
const simForm = document.getElementById('simForm');
const actionSelect = document.getElementById('actionSelect');
const allowedCountEl = document.getElementById('allowedCount');
const blockedCountEl = document.getElementById('blockedCount');

let allowedCount = 1284;
let blockedCount = 42;

const nodes = {
    core: document.getElementById('node-core'),
    sarathi: document.getElementById('node-sarathi'),
    executer: document.getElementById('node-executer')
};

const lines = document.querySelectorAll('.line');

function addLog(action, trace, status) {
    const entry = document.createElement('div');
    entry.className = `log-entry ${status.toLowerCase()}`;
    entry.innerHTML = `
        <div class="log-main">
            <span class="log-action">${action}</span>
            <span class="log-trace">${trace}</span>
        </div>
        <span class="log-status status-${status.toLowerCase()}">${status}</span>
    `;
    logsContainer.prepend(entry);
    if (logsContainer.children.length > 5) {
        logsContainer.removeChild(logsContainer.lastChild);
    }
}

async function runSimulation(e) {
    e.preventDefault();
    const action = actionSelect.value;
    const trace = `tr-${Math.floor(Math.random() * 9000) + 1000}-gen`;
    
    resetPipeline();
    
    // Step 1: Core receives
    nodes.core.classList.add('active');
    await wait(800);
    animateLine(0);
    await wait(600);

    // Step 2: Sarathi Decision
    nodes.sarathi.classList.add('active');
    const isAllowed = !['delete_database', 'external_call'].includes(action);
    await wait(1000);
    
    if (isAllowed) {
        animateLine(1);
        await wait(600);
        // Step 3: Executer
        nodes.executer.classList.add('executing');
        allowedCount++;
        allowedCountEl.innerText = allowedCount.toLocaleString();
        addLog(action, trace, 'ALLOW');
        await wait(1200);
        nodes.executer.classList.remove('executing');
        nodes.executer.classList.add('active');
    } else {
        nodes.sarathi.classList.remove('active');
        nodes.sarathi.classList.add('error');
        blockedCount++;
        blockedCountEl.innerText = blockedCount.toLocaleString();
        addLog(action, trace, 'BLOCK');
    }
}

function animateLine(index) {
    lines[index].style.width = '100%';
}

function resetPipeline() {
    Object.values(nodes).forEach(n => {
        n.classList.remove('active', 'executing', 'error');
    });
    lines.forEach(l => l.style.width = '0');
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

simForm.addEventListener('submit', runSimulation);

// Navigation Logic
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        const targetView = item.getAttribute('data-view');
        
        // Update sidebar
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        // Update views
        views.forEach(view => {
            if (view.id === targetView) {
                view.classList.remove('hidden');
            } else {
                view.classList.add('hidden');
            }
        });
    });
});

// Initial logs
addLog('run_job', 'tr-4421-init', 'ALLOW');
addLog('generate_report', 'tr-1290-init', 'ALLOW');
addLog('delete_database', 'tr-9921-init', 'BLOCK');
