---
name: logging-food
description: Use when the user wants to log a food that they have eaten or a drink that they have consumed during the day, or query today's or past usage
---

## First-time instructions
When this skill is invoked for the first time, ask for daily protein, carb and overall calorie goals, and the users resting energy. Store it in a settings.json file. 

## Instructions for food input
Store the food log of each day in a separate yyyy-mm-dd json file. If the file doesn't exist, create it.

The json file has the fields:
- date as yyyy-mm-dd
- items
- goals (calories, protein, carbs, fat)

where item has:
- name:
- description:
- protein
- carbs
- fat

The user will provide the description of the food they've eaten in natural language. Add it as an entry in the json,  show them the details along with daily summary. Be very terse. If they suggest changes, update the entry. 

The most common foods used by the user are specified below. Attempt to use those hints first. If not found:
- Use online calorie databases. Be precise in calculating Indian food quantities/macros/calories. Don't guess and don't hallucinate.
- Once the user approves suggested values for a new food, add it to a cache.json file for future use.

## User's foods

- By default, the coffee made at home is a Capuccino with 2% whole milk. It has 120ml of 2% milk, with 4g protein, 2.5g fat, 6.5g carbs, for a total of 65 cal. 
- If the user mentions they use whole milk, that's 4g protein, 4.5g fat, 5.5g carbs, for a total of 80 cal.
- A slice of bread is 120 cal - 20g carbs, 3g protein, 3g fat.
- A pasture raised organic whole brown egg is 70 cal - 0g carbs, 6g protein, 5g fat 

## Instructions for queries
When the user asks for a report, generate a daily report and past week's report. Provide appropriate visualizations. Also assuming the user hasn't worked out, provide a "fat added in the past week" metric (total calories consumed minus 7*resting energy). This could be negative.