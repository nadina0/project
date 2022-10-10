import argparse

dictionary = {
  "date_range": "Mar 21 - Apr 20",
  "current_date": "October 6, 2022",
  "description": "Someone has been making a veritable hobby of aggravating you, and it's come to a peak. You've had it with being nice, making peace and doing your best to keep all parties cooperative. It's time to retaliate.",
  "compatibility": "Virgo",
  "mood": "Aggressive",
  "color": "Sky Blue",
  "lucky_number": "48",
  "lucky_time": "6pm"
}

parser = argparse.ArgumentParser()
parser.add_argument("argument")
args = parser.parse_args()

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



for key, value in dictionary.items():
    if key == args.argument:
        print(value)
    
