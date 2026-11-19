# SPDX-License-Identifier: AGPL-3.0-only
"""Public dummy inputs for test-only clients; never a platform login adapter."""

FIXTURE_USERNAME = 'fixture-user'
FIXTURE_PASSWORD = 'fixture-password'


def credential_observation(username, password):
    """Describe equality/length only; never return received credential text."""
    return {
        'fixtureOnly': True,
        'usernameExact': type(username) is str and username == FIXTURE_USERNAME,
        'passwordExact': type(password) is str and password == FIXTURE_PASSWORD,
        'usernameLength': len(username) if type(username) is str else None,
        'passwordLength': len(password) if type(password) is str else None,
        'expectedUsernameLength': len(FIXTURE_USERNAME),
        'expectedPasswordLength': len(FIXTURE_PASSWORD),
    }


def exact_synthetic_login(username, password):
    observed = credential_observation(username, password)
    return observed['usernameExact'] and observed['passwordExact']
