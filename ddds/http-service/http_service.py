# -*- coding: utf-8 -*-

import json
from flask import Flask, request
from jinja2 import Environment

import requests

app = Flask(__name__)
environment = Environment()


def jsonfilter(value):
    return json.dumps(value)


environment.filters["json"] = jsonfilter


def error_response(message):
    response_template = environment.from_string("""
    {
      "status": "error",
      "message": {{message|json}},
      "data": {
        "version": "1.0"
      }
    }
    """)
    payload = response_template.render(message=message)
    response = app.response_class(
        response=payload,
        status=200,
        mimetype='application/json'
    )
    return response


def query_response(value, grammar_entry):
    response_template = environment.from_string("""
    {
      "status": "success",
      "data": {
        "version": "1.1",
        "result": [
          {
            "value": {{value|json}},
            "confidence": 1.0,
            "grammar_entry": {{grammar_entry|json}}
          }
        ]
      }
    }
    """)
    payload = response_template.render(value=value, grammar_entry=grammar_entry)
    response = app.response_class(
        response=payload,
        status=200,
        mimetype='application/json'
    )
    return response


def multiple_query_response(results):
    response_template = environment.from_string("""
    {
      "status": "success",
      "data": {
        "version": "1.0",
        "result": [
        {% for result in results %}
          {
            "value": {{result.value|json}},
            "confidence": 1.0,
            "grammar_entry": {{result.grammar_entry|json}}
          }{{"," if not loop.last}}
        {% endfor %}
        ]
      }
    }
     """)
    payload = response_template.render(results=results)
    response = app.response_class(
        response=payload,
        status=200,
        mimetype='application/json'
    )
    return response


def validator_response(is_valid):
    response_template = environment.from_string("""
    {
      "status": "success",
      "data": {
        "version": "1.0",
        "is_valid": {{is_valid|json}}
      }
    }
    """)
    payload = response_template.render(is_valid=is_valid)
    response = app.response_class(
        response=payload,
        status=200,
        mimetype='application/json'
    )
    return response


@app.route("/dummy_query_response", methods=['POST'])
def dummy_query_response():
    response_template = environment.from_string("""
    {
      "status": "success",
      "data": {
        "version": "1.1",
        "result": [
          {
            "value": "dummy",
            "confidence": 1.0,
            "grammar_entry": null
          }
        ]
      }
    }
     """)
    payload = response_template.render()
    response = app.response_class(
        response=payload,
        status=200,
        mimetype='application/json'
    )
    return response


@app.route("/action_success_response", methods=['POST'])
def action_success_response():
    response_template = environment.from_string("""
   {
     "status": "success",
     "data": {
       "version": "1.1"
     }
   }
   """)
    payload = response_template.render()
    response = app.response_class(
        response=payload,
        status=200,
        mimetype='application/json'
    )
    return response


def get_current_data(sign, day, info_choice):
  api_url = "https://aztro.sameerkumar.website/?sign="+sign+"&day="+day
  print(api_url)
  response = requests.post(api_url)
  data = response.json()
  print(response)
  return data

def get_card_data(card):
  api_url = "https://rws-cards-api.herokuapp.com/api/v1/cards"
  response = requests.get(api_url)
  data = response.json()
  print(response)
  return data


@app.route("/horoscope", methods=['POST'])
def get_horoscope():
    facts = request.get_json()["context"]["facts"]
    sign = facts["sign_search"]["grammar_entry"]
    day = facts["day_search"]["grammar_entry"]
    info_choice = facts["info_choice"]["grammar_entry"]
    if info_choice == "lucky number":
      info_choice = "lucky_number"
    if info_choice == "lucky time":
      info_choice = "lucky_time"
    api_response = get_current_data(sign, day, info_choice)
    for key, value in api_response.items():
      if key == info_choice:
        chosen_category = value
        break
    return query_response(value=chosen_category, grammar_entry=None)


@app.route("/tarot_card_question", methods=['POST'])
def get_tarot():
    facts = request.get_json()["context"]["facts"]
    card = facts["card_search"]["grammar_entry"]
    api_response = get_card_data(card)
    for the_card in api_response['cards']:
      if the_card['name'] == card:
        chosen_card_up = the_card['meaning_up']
        chosen_card_reversed = the_card['meaning_rev']
        break
    return query_response(value=f'Your card upright means: {chosen_card_up}. Reversed, it means: {chosen_card_reversed}', grammar_entry=None)
