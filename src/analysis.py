import asyncio
import itertools
import logging
import re
import time
from collections import defaultdict

from nltk import word_tokenize
from nltk.tag.perceptron import PerceptronTagger
from nltk.tokenize import RegexpTokenizer

import search
import localisation

log = logging.getLogger(__name__)

PUNCTUATION_TO_NONE = str.maketrans({key: None for key in "!\"#$%&\'()*+,-.:;<=>?@[\\]^_`{|}~�“”"})
PUNCTUATION_TO_SPACE = str.maketrans({key: " " for key in "!\"#$%&\'()*+,-.:;<=>?@[\\]^_`{|}~�“”"})
FIX_QUOTES = str.maketrans("“”", "\"\"")

tokenizer = RegexpTokenizer(r"\w+")
tagger = PerceptronTagger()


def _is_opposite(question):
    '''
    Find out if this question is looking
    for the opposite meaning

    Use the localisation module, as the question
    requires different keywords in different countries
    '''
    return localisation.IS_OPPOSITE_FUNCTION(question)


def _find_keywords(words):
    """
    Returns the list of words given without stopwords.
    :param words: List of words
    :return: Words without stopwords
    """
    return [w for w in tokenizer.tokenize(words.lower()) if w not in localisation.STOP_WORDS]


def _find_nouns(text, num_words, reverse=False):
    tags = [tag for tag in localisation.TextBlob(text).tags if tag[1] != "POS"]
    log.debug(tags)

    tags = tags[:num_words] if not reverse else tags[-num_words:]

    nouns = []
    consecutive_nouns = []

    for tag in tags:
        tag_type = tag[1]
        word = tag[0]

        if "NN" not in tag_type and len(consecutive_nouns) > 0:
            nouns.append(" ".join(consecutive_nouns))
            consecutive_nouns = []
        elif "NN" in tag_type:
            consecutive_nouns.append(word)

    if len(consecutive_nouns) > 0:
        nouns.append(" ".join(consecutive_nouns))

    return nouns


def _find_q_word_location(question_lower):
    for q_word in localisation.QUESTION_WORDS:
        q_word_location = question_lower.find(q_word)
        if q_word_location != -1:
            return q_word_location
    return 0


def _generate_probabilities(counts, opposite):
    if opposite:
        for answer in counts:
            if counts[answer] > 0:
                counts[answer] = 1 / counts[answer]
            else:
                # When opposite, 0 answers are worth a lot
                counts[answer] = 100000

    count_sum = sum(counts.values())

    if count_sum == 0:
        return counts

    probabilities = {}
    for answer in counts:
        probabilities[answer] = (counts[answer] / count_sum)
    
    return probabilities


def _analysis_method1(texts, answers, opposite):
    """
    Returns the answer with the maximum/minimum number of exact occurrences in the texts.
    :param texts: List of text to analyze
    :param answers: List of answers
    :param opposite: True if the best answer occurs the least, False otherwise
    :return: Answer that occurs the most/least in the texts, empty string if there is a tie
    """
    print("Running method 1")
    counts = {answer: 0 for answer in answers}

    for text in texts:
        for answer in counts:
            counts[answer] += len(re.findall(f" {answer} ", text))

    log.debug(f"Method 1 counts: {counts}")
    answer_predictions = _generate_probabilities(counts, opposite)
    log.debug(f"Method 1 weights: {answer_predictions}")
    
    return answer_predictions


def _analysis_method2(texts, answers, reverse):
    """
    Return the answer with the maximum/minimum number of keyword occurrences in the texts.
    :param texts: List of text to analyze
    :param answers: List of answers
    :param reverse: True if the best answer occurs the least, False otherwise
    :return: Answer whose keywords occur most/least in the texts
    """
    print("Running method 2")
    counts = {answer: {keyword: 0 for keyword in _find_keywords(answer)} for answer in answers}

    for text in texts:
        for keyword_counts in counts.values():
            for keyword in keyword_counts:
                keyword_counts[keyword] += len(re.findall(f" {keyword} ", text))
    counts = {answer: sum(keyword_counts.values()) for answer, keyword_counts in counts.items()}

    log.debug(f"Method 2 counts: {counts}")
    answer_predictions = _generate_probabilities(counts, reverse)
    log.debug(f"Method 2 weights: {answer_predictions}")

    #if not all(c == 0 for c in counts_sum.values()):
    #    predicted_answer = min(counts_sum, key=counts_sum.get) if reverse else max(counts_sum, key=counts_sum.get)
    
    return answer_predictions


