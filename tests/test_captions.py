from social_studio import captions

RULES = dict(banned=["pawsome", "fur baby", "who's a good boy"])
TAGS = "#corgi #corgisofinstagram #dogzoomies"


def test_plan_examples_pass():
    assert captions.check(f"Corgi zoomies at 6am, every single day 😂 Does yours do this? {TAGS}", RULES) == []
    assert captions.check(f"Biscuit the beagle, 9/10 for that head tilt 🐶 via @owner\n\n{TAGS}", RULES) == []


def test_counts():
    assert "0 emojis (want 1-2)" in captions.check(f"Corgi zoomies at six every single day {TAGS}", RULES)
    assert any("emojis" in p for p in captions.check(f"Corgi zoomies at six every day 😂😂😂 {TAGS}", RULES))
    assert any("hashtags" in p for p in captions.check("Corgi zoomies at six every day 😂 #corgi", RULES))
    assert any("words" in p for p in captions.check(f"Zoomies 😂 {TAGS}", RULES))
    long = " ".join(["word"] * 21)
    assert any("words" in p for p in captions.check(f"{long} 😂 {TAGS}", RULES))


def test_joined_emoji_and_skin_tone_count_once():
    assert len(captions.emojis("👍🏽")) == 1
    assert len(captions.emojis("🐕‍🦺")) == 1
    assert len(captions.emojis("🇺🇸")) == 1


def test_sentences():
    assert any("sentence" in p for p in captions.check(f"He stole a sandwich. Zero remorse at all. 🥪 {TAGS}", RULES))
    assert captions.check(f"He stole a whole sandwich, zero remorse 🥪 Would yours? {TAGS}", RULES) == []


def test_banned_and_repeats():
    assert any("banned" in p for p in captions.check(f"What a pawsome little zoomie machine 😂 {TAGS}", RULES))
    assert any("banned" in p for p in captions.check(f"Who’s a good boy after all that chaos 😂 {TAGS}", RULES))
    assert "repeated hashtag" in captions.check("Corgi zoomies at six every day 😂 #corgi #Corgi #dog", RULES)


def test_build():
    assert captions.build("Zoomies 😂", ["#a", "#b"]) == "Zoomies 😂\n\n#a #b"
