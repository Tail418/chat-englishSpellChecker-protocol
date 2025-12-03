# chat_client_irc_spell.py
import socket
from threading import Thread, Event
import sys
import re

# --- 맞춤법 검사기 모듈 로드 ---
# spell_checker 디렉토리를 sys.path에 추가하여 모듈을 임포트할 수 있도록 함
sys.path.append('spell_checker')
try:
    from spell_checker_v2 import load_words, load_frequency_map, check_text, get_suggestions
    SPELL_CHECKER_LOADED = True
except ImportError:
    SPELL_CHECKER_LOADED = False
    print("[SYSTEM] 경고: 'spell_checker_v2' 모듈을 찾을 수 없습니다. 맞춤법 검사 기능이 비활성화됩니다.")

# --- 클라이언트 설정 ---
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
BUFSIZE = 1024

# --- 전역 변수 ---
event = Event()
my_id = None

def parse_message(msg_str):
    """IRC 스타일 메시지를 파싱합니다."""
    msg_str = msg_str.strip()
    if ' :' in msg_str:
        parts, trailing = msg_str.split(' :', 1)
    else:
        parts, trailing = msg_str, None
    tokens = parts.split()
    command = tokens[0].upper()
    params = tokens[1:]
    return command, params, trailing

def listen_for_messages(sock):
    """서버로부터 오는 메시지를 수신하고 처리하는 스레드"""
    while not event.is_set():
        try:
            raw_msg = sock.recv(BUFSIZE).decode()
            if not raw_msg:
                break
            
            for msg in raw_msg.strip().split('\n'):
                if not msg:
                    continue

                command, params, trailing = parse_message(msg)

                if command == 'MSG_RECV':
                    sender = params[0]
                    content = trailing
                    if sender != my_id:
                        print(f"\r[{sender}] {content}\n> ", end="")

                elif command == 'USER_LIST':
                    users = trailing.split(',')
                    print(f"\r[SYSTEM] 현재 접속자: {', '.join(users)}\n> ", end="")
                
                elif command == 'LOGIN_SUCCESS':
                    print(f"\r[SYSTEM] {trailing}\n> ", end="")

                elif command == 'LOGIN_FAIL':
                    print(f"\r[SYSTEM] {trailing}")
                    event.set()
                    break
                
                else:
                    print(f"\r[SERVER] {msg}\n> ", end="")

        except Exception:
            break
    
    print("\r서버와의 연결이 끊어졌습니다. Enter를 눌러 종료하세요.")
    event.set()

def run_spell_check(text, word_set, freq_map):
    """맞춤법 검사를 실행하고, 수정 제안 메시지를 반환합니다."""
    # 영어 단어만 추출하여 검사
    words_to_check = re.findall(r'\b[a-zA-Z]+\b', text)
    
    # 텍스트 전체를 소문자로 변환하여 오타 찾기
    misspelled = check_text(' '.join(words_to_check), word_set)
    
    if not misspelled:
        return None, None

    corrections = {}
    for word in misspelled:
        suggestions = get_suggestions(word, word_set, freq_map, limit=1)
        if suggestions:
            corrections[word] = suggestions[0]

    if not corrections:
        return None, None
        
    # 원본 텍스트에서 오타를 추천 단어로 변경
    corrected_text = text
    # 원본 단어의 대소문자 형태를 유지하기 위한 로직
    for bad_word, good_word in corrections.items():
        # 정규표현식을 사용하여 단어 경계를 명확히 하고, 대소문자를 구분하지 않도록 함
        pattern = r'\b' + re.escape(bad_word) + r'\b'
        
        # 원본 텍스트에서 해당 단어를 찾아 대소문자 형태를 파악
        found_word = re.search(pattern, corrected_text, re.IGNORECASE)
        if found_word:
            original_casing = found_word.group(0)
            # good_word를 원본 단어의 대소문자 형태에 맞게 변환
            if original_casing.isupper():
                suggestion = good_word.upper()
            elif original_casing.istitle():
                suggestion = good_word.title()
            else:
                suggestion = good_word.lower() # 기본은 소문자
            
            # 첫 번째 발견된 오타만 수정
            corrected_text = re.sub(pattern, suggestion, corrected_text, count=1, flags=re.IGNORECASE)

    return corrected_text, corrections


def main():
    """메인 함수"""
    global my_id
    
    # --- 맞춤법 검사기 초기화 ---
    word_set, freq_map = None, None
    if SPELL_CHECKER_LOADED:
        print("[SYSTEM] 맞춤법 검사 사전을 로드하는 중...")
        word_set = load_words('spell_checker/words.txt')
        freq_map = load_frequency_map('spell_checker/en_full.txt')
        if not word_set or not freq_map:
            print("[SYSTEM] 경고: 사전 파일 로드에 실패했습니다. 맞춤법 검사 기능이 비활성화됩니다.")
            word_set, freq_map = None, None
        else:
            print("[SYSTEM] 맞춤법 검사기 로드 완료.")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((SERVER_HOST, SERVER_PORT))
        print(f"{SERVER_HOST}:{SERVER_PORT} 서버에 연결되었습니다.")
    except Exception as e:
        print(f"서버 연결 실패: {e}")
        sys.exit()

    while not my_id:
        my_id = input("사용할 아이디를 입력하세요: ").strip()
        if not my_id or ' ' in my_id or ':' in my_id or ',' in my_id:
            print("아이디는 공백, ':', ',' 문자를 포함할 수 없습니다.")
            my_id = None

    s.send(f"LOGIN {my_id}\n".encode())

    listener_thread = Thread(target=listen_for_messages, args=(s,))
    listener_thread.daemon = True
    listener_thread.start()

    print("\n채팅 시작! 메시지를 입력하세요. 종료하려면 '/quit'을 입력하세요.")
    
    try:
        while not event.is_set():
            print("> ", end="")
            original_msg = input()
            
            if event.is_set():
                break

            if original_msg.lower() == '/quit':
                s.send(f"QUIT {my_id} :Leaving\n".encode())
                break
            
            if not original_msg:
                continue

            msg_to_send = original_msg
            
            # --- 맞춤법 검사 로직 ---
            if word_set and freq_map:
                corrected_msg, corrections = run_spell_check(original_msg, word_set, freq_map)
                
                if corrected_msg:
                    print("-" * 20)
                    print(f"오타가 발견되었습니다:")
                    for bad, good in corrections.items():
                        print(f" - {bad} -> {good}")
                    
                    print(f"\n제안: \"{corrected_msg}\"")
                    
                    while True:
                        choice = input("수정된 메시지를 보내시겠습니까? ([Y]es/[N]o/[E]dit) ").lower()
                        if choice in ['y', 'yes']:
                            msg_to_send = corrected_msg
                            break
                        elif choice in ['n', 'no']:
                            msg_to_send = original_msg
                            break
                        elif choice in ['e', 'edit']:
                            msg_to_send = None # 루프를 다시 시작하여 재입력 받음
                            break
                        else:
                            print("잘못된 입력입니다. Y, N, E 중 하나를 입력하세요.")
                    print("-" * 20)
                    
                    if msg_to_send is None:
                        continue # 'edit' 선택 시 메시지 재입력

            # 브로드캐스트 메시지 전송
            s.send(f"MSG_ALL {my_id} :{msg_to_send}\n".encode())

    except (KeyboardInterrupt, EOFError):
        s.send(f"QUIT {my_id} :Leaving by force\n".encode())
    
    finally:
        print("\n프로그램을 종료합니다...")
        event.set()
        s.close()

if __name__ == "__main__":
    main()
