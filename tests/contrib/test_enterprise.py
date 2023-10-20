"""Test enterprise grade synonyms."""

import pytest
import picobox
import picobox.contrib.enterprise as di



@pytest.fixture(params=[di.Container, di.MultiContainer])
def containerclass(request):
    yield request.param


def test_container_is_box():
    assert di.Container is picobox.Box


def test_container_put_get(containerclass):
    testcontainer = containerclass()
    testcontainer.put("the-key", "the-value")

    assert testcontainer.get("the-key") == "the-value"


def test_container_inject(containerclass):
    testcontainer = containerclass()
    testcontainer.put("a", 10)

    @testcontainer.inject("a")
    def fn(a, b, c):
        return a + b + c

    assert fn(b=2, c=3) == 15
