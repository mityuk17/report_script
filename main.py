import os
from pathlib import Path
from pyrogram.raw import types
import openpyxl
from opentele.api import API, CreateNewSession, UseCurrentSession
from TGConvertor.manager.manager import SessionManager


def get_sessions():
    if not os.path.exists('sessions'):
        return False
    with os.scandir('sessions') as files:
        subdir = [file.name for file in files if file.is_dir() and os.path.exists(f'sessions/{file.name}/tdata')]
    print('Собрано сессий:', len(subdir))
    return subdir


def get_proxies():
    with open('proxies.txt', 'r') as file:
        data = file.readlines()
    for i in range(len(data)):
        data[i] = data[i].strip().split(':')
        data[i] = {
            'scheme': 'socks5',
            'hostname': data[i][0],
            'port': int(data[i][1]),
            'username': data[i][2],
            'password': data[i][3]
        }
    return data


def connect_proxies_to_accs():
    tdatas = get_sessions()
    proxies = get_proxies()
    accs = list()
    cur_pos = 0
    for i in tdatas:
        if cur_pos >= len(proxies):
            cur_pos = 0
        accs.append([i, proxies[cur_pos]])
        cur_pos += 1
    return accs


def get_tasks():
    tasks = list()
    wb = openpyxl.load_workbook('tasks.xlsx')
    sh = wb.active
#Структура таблицы: ссылка на канал | кол-во репортов | причина репортов
    for row in sh.values:
        task = {'channel_link' : row[0], 'amount' : int(row[1]), 'reason' : int(row[2])}
        tasks.append(task)
    return tasks


def assign_tasks():
    accs = connect_proxies_to_accs()
    tasks = get_tasks()
    for i in range(len(tasks)):
        if len(accs) < tasks[i]['amount']:
            print(f'Для задания {i+1} не хватает аккаунтов, будет отправлено {len(tasks)} репортов')
        tasks[i] = {'task': tasks[i], 'accs': accs}
    return tasks


def remove_session(session_name):
    os.replace(fr'sessions/{session_name}', fr'banned_sessions/{session_name}')


async def main():
    tasks = assign_tasks()
    for task in tasks:
        target = task.get('task')
        channel_link = target.get('channel_link')
        amount = target.get('amount')
        reason = target.get('reason')
        accs = task.get('accs')
        for acc in accs:
            if amount <= 0:
                print(f'Задание по репортам на канал {channel_link} выполнено успешно')
            session_name = acc[0]
            proxy = acc[1]
            if not os.path.exists(fr'sessions/{session_name}/tdata'):
                continue
            sess = SessionManager.from_tdata_folder(Path(fr"sessions/{session_name}/tdata"))
            try:
                api = API.TelegramDesktop.Generate(session_name)
            except ZeroDivisionError:
                api = API.TelegramDesktop.Generate()
            sess.api = api
            client = sess.pyrogram_client(proxy=proxy)
            try:
                await client.start()
            except ConnectionError:
                print(f'Не удалось подключиться к сессии {session_name}')
                continue
            if not (await client.get_me()):
                remove_session(session_name)
# 1)InputReportReasonChildAbuse - Report for child abuse.
# 2)InputReportReasonCopyright - Report for copyrighted content.
# 3)InputReportReasonFake - Report for impersonation.
# 4)InputReportReasonGeoIrrelevant - Report an irrelevant geogroup.
# 5)InputReportReasonIllegalDrugs - Report for illegal drugs.
# 6)InputReportReasonOther - Other.
# 7)InputReportReasonPersonalDetails - Report for divulgation of personal details.
# 8)InputReportReasonPornography - Report for pornography.
# 9)InputReportReasonSpam - Report for spam.
# 10)InputReportReasonViolence - Report for violence.
            report_reasons = {1: types.InputReportReasonChildAbuse,
                              2: types.InputReportReasonCopyright,
                              3: types.InputReportReasonFake,
                              4: types.InputReportReasonGeoIrrelevant,
                              5: types.InputReportReasonIllegalDrugs,
                              6: types.InputReportReasonOther,
                              7: types.SecureValueTypePersonalDetails,
                              8: types.InputReportReasonPornography,
                              9: types.InputReportReasonSpam,
                              10: types.InputReportReasonViolence}
            #здесь нужно саму отправку репортов делать
        if amount > 0:
            print(f'Для задания по репортам на канал {channel_link} не хватило аккаунтов.')