def _analysis_method3(answer_text_map, question_keywords, question_key_nouns, answers, reverse):
    """
    Returns the answer with the maximum number of occurrences of the question keywords in its searches.
    :param question_keywords: Keywords of the question
    :param question_key_nouns: Key nouns of the question
    :param answers: List of answers
    :param reverse: True if the best answer occurs the least, False otherwise
    :return: Answer whose search results contain the most keywords of the question
    """
    keyword_scores = {answer: 0 for answer in answers}
    noun_scores = {answer: 0 for answer in answers}

    # Create a dictionary of word to type of score so we avoid searching for the same thing twice in the same page
    word_score_map = defaultdict(list)
    for word in question_keywords:
        word_score_map[word].append("KW")
    for word in question_key_nouns:
        word_score_map[word].append("KN")

    answer_noun_scores_map = {}
    for answer, texts in answer_text_map.items():
        keyword_score = 0
        noun_score = 0
        noun_score_map = defaultdict(int)

        for text in texts:
            for keyword, score_types in word_score_map.items():
                score = len(re.findall(f" {keyword} ", text))
                if "KW" in score_types:
                    keyword_score += score
                if "KN" in score_types:
                    noun_score += score
                    noun_score_map[keyword] += score

        keyword_scores[answer] = keyword_score
        noun_scores[answer] = noun_score
        answer_noun_scores_map[answer] = noun_score_map
    
    summed_scores = {}

    for answer in keyword_scores:
        # Keywords are worth more than nouns
        summed_scores[answer] = (keyword_scores[answer] * 3/4) + (noun_scores[answer] * 1/4)
    
    prediction = _generate_probabilities(summed_scores, reverse)

    return prediction


