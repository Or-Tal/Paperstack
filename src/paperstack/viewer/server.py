"""Flask server for PDF viewer."""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

from paperstack.config import get_settings
from paperstack.db import Repository


def create_app() -> Flask:
    """Create Flask application."""
    # Get paths
    viewer_dir = Path(__file__).parent
    template_dir = viewer_dir / "templates"
    static_dir = viewer_dir / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    CORS(app)

    # Store current paper context
    app.config["CURRENT_PAPER_ID"] = None

    @app.route("/")
    def index():
        """Main viewer page."""
        paper_id = request.args.get("paper_id", app.config.get("CURRENT_PAPER_ID"))
        if paper_id:
            repo = Repository()
            paper = repo.get_paper(int(paper_id))
            repo.close()
            if paper:
                return render_template(
                    "viewer.html",
                    paper_id=paper.id,
                    paper_title=paper.title,
                )
        return render_template("viewer.html", paper_id=None, paper_title="No paper selected")

    @app.route("/api/paper/<int:paper_id>")
    def get_paper(paper_id: int):
        """Get paper metadata."""
        repo = Repository()
        paper = repo.get_paper(paper_id)
        repo.close()

        if paper is None:
            return jsonify({"error": "Paper not found"}), 404

        tags = json.loads(paper.tags) if paper.tags else []

        return jsonify({
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "doi": paper.doi,
            "arxiv_id": paper.arxiv_id,
            "tags": tags,
            "description": paper.description,
            "status": paper.status,
            "pdf_path": paper.pdf_path,
            "url": paper.url,
        })

    @app.route("/api/paper/<int:paper_id>/pdf")
    def get_pdf(paper_id: int):
        """Serve PDF file."""
        repo = Repository()
        paper = repo.get_paper(paper_id)
        repo.close()

        if paper is None:
            return jsonify({"error": "Paper not found"}), 404

        if not paper.pdf_path:
            return jsonify({"error": "No PDF available"}), 404

        pdf_path = Path(paper.pdf_path)
        if not pdf_path.exists():
            return jsonify({"error": "PDF file not found"}), 404

        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"{paper.title[:50]}.pdf",
        )

    @app.route("/api/paper/<int:paper_id>/annotations")
    def get_annotations(paper_id: int):
        """Get annotations for a paper."""
        repo = Repository()
        annotations = repo.get_annotations(paper_id)
        repo.close()

        return jsonify([
            {
                "id": a.id,
                "page": a.page,
                "type": a.type,
                "content": a.content,
                "selection_text": a.selection_text,
                "position": json.loads(a.position) if a.position else None,
                "color": a.color,
                "created_at": a.created_at.isoformat(),
            }
            for a in annotations
        ])

    @app.route("/api/paper/<int:paper_id>/annotations", methods=["POST"])
    def add_annotation(paper_id: int):
        """Add an annotation."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        repo = Repository()
        annotation = repo.add_annotation(
            paper_id=paper_id,
            page=data.get("page", 1),
            annotation_type=data.get("type", "highlight"),
            content=data.get("content"),
            selection_text=data.get("selection_text"),
            position=data.get("position"),
            color=data.get("color", "#ffeb3b"),
        )
        repo.close()

        return jsonify({
            "id": annotation.id,
            "page": annotation.page,
            "type": annotation.type,
            "content": annotation.content,
            "selection_text": annotation.selection_text,
            "position": json.loads(annotation.position) if annotation.position else None,
            "color": annotation.color,
        })

    @app.route("/api/annotations/<int:annotation_id>", methods=["DELETE"])
    def delete_annotation(annotation_id: int):
        """Delete an annotation."""
        repo = Repository()
        success = repo.delete_annotation(annotation_id)
        repo.close()

        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Annotation not found"}), 404

    @app.route("/api/papers")
    def list_papers():
        """List all papers."""
        status = request.args.get("status")
        repo = Repository()
        papers = repo.list_papers(status=status)
        repo.close()

        return jsonify([
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "status": p.status,
                "tags": json.loads(p.tags) if p.tags else [],
            }
            for p in papers
        ])

    return app


def run_viewer(paper_id: int | None = None, host: str | None = None, port: int | None = None, open_browser: bool = True):
    """Run the viewer server."""
    import socket
    import threading
    import time
    import webbrowser

    settings = get_settings()
    host = host or settings.viewer_host
    port = port or settings.viewer_port

    app = create_app()
    if paper_id:
        app.config["CURRENT_PAPER_ID"] = paper_id

    url = f"http://{host}:{port}"
    if paper_id:
        url += f"/?paper_id={paper_id}"

    def wait_for_server_and_open_browser():
        """Wait for server to be ready, then open browser."""
        max_attempts = 50  # 5 seconds max
        for _ in range(max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    webbrowser.open(url)
                    return
            except Exception:
                pass
            time.sleep(0.1)

    print(f"Starting viewer at {url}")
    if paper_id:
        print(f"Opening paper {paper_id}")

    if open_browser:
        # Start browser opener in background thread
        browser_thread = threading.Thread(target=wait_for_server_and_open_browser, daemon=True)
        browser_thread.start()

    app.run(host=host, port=port, debug=False)
