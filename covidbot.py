import json
import os
import re

import pandas
import requests
from telebot import TeleBot, types
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
import secret
from cities import key_in_keys, region_name_and_code

POINTS = [
    'Красноярск',
    'Россия',
    'Беларусь'
]


bot = TeleBot(os.environ.get("API_KEY", secret.API_KEY))

def get_point_buttons():
    return [types.KeyboardButton(point) for point in POINTS]

def get_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(*get_point_buttons())

    return markup

def get_stats_values(first_day, second_day):
    sick = first_day.get('sick')
    diff_sick = int(first_day.get('sick')) - int(second_day.get('sick'))
    healed = first_day.get('healed')
    diff_healed = int(first_day.get('healed')) - int(second_day.get('healed'))
    died = first_day.get('died')
    diff_died = int(first_day.get('died')) - int(second_day.get('died'))

    return {
        "sick": sick,
        "diff_sick": diff_sick,
        "healed": healed,
        "diff_healed": diff_healed,
        "died": died,
        "diff_died": diff_died
    }

def build_statistics_message(data, place):
    today_data = data[0]
    yesterday_data = data[1]
    last_date = today_data.get('date')
    values = get_stats_values(today_data, yesterday_data)
    if datetime.strptime(last_date, '%d.%m.%Y').date() == datetime.today().date():
        header = f"<b>Данные на сегодня ({last_date}) по" \
                 f"{'' if place in ['Беларуси', 'России'] else ' региону'} {place}</b>:\n"
    else:
        header = f"<b>На сегодня данных еще нет!</b>\n" \
                 f"Последние данные по{'' if place in ['Беларуси', 'России'] else ' региону'} " \
                 f"{place} <b>на {last_date}</b>:\n"

    main_stats = f"<b>Заболевших</b>: {values['sick']} (+{values['diff_sick']})\n" \
                 f"<b>Выздоровевших</b>: {values['healed']} (+{values['diff_healed']})\n" \
                 f"<b>Погибших</b>: {values['died']} (+{values['diff_died']})\n"

    return header + main_stats

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    user_mention = user.first_name if user.first_name else user.username
    response = f"Привет, <b>{user_mention}!</b>\n" \
               f"По какому городу/стране статистика интересует?"
    bot.send_message(
        message.chat.id,
        response,
        parse_mode='html',
        reply_markup=get_markup()
    )

