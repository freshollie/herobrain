FROM python:3.6
RUN pip install pipenv

WORKDIR /hqhero-reporter

COPY Pipfile.lock Pipfile ./
RUN pipenv install --deploy --system --ignore-pipfile && \
    python3.6 -m nltk.downloader 'punkt' 'averaged_perceptron_tagger' 'stopwords' && \
    python3.6 -m textblob.download_corpora

COPY src src

ENTRYPOINT ["python3.6", "-u", "/hqhero-reporter/src/run.py"]
