import logging
import os
import time
from dotenv import load_dotenv
from steam.client import SteamClient
from dota2.client import Dota2Client
from dota2.enums import DOTA_GameMode

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Загрузка переменных окружения ---
load_dotenv("data.env")
STEAM_USERNAME = os.getenv("STEAM_USERNAME")
STEAM_PASSWORD = os.getenv("STEAM_PASSWORD")

if not STEAM_USERNAME or not STEAM_PASSWORD:
    logger.error("Отсутствуют данные для входа в Steam. Проверьте файл .env.")
    exit(1)

# --- Инициализация клиента Steam и Dota 2 ---
steam_client = SteamClient()
dota = Dota2Client(steam_client)

# --- Конфигурация ---
PLAYERS_TO_INVITE = [
    {"id": """steam64id""" , "team": 1},  # 1 - BAD GUYS, STEAM64ids our players and teams
]

LOBBY_NAME = "My Custom Lobby"
LOBBY_REGION = 3  # Регион сервера (3 - Европа)
LOBBY_PASSWORD = ""
LOBBY_GAME_MODE = DOTA_GameMode.DOTA_GAMEMODE_AP
DOTA_GC_TEAM_GOOD_GUYS = 0
DOTA_GC_TEAM_BAD_GUYS = 1
DOTA_GC_TEAM_PLAYER_POOL = 4

lobby_state = None
game_started = False

# --- События ---
@steam_client.on('logged_on')
def start_dota():
    logger.info("Вход в Steam выполнен. Запускаем Dota 2...")
    dota.launch()

@dota.on('ready')
def create_lobby():
    logger.info("Dota 2 готова. Создание лобби...")
    lobby_details = {
        "game_name": LOBBY_NAME,
        "server_region": LOBBY_REGION,
        "game_mode": LOBBY_GAME_MODE,
        "pass_key": LOBBY_PASSWORD
    }
    dota.create_practice_lobby(password=LOBBY_PASSWORD, options=lobby_details)

@dota.on(dota.EVENT_LOBBY_NEW)
def lobby_new_handler(lobby):
    global lobby_state
    global game_started
    lobby_state = lobby
    game_started = False
    logger.info("Лобби создано: %s", lobby)
    for player in PLAYERS_TO_INVITE:
        dota.invite_to_lobby(player["id"])
    dota.channels.join_lobby_channel()

@dota.channels.on('channel_joined')
def channel_joined_handler(channel):
    global chat_channel
    chat_channel = channel
    logger.info("Присоединились к каналу лобби.")
    dota.join_practice_lobby_team(4)   # бот прыгает в неопределившихся

@dota.on(dota.EVENT_LOBBY_CHANGED)
def lobby_changed_handler(lobby):
    global lobby_state
    global game_started
    lobby_state = lobby
    logger.info("Обновлено состояние лобби: %s", lobby)

    if all_players_in_teams(lobby_state, PLAYERS_TO_INVITE) and not game_started:
        for i in range(5, 0, -1):
            message = f"Игра начнётся через {i} секунд"
            logger.info(message)
            if chat_channel:
                chat_channel.send(message)
            time.sleep(1)
        logger.info("Запуск игры...")
        dota.launch_practice_lobby()
        game_started = True
    else:
        logger.info("Ожидание заполнения слотов игроков...")
        time.sleep(5)

def all_players_in_teams(lobby, players_to_invite):
    logger.info("Проверка состояния игроков в лобби...")

    all_members = lobby.all_members
    if not all_members:
        logger.error("Список участников лобби пуст или недоступен.")
        return False

    for member in all_members:
        logger.info(f"Участник лобби: ID={member.id}, команда={member.team}")

    for player in players_to_invite:
        matching_member = next((member for member in all_members if member.id == player["id"]), None)
        if matching_member:
            logger.debug(f"Проверяем игрока: ID={matching_member.id}, команда={matching_member.team}, ожидалось команда={player['team']}")
            if matching_member.team != player["team"]:
                logger.info(f"Игрок {player['id']} в неправильной команде: {matching_member.team} (ожидалось {player['team']}).")
                return False
        else:
            logger.info(f"Игрок {player['id']} отсутствует в лобби.")
            return False

    logger.info("Все игроки находятся в нужных командах.")
    return True

@dota.on(dota.EVENT_LOBBY_CHANGED)
def kick_unknow_players(lobby):
    for player in lobby.v2_members:
        if player.id not in [p["id"] for p in PLAYERS_TO_INVITE]:
            logger.info(f"Кикаем игрока {player.id} из лобби")
            dota.practice_lobby_kick(player.id)

@dota.on('lobby_member_joined')
def member_joined_handler(member):
    logger.info("Участник присоединился к лобби. Обновление состояния лобби...")

@dota.on('error')
def error_handler(error):
    logger.error("Произошла ошибка: %s", error)

# --- Запуск ---
def main():
    try:
        steam_client.cli_login(username=STEAM_USERNAME, password=STEAM_PASSWORD)
        steam_client.run_forever()
    except Exception as e:
        logger.error("Ошибка при запуске: %s", e)

if __name__ == "__main__":
    main()
