import pytest
import uuid
import logging

from falcon import testing
from robotoff.app.api import api
from robotoff import models
from functools import singledispatch
from types import SimpleNamespace


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()



@singledispatch
def wrap_namespace(ob):
    return ob

@wrap_namespace.register(dict)
def _wrap_dict(ob):
    return SimpleNamespace(**{k: wrap_namespace(v) for k, v in ob.items()})

@wrap_namespace.register(list)
def _wrap_list(ob):
    return [wrap_namespace(v) for v in ob]


def client():
    # Assume the hypothetical `myapp` package has a function called
    # `create()` to initialize and return a `falcon.App` instance.
    return testing.TestClient(api)


def test_random_question():
    models.ProductInsight.delete().execute()
    models.ProductInsight.create(id=uuid.uuid4(),
            data='{}',
            barcode=1, 
            type='category', 
            n_votes=0, 
            username='', 
            latent=False, 
            value_tag='en:seeds', 
            server_domain='api.openfoodfacts.net', 
            automatic_processing=False, 
            unique_scans_n=0, 
            reserved_barcode=False)
    cl = client()
    result = cl.simulate_get('/api/v1/questions/random')
    assert result.status_code == 200

    js = wrap_namespace(result.json)
    assert js.count == 1
    assert js.status == 'found'
    assert len(js.questions) == 1
    assert js.questions[0].barcode == '1'
    assert js.questions[0].type == 'add-binary'
    assert js.questions[0].value == 'Seeds'
    assert js.questions[0].question == 'Does the product belong to this category?'
    assert js.questions[0].insight_id != ''
    assert js.questions[0].insight_type == 'category'

def test_popular_question():
    models.ProductInsight.delete().execute()
    models.ProductInsight.create(id=uuid.uuid4(),
            data='{}',
            barcode=1, 
            type='category', 
            n_votes=0, 
            username='', 
            latent=False, 
            value_tag='en:seeds', 
            server_domain='api.openfoodfacts.net', 
            automatic_processing=False, 
            unique_scans_n=0, 
            reserved_barcode=False)
    cl = client()
    result = cl.simulate_get('/api/v1/questions/random')
    assert result.status_code == 200

    js = wrap_namespace(result.json)
    assert js.count == 1
    assert js.status == 'found'
    assert len(js.questions) == 1
    assert js.questions[0].barcode == '1'
    assert js.questions[0].type == 'add-binary'
    assert js.questions[0].value == 'Seeds'
    assert js.questions[0].question == 'Does the product belong to this category?'
    assert js.questions[0].insight_id != ''
    assert js.questions[0].insight_type == 'category'

def test_barcode_question():
    models.ProductInsight.delete().execute()
    models.ProductInsight.create(id=uuid.uuid4(),
            data='{}',
            barcode=1, 
            type='category', 
            n_votes=0, 
            username='', 
            latent=False, 
            value_tag='en:seeds', 
            server_domain='api.openfoodfacts.net', 
            automatic_processing=False, 
            unique_scans_n=0, 
            reserved_barcode=False)
    cl = client()
    result = cl.simulate_get('/api/v1/questions/2')
    assert result.status_code == 200

    js = wrap_namespace(result.json)
    assert len(js.questions) == 0

    result = cl.simulate_get('/api/v1/questions/1')
    assert result.status_code == 200
    logger.info(result.json)

    js = wrap_namespace(result.json)
    assert js.status == 'found'
    assert len(js.questions) == 1
    assert js.questions[0].barcode == '1'
    assert js.questions[0].type == 'add-binary'
    assert js.questions[0].value == 'Seeds'
    assert js.questions[0].question == 'Does the product belong to this category?'
    assert js.questions[0].insight_id != ''
    assert js.questions[0].insight_type == 'category'
