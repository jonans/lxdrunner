import pytest
import flask

from lxdrunner.appconf import config as cfg
from lxdrunner import web

app = flask.Flask(__name__)

headers = {'X-Hub-Signature-256': 'failedsig'}


@pytest.fixture
def reqx():
    with app.test_request_context("/myrequest") as treq:
        yield treq.request


def test_verify_webhook_missing_sig():
    with app.test_request_context():
        assert web.validate_webhook() is False


def test_verify_webhook_wrong_sig():
    hdrs = {'X-Hub-Signature-256': 'incorrect_github_signature'}
    with app.test_request_context(headers=hdrs):
        assert web.validate_webhook() is False


def test_verify_webhook_correct_sig():
    hdrs = {
        'X-Hub-Signature-256':
        'sha256=d96602158aa0d59b65d26942515163691680544bfa57e44c470712cd4aa800ae'
    }
    with app.test_request_context(headers=hdrs):
        assert web.validate_webhook() is True, "Sig does not match computed"
    hdrs = {
        'X-Hub-Signature-256':
        'sha256=986a36d904cc895eaec3f9b14041f7d63a2fddb2076485ea5ada781d176e89a2'
    }
    with app.test_request_context(headers=hdrs, data='different_payload'):
        assert web.validate_webhook() is True, "Sig doest not match computed"