class QuestionAnalyser:
    SEARCH_NUMBER = 7

    def __init__(self, question_str, answers):
        self._log = logging.getLogger(QuestionAnalyser.__name__)
        self._original_answers = answers
        self._question = question_str.translate(FIX_QUOTES)
        self._log.info(f"Question: {self._question}")
        
        self._parsed_answers = []
        self._parsed_answers_to_answer = {}

        self._is_opposite = False
        self._question_keywords = []
        self._unique_question_keywords =[]
        self._key_nouns = {}
        self._extract_info()

        self._log.info(self.get_analysis())

    def _extract_info(self):
        '''
        Analyse the question, extracting the key
        information, ready to perform a search
        for that information
        '''

        ### Remove punctuation and other symbols from the answers ####
        self._parsed_answers = []
        for answer in self._original_answers:
            # Remove the 's to replace with s as google will not care
            self._parsed_answers.append(answer.replace("'s ", "s ").translate(PUNCTUATION_TO_SPACE).lower())
            self._parsed_answers_to_answer[self._parsed_answers[-1]] = answer
        # Remove dupilcates
        self._parsed_answers = list(dict.fromkeys(self._parsed_answers))

        
        ### Work out if this queston is actually the opposite ###
        self._is_opposite = _is_opposite(self._question)

        #### Get all words in quotes ####
        question_lower = self._question.lower()
        quoted = re.findall('"([^"]*)"', question_lower)  
        no_quote = question_lower
        for quote in quoted:
            no_quote = no_quote.replace(f"\"{quote}\"", "1placeholder1")
        
        #### Extract the keywords from the question ####
        self._question_keywords = _find_keywords(no_quote)
        for quote in quoted:
            self._question_keywords[self._question_keywords.index("1placeholder1")] = quote
        
        self._unique_question_keywords = list(set(self._question_keywords))

        #### Extract nouns from the question, if there are no key nouns in the questions ####
        self._key_nouns = set(quoted)

        q_word_location = _find_q_word_location(question_lower)
        if len(self._key_nouns) == 0:
            if q_word_location > len(self._question) // 2 or q_word_location == -1:
                self._key_nouns.update(_find_nouns(self._question, num_words=5))
            else:
                self._key_nouns.update(_find_nouns(self._question, num_words=5, reverse=True))

            self._key_nouns -= {"type"}

        # Add consecutive capitalised words (Thanks talentoscope!)
        self._key_nouns.update(re.findall(r"([A-Z][a-z]+(?=\s[A-Z])(?:\s[A-Z][a-z]+)+)",
                                    " ".join([w for idx, w in enumerate(self._question.split(" ")) if idx != q_word_location])))
        self._key_nouns = {noun.lower() for noun in self._key_nouns}

    def get_analysis(self):
        return {
            "nouns": list(self._key_nouns),
            "keywords": self._question_keywords,
            "opposite": self._is_opposite,
            "parsedAnswers": self._parsed_answers
        }
    
    async def _find_texts_about_question(self):
        search_results = await search.search_google("+".join(self._question_keywords), QuestionAnalyser.SEARCH_NUMBER)
        return [x.translate(PUNCTUATION_TO_NONE) for x in await search.get_clean_texts(search_results)]

    async def _find_texts_about_answers(self):
        search_results = await search.multiple_search(self._parsed_answers, QuestionAnalyser.SEARCH_NUMBER)
        answer_lengths = list(map(len, search_results))
        search_results = itertools.chain.from_iterable(search_results)

        texts = [x.translate(PUNCTUATION_TO_NONE) for x in await search.get_clean_texts(search_results)]

        answer_text_map = {}
        for idx, length in enumerate(answer_lengths):
            answer_text_map[self._parsed_answers[idx]] = texts[0:length]
            del texts[0:length]
        
        return answer_text_map

    async def find_answers(self):
        # Perform all required searches for information about the question and it's answers
        searches = [self._find_texts_about_question(), self._find_texts_about_answers()]
        texts_about_question, texts_about_answers = await asyncio.gather(*searches)

        # Perfrom analysis on web results
        # Returning a confidence fraction per answer
        analysis_1 = _analysis_method1(texts_about_question, self._parsed_answers, self._is_opposite)
        analysis_2 = _analysis_method2(texts_about_question, self._parsed_answers, self._is_opposite)
        analysis_3 = _analysis_method3(texts_about_answers, 
                                       self._unique_question_keywords,
                                       self._key_nouns, 
                                       self._parsed_answers, 
                                       self._is_opposite)

        # Fix the keys for each method which we return as analysis for each method
        methods = []
        for analysis in (analysis_1, analysis_2, analysis_3):
            methods.append({self._parsed_answers_to_answer[answer]: weighting for answer, weighting in analysis.items()})

        self._log.debug(methods)

        self._log.info(f"Analysed {QuestionAnalyser.SEARCH_NUMBER * 2} pages, Reading {sum(map(len, texts_about_question)) + sum(map(len, texts_about_answers.values()))} words")
        
        # Combine the confidence fractions, giving 1 and 2 a higher confience than 3
        combined = {}
        for answer in analysis_1:
            combined[self._parsed_answers_to_answer[answer]] = analysis_1[answer] * 0.75 + analysis_2[answer] * 0.75 + analysis_3[answer] * 0.4
        probs = _generate_probabilities(combined, False)

        self._log.debug(f"Prediction: ")
        for answer in probs:
            self._log.debug(f" - {answer} - {round(probs[answer] * 100)}%")

        return probs, methods


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    async def test_en():
        localisation.set_as(localisation.ENGLISH_UK)
        print(await QuestionAnalyser("Which colour is NOT in on the Italian flag?", ["Green", "Red", "Blue"]).find_answers())
    
    async def test_de():
        localisation.set_as(localisation.GERMANY)
        print(await QuestionAnalyser("Wenn man \"Doppelkopf\" spielt, dann spielt man...?", ["Russisch Roulette falsh", "Ein Kartenspiel", "an sich rum"]).find_answers())
    
    asyncio.get_event_loop().run_until_complete(test_en())
    asyncio.get_event_loop().run_until_complete(test_de())
