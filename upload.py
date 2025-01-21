import ftplib
import os
import logging
import json
import socket
from tqdm import tqdm  # Импортируем tqdm для progress bar

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_logging():
    """
    Настройка логирования: вывод в консоль и запись в файл.
    """
    # Создаем логгер
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Формат сообщений
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Обработчик для записи в файл (с указанием кодировки utf-8)
    file_handler = logging.FileHandler('upload.log', mode='a', encoding='utf-8')  # Указываем кодировку
    file_handler.setFormatter(formatter)

    # Добавляем обработчики к логгеру
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logging()
def upload_file(ftp, filepath, remote_folder):
    """
    Отправляет файл на FTP сервер

    :param ftp:    экземпляр ftplib.FTP, уже подключенный к серверу
    :param filepath:    путь к файлу, который нужно отправить
    :param remote_folder:    путь к папке на сервере, куда отправлять файл
    """
    filesize = os.path.getsize(filepath)

    try:
        ftp.cwd(remote_folder)  # Переход в удаленную папку
    except ftplib.error_perm as e:
        logger.error(f"Ошибка при переходе в папку {remote_folder}: {e}")
        return

    try:
        with open(filepath, 'rb') as file:
            # Используем tqdm для отображения progress bar
            with tqdm(total=filesize, unit='B', unit_scale=True, desc=os.path.basename(filepath)) as pbar:
                def upload_callback(data):
                    """
                    Callback функция для ftplib.FTP.storbinary. Обновляет progress bar.
                    """
                    pbar.update(len(data))

                ftp.storbinary(f'STOR {os.path.basename(filepath)}', file, 1024, upload_callback)
        
        logger.info(f"Файл {filepath} успешно загружен.")
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {filepath}: {e}")

def read_config():
    """
    Чтение параметров подключения из конфигурационного файла
    :return: словарь с параметрами, None в случае ошибки
    """
    try:
        with open('config.json', 'r', encoding='utf-8') as file:  # Указываем кодировку при чтении файла
            config = json.load(file)
            required_keys = ['host', 'user', 'password', 'remote_folder', 'firmware_file', 'storage_file']
            if not all(key in config for key in required_keys):
                logger.error("Ошибка: Конфигурационный файл не содержит всех необходимых ключей.")
                return None
            return config
    except Exception as ex:
        logger.error(f"Ошибка при чтении конфигурационного файла: {ex}")
        return None

def is_server_reachable(host, port=21, timeout=5):
    """
    Проверка доступности FTP-сервера
    """
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except socket.error:
        return False

def main():
    """
    Главная функция программы. Она читает параметры FTP-сервера из
    конфигурационного файла, отправляет файлы firmware и storage на
    сервер, и выводит прогресс загрузки в виде progress bar.
    """
    config = read_config()
    if not config:
        logger.error("Ошибка: Не удалось загрузить конфигурацию из config.json.")
        return
    
    ftp_host = config['host']
    ftp_user = config['user']
    ftp_pass = config['password']
    remote_folder = config['remote_folder']
    firmware_file = config['firmware_file']
    storage_file = config['storage_file']

    # Проверка существования и доступности файлов
    if not os.path.isfile(firmware_file) or not os.access(firmware_file, os.R_OK):
        logger.error(f"Ошибка: firmware файл {firmware_file} не найден или недоступен.")
        return
    
    if not os.path.isfile(storage_file) or not os.access(storage_file, os.R_OK):
        logger.error(f"Ошибка: storage файл {storage_file} не найден или недоступен.")
        return

    # Проверка доступности FTP-сервера
    if not is_server_reachable(ftp_host):
        logger.error(f"Ошибка: FTP-сервер {ftp_host} недоступен.")
        return

    ftp = None

    # Подключение к FTP-серверу
    try:
        ftp = ftplib.FTP(ftp_host, timeout=10)
        ftp.login(ftp_user, ftp_pass)
        logger.info(f"Соединение c {ftp_host} успешно установлено.")

        upload_file(ftp, firmware_file, remote_folder)
        upload_file(ftp, storage_file, remote_folder)

    except ftplib.all_errors as e:
        logger.error(f"Ошибка при подключении к FTP-серверу: {e}")
    finally:
        if ftp:
            ftp.quit()

if __name__ == "__main__":
    main()