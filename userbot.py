import requests
import time
import telethon
from telethon.sync import TelegramClient
from yandex_music import Client
from yandex_music.exceptions import NetworkError
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
stock_tgk = 't.me/'
new_tgk = 't.me/'
###################

client_tele = TelegramClient('my_account', api_id, api_hash)
client_music = Client(music_token).init()

default = ''
count = 0
wave = False

# код обновляет канал
async def update_personal_channel(channel_id):
    async with client_tele as client:
        # Получение информации о канале
        channel = await client.get_entity(channel_id)

        # Обновление личного канала
        result = await client(functions.account.UpdatePersonalChannelRequest(
            channel=types.InputChannel(channel.id, channel.access_hash)
        ))
        print(f"Личный канал обновлён на {channel_id}:", result )

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
        queues = client_music.queues_list()
        try:
            last_queue = client_music.queue(queues[0].id)
        except TypeError:
            print("Ошибка при получении очереди, это нормально для моей волны")
            await update_personal_channel(stock_tgk)
            return
        last_track_id = last_queue.get_current_track()
        last_track = last_track_id.fetch_track()
        artists = ', '.join(last_track.artists_name())
        title = last_track.title
        # 👇 И ЗА ЭТОЙ ГРЕБАНОЙ СТРОКИ Я ПРО#РАЛ 2 ЧАСА
        img_uri = f"https://{last_track.cover_uri[:-2]}1000x1000"
        if default != title:
            default = title
            try:
                await TelegramUpdatState(new_tgk, title, artists, img_uri)
                await update_personal_channel(new_tgk)
            except FloodWaitError as e:
                print(f"Превышен лимит запросов Telegram. Ждем {e.seconds} секунд.")
                await update_personal_channel(stock_tgk)
                await asyncio.sleep(e.seconds) # Ждем указанное время
                return await TelegramUpdatState(new_tgk, title, artists, img_uri)
            # print(img_uri)
        else:
            if count < 5:
                count += 1
            else:
                count = 0
                await update_personal_channel(stock_tgk)
    # если я вот это снизу удалю то тогда код не будет работать
    # кто может помочь, сделайте фикс и comit ;)
    except (IndexError, errors.AboutTooLongError):
        stock_bio = ''
        if wave:
            pass
        else:
            wave = True
            await client_tele(functions.account.UpdateProfileRequest(
                about=f"{stock_bio}"
            ))


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
        await asyncio.sleep(80)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_loop())
