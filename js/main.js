document.addEventListener('DOMContentLoaded', () => {
    // 初始化MCQ
    if (window.initQuestions) window.initQuestions();
    // 初始化便签逻辑
    if (window.initNotes) window.initNotes();

    // 初始化垃圾桶
    if (window.initTrashBin) window.initTrashBin();

    // 初始化收藏夹
    if (window.initFavorites) window.initFavorites();

    // 初始化架构生成
    if (window.initArchitecture) window.initArchitecture();

    // 初始化流程图生成
    if (window.initDiagram) window.initDiagram();

    // 初始化 Mermaid
    if (window.mermaid) {
        window.mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true
            }
        });
    }

    console.log('All modules initialized successfully.');
});


