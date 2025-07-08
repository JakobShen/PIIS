function initNotes() {
    // 添加新便签
    addNoteBtn.addEventListener('click', function () {
        noteCount++;
        const x = 100 + (Math.random() * 200);
        const y = 100 + (Math.random() * 200);

        const note = document.createElement('div');
        note.className = 'note';
        note.style.top = `${y}px`;
        note.style.left = `${x}px`;
        note.innerHTML = `
              <div class="note-header">
                <div>
                  <div class="title-edit-tooltip">Double-click to edit title</div>
                  <div class="note-title" tabindex="0">Note #${noteCount}</div>
                </div>
                <div class="note-actions">
                  <div class="note-action suggest-action" title="AI Suggest"><i class="fas fa-magic"></i></div>
                  <div class="note-action"><i class="fas fa-times"></i></div>
                </div>
              </div>
              <div class="note-content" contenteditable="true">
                Double-click to edit this note...
              </div>
            `;

        whiteboard.appendChild(note);
        addNoteEvents(note);
    });

    // 给所有已有便签添加事件
    document.querySelectorAll('.note').forEach(note => {
        addNoteEvents(note);
    });

    // 便签事件绑定函数
    function addNoteEvents(note) {
        // 删除按钮事件和拖拽删除
        const deleteBtn = note.querySelector('.note-action:not(.suggest-action)');
        const suggestBtn = note.querySelector('.suggest-action');
        const title = note.querySelector('.note-title');
        // 删除按钮点击删除
        deleteBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            note.style.transform = 'scale(0.9)';
            note.style.opacity = '0.5';
            setTimeout(() => {
                deletedNotesArr.push({
                    html: note.outerHTML,
                    top: note.style.top,
                    left: note.style.left
                });
                if (whiteboard.contains(note)) {
                    whiteboard.removeChild(note);
                    deletedNotes++;
                    trashCount.textContent = deletedNotes;
                    updateTrashList();
                }
            }, 300);
        });
        // 拖拽功能（自定义拖动，便签本身不设置draggable）
        note.removeAttribute('draggable');
        note.addEventListener('mousedown', startDrag);
        // 删除按钮支持原生拖拽到垃圾桶
        deleteBtn.setAttribute('draggable', 'true');
        deleteBtn.addEventListener('dragstart', function (e) {
            e.stopPropagation();
            e.dataTransfer.setData('text/plain', 'delete-note');
            // 记录当前拖拽的 note
            currentNote = note;
            // 拖拽预览
            dragPreview = note.cloneNode(true);
            dragPreview.style.position = 'absolute';
            dragPreview.style.pointerEvents = 'none';
            dragPreview.style.opacity = '0.7';
            dragPreview.style.zIndex = '9999';
            dragPreview.style.left = '-9999px';
            dragPreview.style.top = '-9999px';
            document.body.appendChild(dragPreview);
            e.dataTransfer.setDragImage(dragPreview, 100, 30);
        });
        deleteBtn.addEventListener('dragend', function () {
            if (dragPreview && dragPreview.parentNode) {
                dragPreview.parentNode.removeChild(dragPreview);
                dragPreview = null;
            }
            currentNote = null;
        });

        // AI Suggest button
        if (suggestBtn) {
            suggestBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                const titleText = title.textContent.trim() || 'New Note';
                const contentDiv = note.querySelector('.note-content');
                const existingContent = contentDiv.innerText.trim();
                const existingNotes = Array.from(document.querySelectorAll('.note'))
                    .filter(n => n !== note)
                    .map(el => el.innerText.trim())
                    .filter(text => text.length > 0)
                    .join('\n\n');

                const original = contentDiv.innerText;
                contentDiv.innerText = '(Generating suggestion from AI...)';

                const overlay = document.createElement('div');
                overlay.className = 'loading-overlay';
                overlay.innerHTML = '<div class="spinner"></div>';
                whiteboard.appendChild(overlay);

                fetch('http://127.0.0.1:8000/api/note_hint', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ existingNotes, title: titleText, content: existingContent })
                })
                    .then(res => res.json())
                    .then(data => {
                        if (existingContent) {
                            contentDiv.innerText = existingContent + '\n' + data.suggestion;
                        } else {
                            contentDiv.innerText = data.suggestion;
                        }
                    })
                    .catch(err => {
                        console.error('AI suggestion failed', err);
                        contentDiv.innerText = original;
                    })
                    .finally(() => {
                        if (whiteboard.contains(overlay)) {
                            whiteboard.removeChild(overlay);
                        }
                    });
            });
        }

        // 标题双击编辑
        title.addEventListener('dblclick', function (e) {
            e.stopPropagation();
            this.contentEditable = true;
            this.focus();

            // 选中全部文本
            const range = document.createRange();
            range.selectNodeContents(this);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        });

        title.addEventListener('blur', function () {
            this.contentEditable = false;

            // 标题为空时恢复默认
            if (this.textContent.trim() === '') {
                this.textContent = this.dataset.original || 'Untitled Note';
            }
        });

        // 首次交互时保存原始标题
        if (!title.dataset.original) {
            title.dataset.original = title.textContent;
        }

        // 按回车结束编辑
        title.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur();
            }
        });

        // 内容双击可编辑
        const content = note.querySelector('.note-content');
        content.addEventListener('dblclick', function () {
            this.contentEditable = true;
            this.focus();
        });

        content.addEventListener('blur', function () {
            this.contentEditable = false;
        });

        //如果内容为空，由llm提供灵感
        if (content.innerText.trim() === "") {
            content.innerText = "(Generating suggestion from AI...)";
            const existingNotes = Array.from(document.querySelectorAll(".note"))
                .map(el => el.innerText.trim())
                .filter(text => text.length > 0)
                .join("\n\n");

            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="spinner"></div>';
            whiteboard.appendChild(overlay);

            fetch("http://127.0.0.1:8000/api/note_hint", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ existingNotes, title: title.textContent.trim(), content: "" })
            })
                .then(res => res.json())
                .then(data => {
                    content.innerText = data.suggestion;
                })
                .finally(() => {
                    if (whiteboard.contains(overlay)) {
                        whiteboard.removeChild(overlay);
                    }
                });
        }
    }

    // 拖拽开始
    function startDrag(e) {
        // 删除按钮、标题或内容正在编辑时不触发拖拽
        if (
            e.target.classList.contains('note-action') ||
            (e.target.classList.contains('note-title') && e.target.isContentEditable) ||
            (e.target.classList.contains('note-content') && e.target.isContentEditable)
        ) {
            return;
        }
        isDragging = true;
        currentNote = this; // 绑定到整个note
        offsetX = e.clientX - currentNote.getBoundingClientRect().left;
        offsetY = e.clientY - currentNote.getBoundingClientRect().top;

        currentNote.style.zIndex = '100';
        document.addEventListener('mousemove', dragNote);
        document.addEventListener('mouseup', stopDrag);
    }

    // 拖拽中
    function dragNote(e) {
        if (!isDragging) return;

        const whiteboardRect = whiteboard.getBoundingClientRect();
        const x = e.clientX - offsetX - whiteboardRect.left;
        const y = e.clientY - offsetY - whiteboardRect.top;

        // 边界检查
        const maxX = whiteboardRect.width - currentNote.offsetWidth;
        const maxY = whiteboardRect.height - currentNote.offsetHeight;

        currentNote.style.left = `${Math.max(0, Math.min(x, maxX))}px`;
        currentNote.style.top = `${Math.max(0, Math.min(y, maxY))}px`;
    }

    // 拖拽结束
    function stopDrag() {
        isDragging = false;
        if (currentNote) {
            currentNote.style.zIndex = '10';
            currentNote = null;
        }
        document.removeEventListener('mousemove', dragNote);
        document.removeEventListener('mouseup', stopDrag);
    }
}

window.initNotes = initNotes;


