import itertools
import re
import time
import asyncio
from collections import defaultdict

from colorama import Fore, Style

import search

PUNCTUATION_TO_NONE = str.maketrans({key: None for key in "!\"#$%&\'()*+,-.:;<=>?@[\\]^_`{|}~�"})
PUNCTUATION_TO_SPACE = str.maketrans({key: " " for key in "!\"#$%&\'()*+,-.:;<=>?@[\\]^_`{|}~�"})

class QuestionAnalyser:
    SEARCH_NUMBER = 5

    def __init__(self, question_str, answers):
        self._original_answers = answers
        self._question = question_str
        
        self._parsed_answers = []
        self._is_opposite = False
        self._question_keywords = []
        self._unique_question_keywords =[]
        self._key_nouns = {}
        self._analyse()

    def _analyse(self):
        '''
        Analyse the question, extracting the key
        information, ready to perform a search
        for that information
        '''

        ### Remove punctuation and other symbols from the answers ####
        self._parsed_answers = []
        for answer in self._original_answers:
            self._parsed_answers.append(answer.translate(PUNCTUATION_TO_NONE))
            self._parsed_answers.append(answer.translate(PUNCTUATION_TO_SPACE))
        # Remove dupilcates
        self._parsed_answers = list(dict.fromkeys(self._parsed_answers))
        print(self._parsed_answers)

        
        ### Work out if this queston is actually the opposite ####
        question_lower = self._question.lower()
        self._is_opposite = "NOT" in self._question or\
                          ("least" in question_lower and "at least" not in question_lower) or\
                           "NEVER" in self._question

        #### Get all words in quotes ####
        quoted = re.findall('"([^"]*)"', question_lower)  
        no_quote = question_lower
        for quote in quoted:
            no_quote = no_quote.replace(f"\"{quote}\"", "1placeholder1")
        
        #### Extract the keywords from the question ####
        self._question_keywords = search.find_keywords(no_quote)
        for quote in quoted:
            self._question_keywords[self._question_keywords.index("1placeholder1")] = quote
        
        self._unique_question_keywords = list(set(self._question_keywords))

        #### Extract key nouns from the question ####
        self._key_nouns = set(quoted)

        q_word_location = search.find_q_word_location(question_lower)
        if len(self._key_nouns) == 0:
            if q_word_location > len(self._question) // 2 or q_word_location == -1:
                self._key_nouns.update(search.find_nouns(self._question, num_words=5))
            else:
                self._key_nouns.update(search.find_nouns(self._question, num_words=5, reverse=True))

            self._key_nouns -= {"type"}

        # Add consecutive capitalised words (Thanks talentoscope!)
        self._key_nouns.update(re.findall(r"([A-Z][a-z]+(?=\s[A-Z])(?:\s[A-Z][a-z]+)+)",
                                    " ".join([w for idx, w in enumerate(self._question.split(" ")) if idx != q_word_location])))
        self._key_nouns = {noun.lower() for noun in self._key_nouns}


        print(f"Question nouns: {self._key_nouns}")
        print(self._question_keywords)

    def get_analysis(self):
        return {
            "nouns": self._key_nouns,
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
        searches = [self._find_texts_about_question(), self._find_texts_about_answers()]
        texts_about_question, texts_about_answers = await asyncio.gather(*searches)

        analysis_1 = _analysis_method1(texts_about_question, self._parsed_answers, self._is_opposite)
        analysis_2 = _analysis_method2(texts_about_question, self._parsed_answers, self._is_opposite)
        analysis_3 = _analysis_method3(texts_about_answers, 
                                        self._unique_question_keywords,
                                        self._key_nouns, 
                                        self._original_answers, 
                                        self._is_opposite)

        return analysis_1, analysis_2, analysis_3


def _analysis_method1(texts, answers, opposite):
    """
    Returns the answer with the maximum/minimum number of exact occurrences in the texts.
    :param texts: List of text to analyze
    :param answers: List of answers
    :param opposite: True if the best answer occurs the least, False otherwise
    :return: Answer that occurs the most/least in the texts, empty string if there is a tie
    """
    print("Running method 1")
    counts = {answer.lower(): 0 for answer in answers}

    for text in texts:
        for answer in counts:
            counts[answer] += len(re.findall(f" {answer} ", text))

    predicted_answer = ""

    # If not all answers have count of 0 and the best value doesn't occur more than once, return the best answer
    best_value = min(counts.values()) if opposite else max(counts.values())
    if not all(c == 0 for c in counts.values()) and list(counts.values()).count(best_value) == 1:
        predicted_answer = min(counts, key=counts.get) if opposite else max(counts, key=counts.get)
    
    return {
        "prediction": predicted_answer,
        "answers": counts
    }


def _analysis_method2(texts, answers, reverse):
    """
    Return the answer with the maximum/minimum number of keyword occurrences in the texts.
    :param texts: List of text to analyze
    :param answers: List of answers
    :param reverse: True if the best answer occurs the least, False otherwise
    :return: Answer whose keywords occur most/least in the texts
    """
    print("Running method 2")
    counts = {answer: {keyword: 0 for keyword in search.find_keywords(answer)} for answer in answers}

    for text in texts:
        for keyword_counts in counts.values():
            for keyword in keyword_counts:
                keyword_counts[keyword] += len(re.findall(f" {keyword} ", text))

    counts_sum = {answer: sum(keyword_counts.values()) for answer, keyword_counts in counts.items()}

    predicted_answer = ""
    if not all(c == 0 for c in counts_sum.values()):
        predicted_answer = min(counts_sum, key=counts_sum.get) if reverse else max(counts_sum, key=counts_sum.get)
    
    return {
        "prediction": predicted_answer,
        "analysis": {"answers": counts_sum}
    }


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

    answer_scores = {answer: dict(scores) for answer, scores in answer_noun_scores_map.items()}

    predicted_answer = ""
    if set(noun_scores.values()) != {0}:
        predicted_answer =  min(noun_scores, key=noun_scores.get) if reverse else max(noun_scores, key=noun_scores.get)
    if set(keyword_scores.values()) != {0}:
        predicted_answer =  min(keyword_scores, key=keyword_scores.get) if reverse else max(keyword_scores, key=keyword_scores.get)

    return {
        "prediction": predicted_answer,
        "answers": answer_scores,
        "keywords": keyword_scores,
        "nouns": noun_scores 
    }


if __name__ == "__main__":
    question = "A fruit salad would likely include which of these things?"
    answers = ["Melon", "Corn muffins", "Seltzer water"]
    analyser = QuestionAnalyser(question, answers)
    print(analyser.get_analysis())

    # Find the probability of answers
    print(asyncio.get_event_loop().run_until_complete(analyser.find_answers()))