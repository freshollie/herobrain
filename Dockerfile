FROM python:3.6
RUN pip install pipenv

WORKDIR /reporter

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy
RUN pipenv run nltk-install

COPY src src

CMD python3.6 /reporter/src/run.py --token test