import re
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, send_file

from .auth import login_required, owned
from .models import FeedbackEntry

bp = Blueprint('attachments', __name__)
PDF_LIMIT = 4 * 1024 * 1024


def save_reference(upload):
    """Type/size checks only; no content extraction, execution or inline rendering."""
    name = upload.filename or ''
    disposition = upload.headers.get('Content-Disposition', '')
    if '\\' in disposition:
        raise ValueError('Choose a PDF filename without directory paths.')
    if '/' in name or '\\' in name or '\x00' in name or not name.lower().endswith('.pdf'):
        raise ValueError('Choose a PDF with a simple filename (no directory paths).')
    if upload.mimetype != 'application/pdf':
        raise ValueError('Only PDF reference attachments are supported.')
    content = upload.read(PDF_LIMIT + 1)
    if len(content) > PDF_LIMIT:
        raise ValueError('PDF attachments must be 4 MB or smaller.')
    if not re.match(rb'%PDF-1\.[0-9]|%PDF-2\.0', content[:8]) or b'%%EOF' not in content[-1024:]:
        raise ValueError('The attachment does not have a valid PDF header and end marker.')
    folder = Path(current_app.config['UPLOAD_FOLDER'])
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + '.pdf'
    path = folder / name
    with path.open('xb') as handle:
        handle.write(content)
    path.chmod(0o600)
    return name, path


@bp.get('/feedback/<int:identifier>/attachment')
@login_required
def attachment(identifier):
    note = owned(FeedbackEntry, identifier)
    if not note.attachment or not re.fullmatch(r'[0-9a-f]{32}\.pdf', note.attachment):
        abort(404)
    path = Path(current_app.config['UPLOAD_FOLDER']) / note.attachment
    if not path.is_file():
        abort(404)
    response = send_file(path, mimetype='application/pdf', as_attachment=True,
                         download_name=f'feedback-{note.id}.pdf')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'private, no-store'
    return response
