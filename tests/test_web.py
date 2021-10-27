from unittest import mock
import json
from pathlib import Path

import pytest
import flask

from . import gvars
from lxdrunner.appconf import config as cfg
from lxdrunner import web
from lxdrunner.web import app
import lxdrunner.web

app.queue_evt = mock.MagicMock()

headers = {'X-Hub-Signature-256': 'failedsig'}
basedict = {'X-GitHub-Event': 'some-event'}


@pytest.fixture
def reqx():
    with app.test_request_context("/myrequest") as treq:
        yield treq.request


@pytest.fixture
def hdrs():
    return basedict.copy()


@pytest.fixture
def passhdrs():
    return {
        'X-GitHub-Event':
        'workflow_job',
        'X-Hub-Signature-256':
        'sha256=c9ee377a883ea21b5f71e3a43a0e66fce9d9ddeb3c050632115536ac64d4cbac'
    }


def test_verify_webhook_not_event(passhdrs):
    with app.test_request_context(headers=passhdrs, data="{}"):
        assert web.validate_webhook() is True
    del passhdrs['X-GitHub-Event']
    with app.test_request_context(headers=passhdrs):
        assert web.validate_webhook() is False


def test_verify_webhook_missing_sig(hdrs):
    with app.test_request_context(headers=hdrs):
        assert web.validate_webhook() is False


def test_verify_webhook_wrong_sig(hdrs):
    hdrs.update({'X-Hub-Signature-256': 'incorrect_github_signature'})
    with app.test_request_context(headers=hdrs):
        assert web.validate_webhook() is False


def test_verify_webhook_correct_sig(hdrs):
    hdrs.update(
        {
            'X-Hub-Signature-256':
            'sha256=d96602158aa0d59b65d26942515163691680544bfa57e44c470712cd4aa800ae'
        }
    )
    with app.test_request_context(headers=hdrs):
        assert web.validate_webhook() is True, "Sig does not match computed"
    hdrs.update(
        {
            'X-Hub-Signature-256':
            'sha256=986a36d904cc895eaec3f9b14041f7d63a2fddb2076485ea5ada781d176e89a2'
        }
    )
    with app.test_request_context(headers=hdrs, data='different_payload'):
        assert web.validate_webhook() is True, "Sig doest not match computed"


wf_job = json.load((gvars.testroot / "wf_job.json").open())


@mock.patch('lxdrunner.web.validate_webhook', return_value=False)
def test_githubhook(m_validate, passhdrs):

    with app.test_request_context(headers=passhdrs, json=wf_job):
        res = web.githubhook()
        assert res == ("UNAUTHORIZED", 401), "Should be unauthorized"

    m_validate.return_value = True
    with app.test_request_context(headers=passhdrs, json=wf_job):
        res = web.githubhook()
        assert res == "Skipping Event", "Not self-hosted, should be skipped"

    wf_job['workflow_job']['labels'] = ['self-hosted']

    with app.test_request_context(headers=passhdrs, json=wf_job):
        res = web.githubhook()
        assert res == "OK", "Event not enqueued"
