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

for key, value in dictionary.items():
    if key == args.argument:
        print(value)
    
