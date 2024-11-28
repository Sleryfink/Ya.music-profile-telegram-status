import requests
import time
import telethon
from telethon.sync import TelegramClient

import asyncio
import aiohttp
import aiofiles
from telethon import functions, types
from telethon.tl.functions.photos import DeletePhotosRequest
from telethon.tl.functions.channels import DeleteMessagesRequest
from telethon.tl.types import InputPeerChannel
from telethon.errors import FloodWaitError

# сюда вся инфа ##
api_id = ''
api_hash = ''
music_token = ''
stock_tgk = ''
new_tgk = ''
###################

client_tele = TelegramClient('my_account', api_id, api_hash)

default = ''
count = 0
wave = False

# код обновляет канал
async def update_personal_channel(channel_id):
    async with client_tele as client:
        # Получение информации о канале
        channel = await client.get_entity(channel_id)

        # Проверка, стоит ли уже stock_tgk
        if channel.title == stock_tgk:
            print(f"Канал {stock_tgk} уже установлен. Повторное обновление не требуется.")
            return  # Выходим, если уже установлен

        # Обновление личного канала
        result = await client(functions.account.UpdatePersonalChannelRequest(
            channel=types.InputChannel(channel.id, channel.access_hash)
        ))
        print(f"Личный канал обновлён на {channel_id}:", result)

# function для обновления cover/title/mesage
async def TelegramUpdatState(new_tgk, title, artists, img_uri):
    async with client_tele as client:
        # 0 Часть: Скачивание изображения асинхронно
        async with aiohttp.ClientSession() as session:
            async with session.get(img_uri) as response:
                if response.status == 200:
                    async with aiofiles.open("cover.jpeg", 'wb') as file:
                        await file.write(await response.read())
                    print(f'\nобложка скачано')
                else:
                    print('Не удалось скачать обложку')

        # Часть 1: Удаление всех фотографий профиля канала
        photos = await client.get_profile_photos(new_tgk)
        await client(DeletePhotosRequest(photos))
        print(f'Удалено {len(photos)} фотографий профиля канала {new_tgk}')

        # Часть 2: Замена фотографии профиля канала
        result = await client(functions.channels.EditPhotoRequest(
            channel=new_tgk,
            photo=await client.upload_file('cover.jpeg')
        ))
        print('Фотография профиля канала обновлена.')

        # Часть 3: Изменение заголовка канала
        channel = await client.get_entity(new_tgk)

            # Проверяем текущий заголовок
        if channel.title != title:
            await client(functions.channels.EditTitleRequest(new_tgk, title))
            print('Заголовок обновлён на:', title)
        else:
            print("Заголовок не изменился, запрос не отправляется.")

        # Часть 4: Удаление всех сообщений из канала
        channel = await client.get_input_entity(new_tgk)
        messages = await client.get_messages(channel, limit=None)
        message_ids = [msg.id for msg in messages]
        await client(DeleteMessagesRequest(channel, message_ids))
        print(f'Удалено {len(message_ids)} сообщений.')

        # Часть 5: Отправка сообщения в канал
        txt = f"Now listening: {title} - {artists}"
        await client.send_message(new_tgk, txt)
        await client.send_message(new_tgk, artists)
        print('Сообщение отправлено.')

# main Часть скрипта (я.музыка и установка личного канала)
async def main():
    global default, count, wave
    try:
        wave = False
        track_info = get_current_track()

        if not track_info:
            print("Нет информации о текущем треке.")
            await update_personal_channel(stock_tgk)
            return

        title = track_info['title']
        artists = track_info['artist']
        img_uri = track_info['img']

        if default != title:
            default = title
            try:
                await TelegramUpdatState(new_tgk, title, artists, img_uri)
                await update_personal_channel(new_tgk)
            except FloodWaitError as e:
                print(f"Превышен лимит запросов Telegram. Ждем {e.seconds} секунд.")
                await update_personal_channel(stock_tgk)
                await asyncio.sleep(e.seconds)
                return await TelegramUpdatState(new_tgk, title, artists, img_uri)
        else:
            if count < 5:
                count += 1
            else:
                count = 0
                await update_personal_channel(stock_tgk)
    except (IndexError, errors.AboutTooLongError):
        stock_bio = ''
        if wave:
            pass
        else:
            wave = True
            await client_tele(functions.account.UpdateProfileRequest(
                about=f"{stock_bio}"
            ))


def get_current_track():
    url = f"https://api.mipoh.ru/get_current_track_beta?ya_token={music_token}"
    headers = {'accept': 'application/json'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Проверка на ошибки
        data = response.json()

        track_info = {
            'title': data['track']['title'],
            'artist': data['track']['artist'],
            'img': data['track']['img']
        }
        return track_info

    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None



# чекер соединения
def check_internet():
    url = 'http://www.ya.ru/'
    timeout = 30
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        print('Нет подключения к интернету. Ожидание восстановления подключения...')
        return False

class NetworkError(Exception):
    pass

# В основном цикле:
async def main_loop():
    while True:
        if check_internet():
            try:
                await main()
            except NetworkError:
                print('Произошла ошибка сети. Перезапуск через 30 секунд...')
                await asyncio.sleep(30)
                continue
        await asyncio.sleep(100)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_loop())
