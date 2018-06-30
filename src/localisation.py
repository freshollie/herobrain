from nltk.corpus import stopwords
from textblob import TextBlob 
from textblob_de import TextBlobDE

ENGLISH_US = "en-us"
ENGLISH_UK = "en-uk"
GERMANY = "de"

DEFAULT = ENGLISH_UK
ALL_STOP_WORDS = {"en-uk": set(stopwords.words("english")) - {"most", "least"},
                  "en-us": set(stopwords.words("english")) - {"most", "least"},
                  "de": set(stopwords.words("german")) - {"meisten"}}

ALL_GOOGLE_URLS = {"en-uk": "https://www.google.co.uk/search?q={}&ie=utf-8&oe=utf-8&client=firefox-b-1-ab",
                   "en-us": "https://www.google.com/search?q={}&ie=utf-8&oe=utf-8&client=firefox-b-1-ab",
                   "de": "https://www.google.de/search?q={}&ie=utf-8&oe=utf-8&client=firefox-b-1-ab"}

ALL_QUESTION_WORDS = {"en-uk": ["what", "when", "who", "which", "whom", "where", "why", "how"],
                      "en-us": ["what", "when", "who", "which", "whom", "where", "why", "how"],
                      "de": ["was", "wann", "wer", "welche", "wem", "wo", "warum", "wie"]}

TEXT_BLOBS = {"en-uk": TextBlob, 
              "en-us": TextBlob, 
              "de": TextBlobDE}


def is_opposite_german(question):
    question_lower = question.lower()
    return "NICHT" in question or \
            ("am wenigsten" in question_lower and "mindestens" not in question_lower) or \
            "NIE" in question or "NIEMALS" in question


def is_opposite_english(question):
    question_lower = question.lower()
    return "NOT" in question or \
            ("least" in question_lower and "at least" not in question_lower) or \
            "NEVER" in question


ALL_OPPOSITE_FUNCTIONS =  {"en-uk": is_opposite_english, 
                           "en-us": is_opposite_german,
                           "de": is_opposite_german}


GOOGLE_URL = ""
STOP_WORDS = ""
QUESTION_WORDS = ""
IS_OPPOSITE_FUNCTION = None
TextBlob = None


def set_as(language):
    global GOOGLE_URL, STOP_WORDS, QUESTION_WORDS, IS_OPPOSITE_FUNCTION, TextBlob
    GOOGLE_URL = ALL_GOOGLE_URLS[language]
    STOP_WORDS = ALL_STOP_WORDS[language]
    QUESTION_WORDS = ALL_QUESTION_WORDS[language]
    IS_OPPOSITE_FUNCTION = ALL_OPPOSITE_FUNCTIONS[language]
    TextBlob = TEXT_BLOBS[language]


# Default english uk
set_as(DEFAULT)
