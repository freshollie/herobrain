FROM python:3.6
RUN pip install pipenv

WORKDIR /herobrain

COPY Pipfile.lock Pipfile .nltk-install.sh ./
RUN pipenv install --deploy --system --ignore-pipfile && \
    python3.6 -m nltk.downloader 'punkt' 'averaged_perceptron_tagger' 'stopwords' && \
    python3.6 -m textblob.download_corpora

COPY herobrain herobrain
COPY run.py .

# The u is for unbuffered output, so that docker logs works properly
ENTRYPOINT ["python3.6", "-u", "/herobrain/run.py"]
