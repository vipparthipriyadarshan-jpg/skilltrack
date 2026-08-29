import spacy

def test_spacy_loading():
    nlp = spacy.load("en_core_web_sm")
    assert nlp is not None
    print("spaCy loaded successfully")

if __name__ == "__main__":
    test_spacy_loading()
