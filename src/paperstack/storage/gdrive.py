"""Google Drive storage backend."""
from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import BinaryIO

from paperstack.config import get_settings

from .base import StorageBackend


class GoogleDriveStorage(StorageBackend):
    """Google Drive storage backend for PDFs."""

    def __init__(self, folder_id: str | None = None):
        settings = get_settings()
        self.folder_id = folder_id or settings.gdrive_folder_id
        self._service = None
        self._temp_dir = Path(tempfile.gettempdir()) / "paperstack_cache"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def service(self):
        """Lazy initialization of Google Drive service."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        """Build Google Drive API service."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            settings = get_settings()
            creds_path = settings.home_dir / "gdrive_credentials.json"
            token_path = settings.home_dir / "gdrive_token.json"

            creds = None
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path))

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                else:
                    if not creds_path.exists():
                        raise RuntimeError(
                            f"Google Drive credentials not found at {creds_path}. "
                            "Please download OAuth credentials from Google Cloud Console."
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(creds_path),
                        scopes=["https://www.googleapis.com/auth/drive.file"],
                    )
                    creds = flow.run_local_server(port=0)

                with open(token_path, "w") as token:
                    token.write(creds.to_json())

            return build("drive", "v3", credentials=creds)

        except ImportError as e:
            raise RuntimeError(
                "Google API libraries not installed. "
                "Install with: pip install google-api-python-client google-auth-oauthlib"
            ) from e

    def save_pdf(self, paper_id: int, content: bytes | BinaryIO) -> str:
        """Save a PDF to Google Drive."""
        from googleapiclient.http import MediaIoBaseUpload

        if isinstance(content, bytes):
            content = io.BytesIO(content)

        file_metadata = {
            "name": f"paper_{paper_id}.pdf",
            "parents": [self.folder_id] if self.folder_id else [],
        }

        media = MediaIoBaseUpload(content, mimetype="application/pdf")

        file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )

        return file["id"]

    def get_pdf(self, path: str) -> bytes | None:
        """Get PDF content from Google Drive."""
        try:
            from googleapiclient.http import MediaIoBaseDownload

            request = self.service.files().get_media(fileId=path)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            return buffer.getvalue()

        except Exception:
            return None

    def get_pdf_path(self, path: str) -> Path | None:
        """Download PDF to temp directory and return local path."""
        content = self.get_pdf(path)
        if content is None:
            return None

        local_path = self._temp_dir / f"{path}.pdf"
        local_path.write_bytes(content)
        return local_path

    def delete_pdf(self, path: str) -> bool:
        """Delete a PDF from Google Drive."""
        try:
            self.service.files().delete(fileId=path).execute()
            return True
        except Exception:
            return False

    def exists(self, path: str) -> bool:
        """Check if a PDF exists in Google Drive."""
        try:
            self.service.files().get(fileId=path).execute()
            return True
        except Exception:
            return False
