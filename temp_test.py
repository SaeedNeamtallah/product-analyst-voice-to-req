from backend.services.srs_service import SRSService

content = {
    'sections': [
        {
            'title': 'Requirements Diagrams (Mermaid)',
            'confidence': '100%',
            'items': ['```mermaid\nflowchart LR\nA-->B\n```']
        }
    ],
    'summary': 'test'
}

svc = SRSService()
pdf = svc._build_pdf(content=content, project_id=1, language='en')
print('generated', len(pdf), 'bytes')
