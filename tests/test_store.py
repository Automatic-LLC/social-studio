from social_studio.store import clean_url

GOOD = "https://abc.supabase.co"


def test_clean_url_forgives_paste_slips():
    for raw in (GOOD, GOOD + "/", "https:" + GOOD, " " + GOOD + " ", GOOD + "/rest/v1/", '"' + GOOD + '"'):
        assert clean_url(raw) == GOOD
