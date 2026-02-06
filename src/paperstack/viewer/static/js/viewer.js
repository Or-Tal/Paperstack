/**
 * Paperstack PDF Viewer JavaScript
 */

class PaperstackViewer {
    constructor(paperId) {
        this.paperId = paperId;
        this.pdf = null;
        this.currentPage = 1;
        this.totalPages = 0;
        this.scale = 1.0;
        this.annotations = [];
        this.currentTool = 'highlight';
        this.currentColor = '#ffeb3b';
        this.pendingAnnotation = null;

        this.canvas = document.getElementById('pdfCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.annotationLayer = document.getElementById('annotationLayer');

        this.init();
    }

    async init() {
        this.bindEvents();

        if (this.paperId) {
            await this.loadPaperInfo();
            await this.loadPdf();
            await this.loadAnnotations();
        } else {
            document.getElementById('loadingIndicator').innerHTML =
                '<p>No paper selected. Use paperstack view &lt;id&gt; to open a paper.</p>';
        }
    }

    bindEvents() {
        // Navigation
        document.getElementById('prevPage').addEventListener('click', () => this.prevPage());
        document.getElementById('nextPage').addEventListener('click', () => this.nextPage());
        document.getElementById('pageInput').addEventListener('change', (e) => {
            this.goToPage(parseInt(e.target.value));
        });

        // Zoom
        document.getElementById('zoomIn').addEventListener('click', () => this.zoom(0.25));
        document.getElementById('zoomOut').addEventListener('click', () => this.zoom(-0.25));
        document.getElementById('fitWidth').addEventListener('click', () => this.fitWidth());

        // Tools
        document.querySelectorAll('.btn-tool').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.btn-tool').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentTool = e.target.dataset.tool;
            });
        });

        // Colors
        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentColor = e.target.dataset.color;
            });
        });

        // Text selection for highlights
        this.canvas.addEventListener('mouseup', () => this.handleTextSelection());

        // Sidebar toggle
        document.getElementById('toggleSidebar').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('collapsed');
        });

        // Comment modal
        document.getElementById('saveComment').addEventListener('click', () => this.saveComment());
        document.getElementById('cancelComment').addEventListener('click', () => this.closeCommentModal());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') this.prevPage();
            if (e.key === 'ArrowRight') this.nextPage();
            if (e.key === '+' || e.key === '=') this.zoom(0.25);
            if (e.key === '-') this.zoom(-0.25);
        });
    }

    async loadPaperInfo() {
        try {
            const response = await fetch(`/api/paper/${this.paperId}`);
            const paper = await response.json();

            document.getElementById('paperTitle').textContent = paper.title;
            document.getElementById('paperAuthors').textContent = paper.authors || '';

            const tagsContainer = document.getElementById('paperTags');
            tagsContainer.innerHTML = '';
            (paper.tags || []).forEach(tag => {
                const span = document.createElement('span');
                span.className = 'tag';
                span.textContent = tag;
                tagsContainer.appendChild(span);
            });
        } catch (error) {
            console.error('Failed to load paper info:', error);
        }
    }

    async loadPdf() {
        try {
            const url = `/api/paper/${this.paperId}/pdf`;
            this.pdf = await pdfjsLib.getDocument(url).promise;
            this.totalPages = this.pdf.numPages;

            document.getElementById('totalPages').textContent = this.totalPages;
            document.getElementById('pageInput').max = this.totalPages;
            document.getElementById('loadingIndicator').classList.add('hidden');

            await this.renderPage(1);
        } catch (error) {
            console.error('Failed to load PDF:', error);
            document.getElementById('loadingIndicator').innerHTML =
                '<p>Failed to load PDF. Make sure the paper has a PDF file attached.</p>';
        }
    }

    async loadAnnotations() {
        try {
            const response = await fetch(`/api/paper/${this.paperId}/annotations`);
            this.annotations = await response.json();
            this.renderAnnotationsList();
            this.renderPageAnnotations();
        } catch (error) {
            console.error('Failed to load annotations:', error);
        }
    }

    async renderPage(pageNum) {
        if (!this.pdf || pageNum < 1 || pageNum > this.totalPages) return;

        const page = await this.pdf.getPage(pageNum);
        const viewport = page.getViewport({ scale: this.scale });

        this.canvas.width = viewport.width;
        this.canvas.height = viewport.height;

        await page.render({
            canvasContext: this.ctx,
            viewport: viewport
        }).promise;

        this.currentPage = pageNum;
        document.getElementById('currentPage').textContent = pageNum;
        document.getElementById('pageInput').value = pageNum;

        // Update annotation layer size and position
        const rect = this.canvas.getBoundingClientRect();
        this.annotationLayer.style.width = `${this.canvas.width}px`;
        this.annotationLayer.style.height = `${this.canvas.height}px`;

        this.renderPageAnnotations();
    }

    renderPageAnnotations() {
        this.annotationLayer.innerHTML = '';

        const pageAnnotations = this.annotations.filter(a => a.page === this.currentPage);

        pageAnnotations.forEach(annotation => {
            if (annotation.type === 'highlight' && annotation.position) {
                const highlight = document.createElement('div');
                highlight.className = 'highlight';
                highlight.style.left = `${annotation.position.x * this.scale}px`;
                highlight.style.top = `${annotation.position.y * this.scale}px`;
                highlight.style.width = `${annotation.position.width * this.scale}px`;
                highlight.style.height = `${annotation.position.height * this.scale}px`;
                highlight.style.backgroundColor = annotation.color;
                highlight.title = annotation.selection_text || '';
                this.annotationLayer.appendChild(highlight);
            }
        });
    }

    renderAnnotationsList() {
        const list = document.getElementById('annotationsList');
        list.innerHTML = '';

        this.annotations.forEach(annotation => {
            const item = document.createElement('li');
            item.className = 'annotation-item';
            item.style.borderLeft = `3px solid ${annotation.color}`;

            item.innerHTML = `
                <span class="page-num">Page ${annotation.page}</span>
                <button class="delete-btn" data-id="${annotation.id}">×</button>
                <div class="text">${annotation.selection_text || annotation.content || 'Note'}</div>
            `;

            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('delete-btn')) {
                    this.goToPage(annotation.page);
                }
            });

            item.querySelector('.delete-btn').addEventListener('click', async (e) => {
                e.stopPropagation();
                await this.deleteAnnotation(annotation.id);
            });

            list.appendChild(item);
        });
    }

    async handleTextSelection() {
        const selection = window.getSelection();
        const text = selection.toString().trim();

        if (!text) return;

        // Get selection bounds relative to canvas
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const canvasRect = this.canvas.getBoundingClientRect();

        const position = {
            x: (rect.left - canvasRect.left) / this.scale,
            y: (rect.top - canvasRect.top) / this.scale,
            width: rect.width / this.scale,
            height: rect.height / this.scale
        };

        if (this.currentTool === 'highlight') {
            await this.createAnnotation('highlight', text, position);
        } else if (this.currentTool === 'comment') {
            this.pendingAnnotation = { text, position };
            this.openCommentModal();
        }

        selection.removeAllRanges();
    }

    async createAnnotation(type, selectionText, position, content = null) {
        try {
            const response = await fetch(`/api/paper/${this.paperId}/annotations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    page: this.currentPage,
                    type: type,
                    selection_text: selectionText,
                    position: position,
                    content: content,
                    color: this.currentColor
                })
            });

            const annotation = await response.json();
            this.annotations.push(annotation);
            this.renderAnnotationsList();
            this.renderPageAnnotations();
        } catch (error) {
            console.error('Failed to create annotation:', error);
        }
    }

    async deleteAnnotation(id) {
        try {
            await fetch(`/api/annotations/${id}`, { method: 'DELETE' });
            this.annotations = this.annotations.filter(a => a.id !== id);
            this.renderAnnotationsList();
            this.renderPageAnnotations();
        } catch (error) {
            console.error('Failed to delete annotation:', error);
        }
    }

    openCommentModal() {
        document.getElementById('commentModal').classList.add('active');
        document.getElementById('commentText').value = '';
        document.getElementById('commentText').focus();
    }

    closeCommentModal() {
        document.getElementById('commentModal').classList.remove('active');
        this.pendingAnnotation = null;
    }

    async saveComment() {
        const comment = document.getElementById('commentText').value.trim();
        if (comment && this.pendingAnnotation) {
            await this.createAnnotation(
                'comment',
                this.pendingAnnotation.text,
                this.pendingAnnotation.position,
                comment
            );
        }
        this.closeCommentModal();
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.renderPage(this.currentPage - 1);
        }
    }

    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.renderPage(this.currentPage + 1);
        }
    }

    goToPage(pageNum) {
        pageNum = Math.max(1, Math.min(pageNum, this.totalPages));
        this.renderPage(pageNum);
    }

    zoom(delta) {
        this.scale = Math.max(0.5, Math.min(3, this.scale + delta));
        document.getElementById('zoomLevel').textContent = `${Math.round(this.scale * 100)}%`;
        this.renderPage(this.currentPage);
    }

    fitWidth() {
        const container = document.getElementById('pdfContainer');
        const containerWidth = container.clientWidth - 40; // padding

        if (this.pdf) {
            this.pdf.getPage(this.currentPage).then(page => {
                const viewport = page.getViewport({ scale: 1 });
                this.scale = containerWidth / viewport.width;
                document.getElementById('zoomLevel').textContent = `${Math.round(this.scale * 100)}%`;
                this.renderPage(this.currentPage);
            });
        }
    }
}

// Initialize viewer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PaperstackViewer(window.PAPER_ID);
});
