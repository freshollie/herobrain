# Herobrain

Herobrain is a quiz prediction processor based on [HackQ-Trivia](https://github.com/Exaphis/HackQ-Trivia).

Herobrain was designed for use with [hqhero](https://github.com/freshollie/hqhero), and answers questions from HQTrivia.

## Running

Herobrain uses `pipenv` for package management.

1. `pipenv install --dev` will install all the required packages to ba able to run Herobrain
1. `pipenv run nltk-install` to install the language resources
1. `pipenv run python run.py` to run the processor

```
usage: run.py [-h] [-t TOKEN] [-s OUTPUT] [-l {en-uk,en-us,de}] [--test]
              [--quiz-api QUIZ_API] [--test-api TEST_API]
              [--log-level {critical,error,warning,info,debug}]

Herobrain, a quiz prediction processor

optional arguments:
  -h, --help            show this help message and exit
  -t TOKEN, --token TOKEN
                        HQTrivia bearer token
  -s OUTPUT, --output OUTPUT
                        HQhero server
  -l {en-uk,en-us,de}, --locale {en-uk,en-us,de}
                        Configures methods of question analysis
  --test                Run in test mode, doesn't require bearer token
  --quiz-api QUIZ_API   HQTrivia quiz-api
  --test-api TEST_API   Simulated quiz-api, requires --test
  --log-level {critical,error,warning,info,debug}
```

## Languages

Herobrain is designed for English and German. However the German processing is not amazing.

## Production

herobrain is designed for use with docker. An example service config

```yml
services:
  herobrain-uk:
    image: "freshollie/herobrain:master"
    networks:
      - hqhero-net
    command:
      - --token 
      - TOKEN
      - --hqhero 
      - http://hqhero-uk:1029/
      - --log-level 
      - debug

networks:
  hqhero-net:
```

## Auto-deployment

`bitbucket-piplines` were used to automatically build and deploy the herobrain image to hqhero.com.
this file can be edited for your bitbucket repository.
