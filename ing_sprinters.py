from requests_html import HTMLSession
from collections import defaultdict
from emoji import emojize
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
                "isin": "✅Enabled",
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
def add(user_id, isin):
    result = sprinter_check(isin)

    if result == "Beëindigd":
        message = "This sprinter doesn't exist!"
        return message

    if result is None:
        message = "Something went wrong, try again later!"
        return message

    data = database()

    with open('database.pkl', 'wb') as file:
        if user_id not in data.keys():  # Add user
            new_user(user_id)

        if isin not in data[user_id]["Track"].setdefault(result, []):
            data[user_id]["Track"].setdefault(result, []).append(isin)
            message = "Sprinter added!"
        else:
            message = "Sprinter is already in your list!"

        pickle.dump(data, file)

    return message


# Remove sprinter from database
def remove(user_id, query):
    isin = query.split()[-1]
    query = " ".join(query.split()[:-1])

    data = database()
    track = data[user_id]["Track"]

    with open('database.pkl', 'wb') as file:
        if user_id not in data.keys():  # Add user
            new_user(user_id)

        if query in track:
            if isin in track[query]:
                track[query].remove(isin)
            if track[query] == []:
                track.pop(query, None)

        message = "Sprinter removed!"

        pickle.dump(data, file)

    return message


def add_to_list(myList):
    user_id = myList[0]
    sprinter = myList[1]
    isin = myList[2]
    result = sprinter_check(isin)

    if result == "Beëindigd":
        remove(user_id, (sprinter + ' ' + isin))
        message = '[' + sprinter + '](https://www.ingsprinters.nl/markten/indices/' + sprinter + ') is removed.\n'
        return message
    elif result is None:
        message = '[' + sprinter + '](https://www.ingsprinters.nl/markten/indices/' + sprinter + ') could not be found or loaded.\n'
        return message

    result = sprinter_info(isin)

    data = database()
    data = data[user_id]["Settings"]

    keys = list(result.keys())
    values = list(result.values())

    message = ""
    table = []
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

    message = '[' + sprinter + '](https://www.ingsprinters.nl/markten/indices/' + sprinter + ')'
    if data["isin"] == "✅Enabled":
        message += ("\n*isin*                            [%s](https://www.ingsprinters.nl/zoeken?q=%s)" % (isin, isin))
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


    # table.append(['[' + sprinter + '](https://www.ingsprinters.nl/markten/indices/' + sprinter + ')'])
    # if data["isin"] == "✅Enabled":
    #     table.append(["*isin*", "[%s](https://www.ingsprinters.nl/zoeken?q=%s)" % (isin, isin)])
    # if data["Bied"] == "✅Enabled":
    #     table.append(["*%s*" % keys[0], "_%s_" % values[0]])
    # if data["Laat"] == "✅Enabled":
    #     table.append(["*%s*" % keys[1], "_%s_" % values[1]])
    # if data["%1 dag"] == "✅Enabled":
    #     table.append(["*%s*" % keys[2], "_%s_" % val1, "_%s_" % values[2]])
    # if data["Hefboom"] == "✅Enabled":
    #     table.append(["*%s*" % keys[3], "_%s_" % values[3]])
    # if data["Stop loss-niveau"] == "✅Enabled":
    #     table.append(["*%s*" % keys[4], "_%s_" % values[4]])
    # if data["Referentie"] == "✅Enabled":
    #     table.append(["*%s*" % keys[5], "_%s_" % val2, "_%s_" % values[5][0], "_%s_" % values[5][1]])

    # Returns list of lists
    return message


# Get list of markets
def markets():
    url = 'https://www.ingsprinters.nl/sprinters/'

    r = HTMLSession().get(url)
    payload = []

    names = r.html.find('a.list-group__label')

    # To return a list
    for x in range(0, len(names)):
        payload.append(names[x].text.strip().replace("é", "e"))

    data = database()
    with open('database.pkl', 'wb') as file:
        data["markets"] = payload
        pickle.dump(data, file)
    return payload


# Get market info
def market_info(market):
    market = market.replace('(', '')
    market = market.replace(')', '')
    market = market.replace(' ', '-')

    url = 'https://www.ingsprinters.nl/sprinters/' + market

    r = HTMLSession().get(url)
    payload = {}

    key = r.html.find('h2.h4,no-margin', clean=True)[0].text
    value = r.html.find('span', clean=True)

    payload[key.replace("*", "")] = value[3].text.strip() + ' ' + value[4].text.strip()

    return payload


# Get list of current long and short sprinters from a certain market
# Expects a string (generated by markets()) that contains Long or Short (added to the string) at the end
def sprinter_list(sprinter):
    query = sprinter.split()

    url = 'https://www.ingsprinters.nl/zoeken?q=' + ' '.join(query[:-1])

    r = HTMLSession().get(url)
    payload = {}
    data = r.html.find('a.fill-cell', clean=True)

    for item in data:
        if 'long'.capitalize() in item.text:
            payload[item.text] = re.sub(r'.*/NL', 'NL', item.attrs["href"])

    return payload


# Get data from the sprinter
# Expects sprinter isin (generated by sprinter_list())
# To do:
# - Add check if sprinter still exists
def sprinter_info(isin):
    url = 'https://www.ingsprinters.nl/zoeken?q=' + isin

    r = HTMLSession().get(url)
    payload = {}

    name = r.html.find(selector='h3.meta__heading.no-margin', clean=True)
    data = r.html.find(selector='span.meta__value.meta__value--l', clean=True)

    for x in range(len(name)):
        if x < (len(name) - 1):
            payload[name[x].text.strip()] = data[x].text.strip()
        else:
            payload[name[x].text.strip().replace(
                "*", "")] = [data[x].text.strip(), data[6].text.strip()]
    return payload


# Checks if the sprinter exists
def sprinter_check(isin):
    url = 'https://www.ingsprinters.nl/zoeken?q=' + isin

    r = HTMLSession().get(url)

    data = r.html.find(selector='span[itemprop=name]')

    try:
        data = data[1].text
    except IndexError:
        data = None

    return data
