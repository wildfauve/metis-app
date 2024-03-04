import pytest

from metis_app import error, pdp, pip, monad


class UnAuthorised(error.BaseError):
    pass


#
# Activity PDPs
#
def test_success_activity_auth():
    result = call_the_service(pip=success_pip_activities())

    assert result.is_right()
    assert result.value == "called_successfully"


def test_success_activity_auth_with_no_namespace():
    result = call_the_service_without_namespace(pip=success_pip_activities())

    assert result.is_right()
    assert result.value == "called_successfully"


def test_failed_activity_auth():
    result = call_the_service(pip=failed_pip_activities())

    assert result.is_left()
    assert isinstance(result.error(), UnAuthorised)


def test_fails_when_subject_userinfo_has_failed():
    result = call_the_service(pip=pip.Pip(id_token=None,
                                          subject=userinfo_mock(['service:resource:domain1:action2'])))

    assert result.is_left()
    assert isinstance(result.error(), UnAuthorised)


#
# Token PDPs
#
token_tests = [
    (pip.Pip(id_token=monad.Left("bad-token")), monad.maybe_value_fail),
    (pip.Pip(id_token=monad.Right("good-token")), monad.maybe_value_ok),
    (pip.Pip(id_token=None), monad.maybe_value_fail),
]


@pytest.mark.parametrize("pip,monad_result", token_tests)
def test_token_pdp(pip, monad_result):
    result = call_the_service_with_token_validation(pip=pip)

    assert monad_result(result)


#
# Composable PDPs
#
def test_it_runs_multiple_pdps_all_successful():
    result = call_the_service_composed_authz(pip=pip.Pip(id_token=monad.Right('good-token'),
                                                         subject=userinfo_mock(['service:resource:domain1:action1'])))

    assert result.is_right()
    assert result.value == "called_successfully"


#
# Helpers
#
def success_pip_activities():
    return pip.Pip(id_token=None,
                   subject=userinfo_mock(['service:resource:domain1:action1']))


def failed_pip_activities():
    return pip.Pip(id_token=None,
                   subject=userinfo_mock(['service:resource:domain1:action2']))


def failed_userinfo_get():
    return pip.Pip(id_token=None,
                   subject=monad.Left("unauth"))


@pdp.activity_pdp_decorator("a_service", "service:resource:domain1:action1", "service", UnAuthorised)
def call_the_service(pip: pip.Pip) -> monad.MEither:
    return monad.Right("called_successfully")


@pdp.pdp_decorator(name="a_service",
                   ctx="service:resource:domain1:action1",
                   namespace="service",
                   pdps=[pdp.token_pdp, pdp.activity_pdp],
                   error_cls=UnAuthorised)
def call_the_service_composed_authz(pip: pip.Pip) -> monad.MEither:
    return monad.Right("called_successfully")


@pdp.activity_pdp_decorator("a_service", "service:resource:domain1:action1", None, UnAuthorised)
def call_the_service_without_namespace(pip: pip.Pip) -> monad.MEither:
    return monad.Right("called_successfully")


@pdp.token_pdp_decorator(name="a_service", error_cls=UnAuthorised)
def call_the_service_with_token_validation(pip: pip.Pip) -> monad.MEither:
    return monad.Right("called_successfully")


def userinfo_mock(activities):
    class Subject(pip.UserinfoStateProtocol):
        def __init__(self, state):
            self.state = state

        def activities(self):
            return self.state['activities']

    return monad.Right(Subject(state={'sub': 'subject1', 'activities': activities}))