@bot.message_handler(content_types=['text'])
def handle_message(message):
    point = message.text.strip().lower()

    if point == "россия":
        data = requests.get("https://xn--80aesfpebagmfblc0a.xn--p1ai/information/")
        if data.status_code != 200:
            bot.send_message(
                message.chat.id,
                "Извините, какой-то сбой, не могу получить данные!",
                parse_mode='html',
                reply_markup=get_markup()
            )
            return

        soup = BeautifulSoup(data.text, 'lxml')
        result = soup.find("cv-stats-virus")
        if result:
            charts_data = result.attrs.get(":charts-data", "")
            if charts_data:
                charts_data_json = json.loads(charts_data)
                message_text = build_statistics_message(charts_data_json, "России")
                bot.send_message(
                    message.chat.id,
                    message_text,
                    parse_mode='html',
                    reply_markup=get_markup()
                )
                return
        bot.send_message(
            message.chat.id,
            "Извините, какой-то сбой, не могу получить данные!",
            parse_mode='html',
            reply_markup=get_markup()
        )
        return
    # elif point == "беларусь":
    #     date = datetime.today()
    #     link = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/{date}.csv"
    #
    #     data = requests.get(link.format(date=date.strftime('%m-%d-%Y')))
    #     if data.status_code != 200:
    #         if data.status_code == 404:
    #             date = datetime.today() - timedelta(days=1)
    #             data = requests.get(link.format(date=date.strftime('%m-%d-%Y')))
    #             if data.status_code != 200:
    #                 bot.send_message(
    #                     message.chat.id,
    #                     "Извините, какой-то сбой, не могу получить данные!",
    #                     parse_mode='html',
    #                     reply_markup=get_markup()
    #                 )
    #                 return
    #
    #     database = pandas.read_csv(link.format(date=date.strftime('%m-%d-%Y')), index_col='Country_Region')
    #     sick = database["Confirmed"]["Belarus"]
    #     healed = database["Recovered"]["Belarus"]
    #     died = database["Deaths"]["Belarus"]
    #     result = [{
    #         "sick":sick,
    #         "healed": healed,
    #         "died": died,
    #         "date": date.strftime("%d.%m.%Y")
    #     }]
    #
    #     database_yesterday = pandas.read_csv(
    #         link.format(date=(date - timedelta(days=1)).strftime('%m-%d-%Y')),
    #         index_col='Country_Region'
    #     )
    #     result.append(
    #         {
    #             "sick": database_yesterday["Confirmed"]["Belarus"],
    #             "healed": database_yesterday["Recovered"]["Belarus"],
    #             "died": database_yesterday["Deaths"]["Belarus"],
    #             "date": (date - timedelta(days=1)).strftime('%d.%m.%Y')
    #         }
    #     )
    #     message_text = build_statistics_message(result, "Беларуси")
    #
    #     bot.send_message(
    #         message.chat.id,
    #         message_text,
    #         parse_mode='html',
    #         reply_markup=get_markup()
    #     )
    #     return
    elif point == "беларусь":
        today = datetime.today()
        yesterday = today - timedelta(days=1)
        pre_yesterday = today - timedelta(days=2)
        today_find_date = today.strftime("%d %B")
        yesterday_find_date = yesterday.strftime("%d %B")
        pre_yesterday_find_date = pre_yesterday.strftime("%d %B")
        if today_find_date[0] == "0":
            today_find_date = today_find_date[1:]
        if yesterday_find_date[0] == "0":
            yesterday_find_date = yesterday_find_date[1:]
        if pre_yesterday_find_date[0] == "0":
            pre_yesterday_find_date = pre_yesterday_find_date[1:]

        link = "https://en.wikipedia.org/wiki/COVID-19_pandemic_in_Belarus"

        data = requests.get(link)
        if data.status_code != 200:
            bot.send_message(
                message.chat.id,
                "Извините, какой-то сбой, не могу получить данные!",
                parse_mode='html',
                reply_markup=get_markup()
            )
            return

        soup = BeautifulSoup(data.text, 'lxml')
        result = soup.select("p > b")
        today_data = {}
        yesterday_data = {}
        pre_yesterday_data = {}
        for item in reversed(result):
            confirmed = ""
            recoveries = ""
            deaths = ""
            if item.text == today_find_date:
                info = item.parent.contents[2]
                confirmed = re.findall("([0-9]+[,[0-9]+)?( confirmed cases)", info)[0][0].replace(",", "")
                recoveries = re.findall("([0-9]+[,[0-9]+)?( recoveries)", info)[0][0].replace(",", "")
                deaths = re.findall("([0-9]+[,[0-9]+)?( deaths)", info)[0][0].replace(",", "")
                today_data = {
                    "date": datetime.today().strftime('%d.%m.%Y'),
                    "sick": int(confirmed),
                    "healed": int(recoveries),
                    "died": int(deaths)
                }
            if item.text == yesterday_find_date:
                info = item.parent.contents[2]
                confirmed = re.findall("([0-9]+[,[0-9]+)?( confirmed cases)", info)[0][0].replace(",", "")
                recoveries = re.findall("([0-9]+[,[0-9]+)?( recoveries)", info)[0][0].replace(",", "")
                deaths = re.findall("([0-9]+[,[0-9]+)?( deaths)", info)[0][0].replace(",", "")
                yesterday_data = {
                    "date": (datetime.today() - timedelta(days=1)).strftime('%d.%m.%Y'),
                    "sick": int(confirmed),
                    "healed": int(recoveries),
                    "died": int(deaths)
                }
            if item.text == pre_yesterday_find_date:
                info = item.parent.contents[2]
                confirmed = re.findall("([0-9]+[,[0-9]+)?( confirmed cases)", info)[0][0].replace(",", "")
                recoveries = re.findall("([0-9]+[,[0-9]+)?( recoveries)", info)[0][0].replace(",", "")
                deaths = re.findall("([0-9]+[,[0-9]+)?( deaths)", info)[0][0].replace(",", "")
                pre_yesterday_data = {
                    "date": (datetime.today() - timedelta(days=2)).strftime('%d.%m.%Y'),
                    "sick": int(confirmed),
                    "healed": int(recoveries),
                    "died": int(deaths)
                }

        result = []
        if today_data:
            result.append(today_data)
        if yesterday_data:
            result.append(yesterday_data)
        if pre_yesterday_data:
            result.append(pre_yesterday_data)

        message_text = build_statistics_message(result, "Беларуси")

        bot.send_message(
            message.chat.id,
            message_text,
            parse_mode='html',
            reply_markup=get_markup()
        )
        return
    elif key_in_keys(point):
        result = region_name_and_code(point)
        if result is not None:
            data = requests.get(
                f"https://xn--80aesfpebagmfblc0a.xn--p1ai/"
                f"covid_data.json?do=region_stats&code=RU-{result[1]}"
            )
            if data.status_code != 200:
                bot.send_message(
                    message.chat.id,
                    "Извините, какой-то сбой, не могу получить данные!",
                    parse_mode='html',
                    reply_markup=get_markup()
                )
                return
            else:
                data = data.json()

            message_text = build_statistics_message(data, result[0])

            bot.send_message(
                message.chat.id,
                message_text,
                parse_mode='html',
                reply_markup=get_markup()
            )
            return

    bot.send_message(
        message.chat.id,
        "Не удалось найти указанный Вами регион/город.\n"
        "Попробуйте ввести столицу Вашего региона.",
        parse_mode='html',
        reply_markup=get_markup()
    )


bot.polling(none_stop=True)