"""Reject stale/malformed preview images instead of misprojecting labels."""
import base64
from copy import deepcopy
import hashlib
import io
import pytest
from PIL import Image
from constraint_recovery.annotation import source_image_url
from constraint_recovery.model import DiagramError

SOURCE='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"/>'


def measured():
    stream=io.BytesIO()
    Image.new('RGB',(40,30),(20,40,200)).save(stream,format='PNG')
    raw=stream.getvalue()
    return dict(image_size=[40,30],snapshot=dict(format='png',
        source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        sha256=hashlib.sha256(raw).hexdigest(),css_size=[40,30],pixel_size=[40,30],
        data=base64.b64encode(raw).decode()))


def test_implicit_viewport_needs_measured_snapshot():
    with pytest.raises(DiagramError,match='remeasure with --snapshot'):
        source_image_url(SOURCE,dict(image_size=[40,30]))
    assert source_image_url(SOURCE,measured()).startswith('data:image/png;base64,')


@pytest.mark.parametrize('field,value',[
    ('source_sha256','0'*64),('css_size',[20,10]),('sha256','0'*64),
    ('pixel_size',[20,10]),('data','not base64!'),('format','svg')])
def test_snapshot_binding_and_integrity(field,value):
    data=deepcopy(measured());data['snapshot'][field]=value
    with pytest.raises(DiagramError):source_image_url(SOURCE,data)


def test_hashed_non_image_is_not_a_snapshot():
    data=measured();raw=b'not an image'
    data['snapshot'].update(data=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(DiagramError,match='Invalid source snapshot'):
        source_image_url(SOURCE,data)


def test_css_sizing_cannot_fall_back_to_intrinsic_image():
    source='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><style>svg{width:80px}</style></svg>'
    with pytest.raises(DiagramError,match='remeasure with --snapshot'):
        source_image_url(source,dict(image_size=[80,30]))
    plain=source.replace('<style>svg{width:80px}</style>','')
    assert source_image_url(plain,dict(image_size=[40,30])).startswith('data:image/svg+xml;base64,')
