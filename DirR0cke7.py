# Exibe o primeiro banner
print(''' ____  _      ____   ___       _       _____ 
|  _ \(_)_ __|  _ \ / _ \  ___| | ____|___  |
| | | | | '__| |_) | | | |/ __| |/ / _ \ / / 
| |_| | | |  |  _ <| |_| | (__|   <  __// /  
|____/|_|_|  |_| \_\\___/ \___|_|\_\___/_/   ''')

# Exibe o segundo banner
print('''                                                          
                                        ██████████████    
                                  ██████████        ██    
                              ████████              ██    
                          ██████                  ████    
                        ██████      ████          ██      
                      ████        ████████      ████      
                    ████        ████░░░░████    ████      
          ████████████          ████░░░░████  ████        
        ████    ▒▒██              ████████    ████        
        ██    ▒▒██                  ████    ████          
      ████  ▒▒██          ████            ████            
      ██▒▒  ▒▒██        ████▒▒██          ████            
    ████▒▒▒▒██        ████▒▒██▒▒        ████              
    ████████████    ████▒▒██▒▒        ████                
            ░░    ████▒▒██▒▒        ████                  
      ░░░░        ██▒▒██▒▒        ████                    
    ▒▒▒▒░░        ▒▒██▒▒        ██▒▒██                    
  ░░▒▒▒▒▒▒░░                ████  ▒▒██                    
        ▒▒░░          ░░████▒▒    ▒▒██                    
      ▒▒▒▒▒▒░░    ░░  ▒▒██▒▒      ▒▒██                    
    ▒▒▒▒▒▒▒▒░░░░▒▒░░  ▒▒██▒▒▒▒██████                      
  ░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░▒▒████████                          
  ▒▒      ▒▒▒▒▒▒░░▒▒░░  ████                              
        ▒▒▒▒▒▒  ▒▒▒▒                                      
        ▒▒░░    ▒▒░░
''')
import threading
import subprocess
import requests
import readline
import os
from pathlib import Path
from concurrent import futures
import signal

# Variável para controlar a execução das threads
running = True

# Função para interromper a execução das threads
def stop_execution():
    global running
    running = False

# Captura do sinal de interrupção (Ctrl + C)
signal.signal(signal.SIGINT, lambda sig, frame: stop_execution())

# Verifica se o Tor está instalado
try:
    subprocess.check_output(['tor', '--version'])
except FileNotFoundError:
    print("O Tor não está instalado. Instalando...")
    subprocess.run(['sudo', 'apt', 'install', 'tor', '-y'])
except PermissionError:
    print("Permissão negada para executar o comando 'tor'. Verifique suas permissões.")

# Faz as configurações necessárias
subprocess.run(['sudo', 'systemctl', 'start', 'tor'])
subprocess.run(['sudo', 'systemctl', 'enable', 'tor'])

# Solicita a URL alvo ao usuário
target_url = input("Digite a URL alvo: ")

# Solicita a quantidade de threads ao usuário
num_threads = int(input("Digite a quantidade de threads desejada: "))

# Solicita o caminho da Wordlist ao usuário
def complete_path(text, state):
    if '~' in text:
        text = os.path.expanduser(text)
    path = os.path.dirname(text)
    if not path:
        path = './'
    line_buffer = readline.get_line_buffer()
    line_buffer = os.path.expanduser(line_buffer)
    if '~' in line_buffer:
        line_buffer = os.path.expanduser(line_buffer)
    names = os.listdir(path)
    matches = [name for name in names if name.startswith(line_buffer)]
    return matches[state]

readline.set_completer(complete_path)
readline.parse_and_bind("tab: complete")

wordlist_path = Path(input("Digite o caminho da sua wordlist: "))

# Lê a Wordlist e combina com a URL fornecida
directories = []
with wordlist_path.open('r') as wordlist_file:
    for line in wordlist_file:
        directory = line.strip()
        full_url = target_url + '/' + directory
        directories.append(full_url)

# Solicita os intervalos de comprimento para ignorar
length_ranges = input("Digite os intervalos de comprimento para ignorar (exemplo: 6000-6999,80555,7000-7050): ").strip().split(',')

# Lista para armazenar as funções de verificação de intervalo
range_checks = []

# Função para verificar se o comprimento está dentro de qualquer intervalo especificado
def is_within_any_range(length):
    return any(check(length) for check in range_checks)

# Processa cada intervalo fornecido pelo usuário
for length_range in length_ranges:
    # Divide o intervalo em início e fim
    range_parts = length_range.strip().split('-')

    # Converte os valores para inteiros
    start = int(range_parts[0].strip())
    end = int(range_parts[-1].strip())

    # Cria uma função de verificação para o intervalo
    def is_within_range(length, start=start, end=end):
        return start <= length <= end

    # Adiciona a função de verificação à lista
    range_checks.append(is_within_range)

# Verifica se o comprimento está dentro de qualquer intervalo especificado
def is_within_ranges(length):
    return not is_within_any_range(length)

# Função para verificar um diretório
def check_directory(directory):
    try:
        response = requests.get(directory, timeout=1)
        if response.status_code in [200, 301, 302]:
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                content_length = len(response.content)
                if is_within_ranges(content_length):
                    with print_lock:
                        print("\n\033[92mDiretório encontrado:\033[0m", directory)
                        print("\033[93mLength:\033[0m", content_length)
    except (requests.RequestException, requests.Timeout):
        pass

# Função para dividir a lista de diretórios em partes iguais para cada thread
def divide_list(lst, n):
    avg = len(lst) // n
    out = []
    last = 0

    while last < len(lst):
        out.append(lst[last:last + avg])
        last += avg

    return out

# Função para processar cada parte da lista de diretórios em uma thread separada
def process_directory_part(directory_part):
    for directory in directory_part:
        with print_lock:
            if not running:
                return
            print("\r\033[91mVerificando:\033[0m", directory, end='', flush=True)
        check_directory(directory)
        if not running:
            return

# Divide a lista de diretórios em partes iguais para cada thread
directory_parts = divide_list(directories, num_threads)

# Cria uma lista para armazenar as threads
threads = []
print_lock = threading.Lock()

# Inicia e executa as threads para processar cada parte da lista de diretórios
with futures.ThreadPoolExecutor() as executor:
    for part in directory_parts:
        thread = executor.submit(process_directory_part, part)
        threads.append(thread)

# Aguarda todas as threads terminarem
try:
    for thread in threads:
        thread.result()
except KeyboardInterrupt:
    pass

print("\nVerificação concluída.")
