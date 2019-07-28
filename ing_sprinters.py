from collections import defaultdict
from bs4 import BeautifulSoup
from emoji import emojize
import requests
import re
import _pickle as pickle


# Paging
def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


# Check database
def database():
    with open('database.pkl', 'rb') as file:
        try:
            data = pickle.load(file)
            # Output user's data, not everything
        except EOFError:
            data = {}

    return data


# New user
def new_user(user_id):
    data = database()

    with open('database.pkl', 'wb') as file:
        data[user_id] = {
            "Track": {},
            "List": None,
            "Settings": {
                "ISIN": "✅Enabled",
                "Bied": "✅Enabled",
                "Laat": "✅Enabled",
                "%1 dag": "✅Enabled",
                "Hefboom": "✅Enabled",
                "Stop loss-niveau": "✅Enabled",
                "Referentie": "✅Enabled"
            }
        }

        pickle.dump(data, file)


# User settings
def settings(user_id, query):
    data = database()

    with open('database.pkl', 'wb') as file:
        if data[user_id]["Settings"][query] == "✅Enabled":
            data[user_id]["Settings"][query] = "❌Disabled"
        else:
            data[user_id]["Settings"][query] = "✅Enabled"

        pickle.dump(data, file)

    return data[user_id]["Settings"][query]


# Add sprinter to database
def add(user_id, ISIN):
    market = sprinter_check(ISIN)

    if market is False:
        return None

    if market is None:
        message = "Something went wrong, try again later!"
        return message

    data = database()

    with open('database.pkl', 'wb') as file:
        if user_id not in data.keys():  # Add user
            new_user(user_id)

        data[user_id]["Track"].setdefault(market, []).append(ISIN)

        message = "Sprinter added!"

        pickle.dump(data, file)

    return message


# Remove sprinter from database
def remove(user_id, query):
    ISIN = query.split()[-1]
    query = "".join(query.split()[:-1])

    data = database()

    with open('database.pkl', 'wb') as file:
        if user_id not in data.keys():  # Add user
            new_user(user_id)

        try:
            data[user_id]["Track"][query].remove(ISIN)
        except ValueError:
            message = "Sprinter not found!"

        if data[user_id]["Track"][query] == []:
            data[user_id]["Track"].pop(query, None)

        message = "Sprinter removed!"

        pickle.dump(data, file)

    return message


def add_to_list(user_id, sprinter, ISIN):
    result = sprinter_info(ISIN)
    if result is None:
        return ''

    data = database()
    data = data[user_id]["Settings"]

    keys = list(result.keys())
    values = list(result.values())

    message = ""
    val1 = ""
    val2 = ""

    if "-" in values[2]:
        val1 = emojize(':down_arrow:')  # ⬇️
    elif float(values[2][:-2].replace(",", ".")) != 0.00:
        val1 = emojize(':up_arrow:')  # ⬆️

    if "-" in values[5][1]:
        val2 = emojize(':down_arrow:')  # ⬇️
    elif "+" in values[5][1]:
        val2 = emojize(':up_arrow:')  # ⬆️

    message = '*' + sprinter + '*'
    if data["ISIN"] == "✅Enabled":
        message += ("\n*ISIN*                            _%s_" % (ISIN))
    if data["Bied"] == "✅Enabled":
        message += ("\n*%s*                           _%s_" % (keys[0], values[0]))
    if data["Laat"] == "✅Enabled":
        message += ("\n*%s*                           _%s_" % (keys[1], values[1]))
    if data["%1 dag"] == "✅Enabled":
        message += ("\n*%s*                    _%s_ _%s_" % (keys[2], val1, values[2]))
    if data["Hefboom"] == "✅Enabled":
        message += ("\n*%s*                 _%s_" % (keys[3], values[3]))
    if data["Stop loss-niveau"] == "✅Enabled":
        message += ("\n*%s*  _%s_" % (keys[4], values[4]))
    if data["Referentie"] == "✅Enabled":
        message += ("\n*%s*   _%s_ _%s_ _%s_\n\n" % (keys[5], val2, values[5][0], values[5][1]))

    return message


# Get list of markets
def markets():
    url = 'https://www.ingsprinters.nl/sprinters/'

    r = requests.get(url)
    if r.status_code == 200:
        payload = []
        soup = BeautifulSoup(r.content, "html.parser")

        data = soup.find("div", class_="grid grid--wrap grid--align-start")
        names = data.find_all("a", class_="list-group__label")

        # To return a list
        for x in range(0, len(names)):
            payload.append(names[x].get_text().strip().replace("é", "e"))

        data = database()
        with open('database.pkl', 'wb') as file:
            data["markets"] = payload
            pickle.dump(data, file)
        return payload

    else:
        return None


# Get market info
def market_info(market):
    market = market.replace('(', '')
    market = market.replace(')', '')
    market = market.replace(' ', '-')

    url = 'https://www.ingsprinters.nl/sprinters/' + market

    r = requests.get(url)
    if r.status_code == 200:
        payload = {}
        soup = BeautifulSoup(r.content, "html.parser")

        data = soup.find("div", class_="card__body")
        key = data.find("h2", class_="h4 no-margin").text.strip()
        value = data.find_all("span")

        payload[key.replace("*", "")] = value[0].text.strip() + ' ' + value[1].text.strip()

        return payload

    else:
        return None


# Get list of current long and short sprinters from a certain market
# Expects a string (generated by markets()) that contains Long or Short (added to the string) at the end
def sprinter_list(sprinter):
    query = sprinter.split()

    url = 'https://www.ingsprinters.nl/zoeken?q=' + ' '.join(query[:-1])

    r = requests.get(url)
    if r.status_code == 200:
        payload = {}
        soup = BeautifulSoup(r.content, "html.parser")

        data = soup.find_all("a", class_="fill-cell")
        for item in data:
            if query[-1].capitalize() in item.get_text():
                payload[item.get_text()] = re.sub(r'.*/NL', 'NL', item.get('href'))

        return payload

    else:
        return None


# Get data from the sprinter
# Expects sprinter ISIN (generated by sprinter_list())
# To do:
# - Add check if sprinter still exists
def sprinter_info(ISIN):
    url = 'https://www.ingsprinters.nl/zoeken?q=' + ISIN

    r = requests.get(url)
    if r.status_code == 200:
        payload = {}
        soup = BeautifulSoup(r.content, "html.parser")

        data = soup.find("div", class_="meta-block__row")
        name = data.find_all("h3", class_="meta__heading no-margin")
        date = data.find_all("span", class_=lambda x: x and x.startswith(
            'meta__value meta__value--l'))

        for x in range(len(name)):
            if x < (len(name) - 1):
                payload[name[x].text.strip()] = date[x].text.strip()
            else:
                payload[name[x].text.strip().replace("*", "")] = [date[x].text.strip(), date[6].text.strip()]

        return payload

    else:
        return None


# Checks if the sprinter exists
def sprinter_check(ISIN):
    url = 'https://www.ingsprinters.nl/zoeken?q=' + ISIN

    r = requests.get(url)

    if r.status_code == 200:
        soup = BeautifulSoup(r.content, "html.parser")
        data = soup.find("div", class_="container")

        if "'noSearchResults': true" in data.text:
            return False
        else:
            market = soup.find_all("span", itemprop="name")[1]
            return market.text
    else:
        return None
