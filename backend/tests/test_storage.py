from unittest.mock import patch

from app.services.storage import save_cv


class _FakeUpload:
    def __init__(self, filename: str, content: bytes, content_type: str | None = None):
        self.filename = filename
        self.content_type = content_type
        self.file = _BytesIO(content)


class _BytesIO:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self) -> bytes:
        chunk = self._data[self._pos :]
        self._pos = len(self._data)
        return chunk


def test_save_cv_to_minio_when_enabled():
    fake_upload = _FakeUpload("resume.pdf", b"%PDF-1.4 fake", "application/pdf")

    with (
        patch("app.services.storage.get_settings") as mock_settings,
        patch("app.services.storage.upload_bytes", return_value="itv-abc/resume.pdf") as mock_upload,
    ):
        settings = mock_settings.return_value
        settings.minio_enabled = True
        settings.minio_bucket_cvs = "cvs"
        settings.storage_path = __import__("pathlib").Path("/tmp")

        name, path, content = save_cv("itv-abc", fake_upload)

    assert name == "resume.pdf"
    assert path == "itv-abc/resume.pdf"
    assert content == b"%PDF-1.4 fake"
    mock_upload.assert_called_once()
    assert mock_upload.call_args.kwargs["key"] == "itv-abc/resume.pdf"
    assert mock_upload.call_args.kwargs["content_type"] == "application/pdf"