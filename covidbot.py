import json
import os
import re

import requests
from telebot import TeleBot, types
from datetime import datetime

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
    sick = int(first_day.get('sick', 0))
    diff_sick = sick - int(second_day.get('sick', 0))
    healed = int(first_day.get('healed', 0))
    diff_healed = healed - int(second_day.get('healed', 0))
    died = int(first_day.get('died', 0))
    diff_died = died - int(second_day.get('died', 0))

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
    message_text = ""
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

    elif point == "беларусь":
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
        result = soup.select("p > b, td > b")

        result_data = []
        for item in list(reversed(result))[:3]:
            info = item.parent.contents[2]
            confirmed = re.findall("([0-9]+[,[0-9]+)?( confirmed cases)", info)[0][0].replace(",", "")
            recoveries = re.findall("([0-9]+[,[0-9]+)?( recoveries)", info)[0][0].replace(",", "")
            deaths = re.findall("([0-9]+[,[0-9]+)?( deaths)", info)[0][0].replace(",", "")
            result_data.append(
                {
                    "date": datetime.strptime(f"{item.text.strip()} 2020", "%d %B %Y").strftime('%d.%m.%Y'),
                    "sick": int(confirmed),
                    "healed": int(recoveries),
                    "died": int(deaths)
                }
            )
        message_text = build_statistics_message(result_data, "Беларуси")
    elif key_in_keys(point):
        result = region_name_and_code(point)
        if result is not None:
            data = requests.get(
                f"https://xn--80aesfpebagmfblc0a.xn--p1ai/"
                f"covid_data.json?do=region_stats&code=RU-{result.code}"
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

            message_text = build_statistics_message(data, result.region)

    if message_text:
        bot.send_message(
            message.chat.id,
            message_text,
            parse_mode='html',
            reply_markup=get_markup()
        )
    else:
        bot.send_message(
            message.chat.id,
            "Не удалось найти указанный Вами регион/город.\n"
            "Попробуйте ввести столицу Вашего региона.",
            parse_mode='html',
            reply_markup=get_markup()
        )


bot.polling(none_stop=True)
