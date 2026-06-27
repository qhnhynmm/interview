"""PDF report generator — used by Inspector agent."""


class PDFGenerator:
    def render_report(self, report: dict) -> bytes:
        raise NotImplementedError("PDF generator not implemented — add reportlab or weasyprint")