"""Capitalising the first letter of a name, and nothing else.

The tempting one-liners here (`.title()`, `.capitalize()`) both damage real
names, so the cases below are mostly about what must be left alone.
"""

from app.names import normalise_display_name as tidy

from conftest import login


def test_a_lowercase_name_is_capitalised():
    assert tidy("benji") == "Benji"


def test_surrounding_space_goes_first():
    assert tidy("  kai  ") == "Kai"


def test_only_the_first_letter_is_touched():
    """Just the first name's first letter, as asked -- not every word."""
    assert tidy("benji alwis") == "Benji alwis"


def test_capitalisation_people_chose_is_preserved():
    """The reason .capitalize() and .title() are both wrong.

    Someone whose name is McDonald wrote it that way on purpose, and a platform
    that quietly restyles it to Mcdonald is getting their name wrong.
    """
    assert tidy("McDonald") == "McDonald"
    assert tidy("JJ") == "JJ"
    assert tidy("O'Neill") == "O'Neill"
    assert tidy("van der Berg") == "Van der Berg"


def test_non_ascii_names_work():
    assert tidy("élodie") == "Élodie"
    assert tidy("ötzi") == "Ötzi"


def test_an_already_capitalised_name_is_unchanged():
    assert tidy("Benji") == "Benji"


def test_empty_stays_empty():
    # The caller turns this into "please enter a name"; it must not crash here.
    assert tidy("   ") == ""


# --- through the API --------------------------------------------------------


def test_signing_up_capitalises_the_name(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "lower@example.com",
            "password": "password123",
            "display_name": "  benji ",
        },
    )
    assert response.status_code == 201
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/auth/me", headers=headers).json()["display_name"] == "Benji"


def test_an_existing_account_is_not_disturbed(client):
    """Seeded and older accounts keep whatever name they already have."""
    me = client.get("/auth/me", headers=login(client)).json()
    assert me["display_name"] == "Test Student"


def test_an_oauth_name_derived_from_an_address_is_capitalised():
    """The fallback takes the local part of the address, which is nearly always
    lowercase -- the exact case this fixes."""
    from app.oauth import profile_from, providers

    profile = profile_from(providers()["google"], {"sub": "1", "email": "kai@b.com"})
    assert profile.display_name == "Kai"
