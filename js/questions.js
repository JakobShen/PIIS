function initQuestions() {
    const mcqBtn = document.getElementById('generateMCQBtn');
    if (!mcqBtn) return;
    mcqBtn.addEventListener('click', async function () {
        const category = document.getElementById('questionCategory').value;
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        whiteboard.appendChild(overlay);

        const appType = document.getElementById('appType').value;
        const userCount = document.getElementById('userCount').value;
        const projectDesc = document.getElementById('projectDesc').value;
        const features = [];
        for (let i = 1; i <= 8; i++) {
            if (document.getElementById('feature' + i).checked) {
                features.push(document.querySelector('label[for="feature' + i + '"]').textContent);
            }
        }
        const notes = Array.from(document.querySelectorAll('.note'))
            .map(n => n.innerText.trim())
            .filter(t => t !== '');

        try {
            const response = await fetch('http://127.0.0.1:8000/api/generate_mcq', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category,
                    prompt: projectDesc,
                    appType,
                    features,
                    userCount,
                    notes
                })
            });
            const data = await response.json();
            if (whiteboard.contains(overlay)) whiteboard.removeChild(overlay);
            const note = document.createElement('div');
            note.className = 'note result-note';
            note.style.top = '200px';
            note.style.left = '200px';

            const parsed = parseMCQ(data.mcq || '');
            const radioName = 'mcq-' + Date.now();
            let optionsHtml = '';
            parsed.options.forEach((opt, idx) => {
                const letter = String.fromCharCode(65 + idx);
                optionsHtml += `<label class="mcq-option"><input type="radio" name="${radioName}" value="${letter}"> ${opt}</label><br>`;
            });

            note.innerHTML = `
                <div class="note-header">
                    <div>
                        <div class="title-edit-tooltip">Double-click to edit title</div>
                        <div class="note-title" tabindex="0">${category}</div>
                    </div>
                    <div class="note-actions">
                        <div class="note-action"><i class="fas fa-times"></i></div>
                    </div>
                </div>
                <div class="note-content">
                    <div class="mcq-question">${parsed.question}</div>
                    <div class="mcq-options">${optionsHtml}</div>
                </div>
            `;
            whiteboard.appendChild(note);
            addNoteEvents(note);
            note.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } catch (err) {
            if (whiteboard.contains(overlay)) whiteboard.removeChild(overlay);
            alert('MCQ generation failed.');
            console.error('generateMCQ failed:', err);
        }
    });
}

function parseMCQ(text) {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l);
    const question = lines[0] || text;
    let options = lines.slice(1).map(l => l.replace(/^[A-D][).:\s]*\s*/, ''));
    if (options.length < 4) {
        options = [];
        const regex = /[A-D][).:\s]*([^\n]+)/g;
        let m;
        while ((m = regex.exec(text)) && options.length < 4) {
            options.push(m[1].trim());
        }
    }
    while (options.length < 4) options.push('');
    return { question, options };
}

window.initQuestions = initQuestions;
