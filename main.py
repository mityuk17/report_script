import asyncio
import os
from pathlib import Path

import pyrogram.raw.functions.account
import requests
import pyrogram.errors.exceptions as pyro_exceptions
from pyrogram.raw import types
import openpyxl
from opentele.api import API , CreateNewSession , UseCurrentSession
from TGConvertor.manager.manager import SessionManager
from pyrogram.raw.functions.account import ReportPeer


def get_sessions():
    if not os.path.exists('sessions'):
        return False
    with os.scandir('sessions') as files:
        subdir = [file.name for file in files if file.is_dir() and os.path.exists(f'sessions/{file.name}/tdata')]
    print('Собрано сессий:' , len(subdir))
    return subdir


def get_proxies():
    with open('proxies.txt' , 'r') as file:
        data = file.readlines()
    for i in range(len(data)):
        data[ i ] = data[ i ].strip().split(':')
        data[ i ] = {
            'scheme': 'socks5' ,
            'hostname': data[ i ][ 0 ] ,
            'port': int(data[ i ][ 1 ]) ,
            'username': data[ i ][ 2 ] ,
            'password': data[ i ][ 3 ]
        }
    while True:
        ans = input('Проводить проверку прокси на валидность?(y/n)')
        if ans == 'y':
            flag = True
            break
        elif ans == 'n':
            flag = False
            break
        print('Введите y или n')
    for i in data:
        if not check_proxy(i):
            print(f'Прокси {i.get("hostname")} не валидный')
            data.remove(i)

    return data


def connect_proxies_to_accs():
    tdatas = get_sessions()
    proxies = get_proxies()
    accs = list()
    cur_pos = 0
    for i in tdatas:
        if cur_pos >= len(proxies):
            cur_pos = 0
        accs.append([ i , proxies[ cur_pos ] ])
        cur_pos += 1
    return accs


def get_tasks():
    tasks = list()
    wb = openpyxl.load_workbook('tasks.xlsx')
    sh = wb.active
    # Структура таблицы: ссылка на канал | кол-во репортов | причина репортов
    for row in sh.values:
        task = {'channel_link': row[ 0 ] , 'amount': int(row[ 1 ]) , 'reason': int(row[ 2 ])}
        tasks.append(task)
    return tasks


def assign_tasks():
    accs = connect_proxies_to_accs()
    tasks = get_tasks()
    for i in range(len(tasks)):
        if len(accs) < tasks[ i ][ 'amount' ]:
            print(f'Для задания {i + 1} не хватает аккаунтов, будет отправлено {len(tasks)} репортов')
        tasks[ i ] = {'task': tasks[ i ] , 'accs': accs}
    return tasks


def remove_session(session_name):
    os.replace(fr'sessions/{session_name}' , fr'banned_sessions/{session_name}')


def check_proxy(proxy: dict):
    scheme = proxy.get('scheme')
    host = proxy.get('hostname')
    port = proxy.get('port')
    username = proxy.get('username')
    password = proxy.get('password')
    proxy_f = f'{scheme}://{username}:{password}@{host}:{port}'
    proxies = {
        'http': proxy_f ,
        'https': proxy_f
    }
    original_ip = requests.get('https://api.ipify.org').text
    try:
        masked_ip = requests.get('https://api.ipify.org' , proxies=proxies).text
    except requests.exceptions.ConnectionError:
        return False
    return masked_ip and original_ip != masked_ip


async def main():
    tasks = assign_tasks()
    for task in tasks:
        target = task.get('task')
        channel_link = target.get('channel_link')
        amount = target.get('amount')
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
        report_reasons = {1: types.InputReportReasonChildAbuse() ,
                          2: types.InputReportReasonCopyright() ,
                          3: types.InputReportReasonFake() ,
                          4: types.InputReportReasonGeoIrrelevant() ,
                          5: types.InputReportReasonIllegalDrugs() ,
                          6: types.InputReportReasonOther() ,
                          7: types.SecureValueTypePersonalDetails() ,
                          8: types.InputReportReasonPornography() ,
                          9: types.InputReportReasonSpam() ,
                          10: types.InputReportReasonViolence()}
        reason = target.get('reason')
        reason = report_reasons.get(reason)
        accs = task.get('accs')
        for acc in accs:
            if amount <= 0:
                print(f'Задание по репортам на канал {channel_link} выполнено успешно')
                break
            session_name = acc[ 0 ]
            proxy = acc[ 1 ]
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
            except pyro_exceptions.Unauthorized:
                print(f'Сессия {session_name} не валидна')
                remove_session(session_name)
                continue
            if not (await client.get_me()):
                remove_session(session_name)
                continue
            print(f'Подключен аккаунт {session_name}')
            print(f'''Попытка отправить репорт на канал {channel_link} с аккаунта {session_name}''')
            peer = await client.resolve_peer(channel_link)
            peer_id = peer.channel_id
            access_hash = peer.access_hash
            channel = types.InputPeerChannel(channel_id=peer_id , access_hash=access_hash)

            if await client.invoke(ReportPeer(peer=channel , reason=reason , message='')):
                print(f'Репорт отправлен успешно.')
        if amount > 0:
            print(f'Для задания по репортам на канал {channel_link} не хватило аккаунтов.')


asyncio.run(main())
