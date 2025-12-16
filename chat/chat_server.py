# chat_server.py
import socket
from threading import Thread, Event
import sys
import re

# --- 맞춤법 검사기 모듈 로드 ---
try:
    from spell_checker_v2 import load_words, load_frequency_map, check_text, get_suggestions
    SPELL_CHECKER_LOADED = True
except ImportError:
    SPELL_CHECKER_LOADED = False
    print("[SERVER-ERROR] 'spell_checker_v2' 모듈을 찾을 수 없습니다. 맞춤법 검사 기능이 비활성화됩니다.")

# --- 서버 설정 ---
HOST = ''
PORT = 5001
ADDR = (HOST, PORT)
BUFSIZE = 1024

# --- 전역 변수 ---
event = Event()
client_sockets = {}  # { 'id': socket }
rooms = {}  # { 'room_name': {socket1, socket2, ...} }
word_set = None
freq_map = None

def parse_message(msg_str):
    """프로토콜 메시지 파싱: CMD param1 ... :trailing"""
    msg_str = msg_str.strip()
    if ' :' in msg_str:
        parts, trailing = msg_str.split(' :', 1)
    else:
        parts, trailing = msg_str, None
    tokens = parts.split()
    command = tokens[0].upper()
    params = tokens[1:]
    return command, params, trailing

def get_user_id(cs):
    """소켓 객체로 사용자 ID 찾기"""
    for user_id, sock in client_sockets.items():
        if sock == cs:
            return user_id
    return None

def broadcast(message, sender_socket=None):
    """모든 클라이언트에게 메시지 전송 (특정 소켓 제외 가능)"""
    for sock in client_sockets.values():
        if sock != sender_socket:
            try:
                sock.send(message.encode())
            except Exception as e:
                print(f"[SYSTEM] 브로드캐스트 오류: {e}")

def update_user_list():
    """모든 클라이언트에게 현재 사용자 목록 브로드캐스트"""
    user_list = ",".join(client_sockets.keys())
    broadcast(f"USER_LIST :{user_list}\n")

def run_spell_check_on_server(text):
    """서버에서 맞춤법 검사를 실행하고, 수정 제안 메시지를 반환합니다."""
    if not SPELL_CHECKER_LOADED or not word_set or not freq_map:
        return text # 검사기 비활성화 시 원문 반환

    # re.sub와 콜백 함수를 사용하여 한 번에 모든 단어를 검사하고 수정합니다.
    def replace_word(match):
        original_word = match.group(0)
        # 단어의 소문자 버전이 사전에 있는지 확인합니다.
        if original_word.lower() in word_set:
            return original_word # 올바른 단어이므로 그대로 반환합니다.

        # 철자가 틀린 단어이므로, 제안을 받습니다.
        suggestions = get_suggestions(original_word.lower(), word_set, freq_map, limit=1)
        if not suggestions:
            return original_word # 제안이 없으면 그대로 반환합니다.

        suggestion = suggestions[0]

        # 원래 대소문자를 보존합니다.
        if original_word.isupper():
            return suggestion.upper()
        if original_word.istitle():
            return suggestion.title()
        
        # 일반적인 단어는 소문자로 반환합니다.
        return suggestion.lower()

    # 정규식을 사용하여 텍스트의 모든 단어에 대해 replace_word 콜백을 실행합니다.
    return re.sub(r'[a-zA-Z]+', replace_word, text)

# --- Command Handlers ---

def handle_login(cs, params):
    user_id = params[0]
    if user_id in client_sockets or not user_id:
        cs.send("LOGIN_FAIL :이미 사용 중이거나 잘못된 ID입니다.\n".encode())
        return False
    
    client_sockets[user_id] = cs
    print(f"[SYSTEM] 로그인: {user_id}님이 접속했습니다.")
    cs.send("LOGIN_SUCCESS :서버에 성공적으로 접속했습니다.\n".encode())
    update_user_list()
    return True

def handle_spell_check(cs, trailing):
    corrected_text = run_spell_check_on_server(trailing)
    cs.send(f"SPELL_RESULT :{corrected_text}\n".encode())

def handle_quiz(cs, trailing):
    sender_id = get_user_id(cs)
    broadcast(f"MSG_RECV 퀴즈-{sender_id} :{trailing}\n", sender_socket=cs)

def handle_quiz_answer(cs, trailing):
    sender_id = get_user_id(cs)
    broadcast(f"MSG_RECV 퀴즈정답-{sender_id} :{trailing}\n", sender_socket=cs)

def handle_private_message(cs, params, trailing):
    sender_id = get_user_id(cs)
    target_id = params[0]
    target_socket = client_sockets.get(target_id)
    if target_socket:
        try:
            target_socket.send(f"MSG_RECV 1:1-{sender_id} :{trailing}\n".encode())
        except Exception as e:
            print(f"[SYSTEM] 1:1 메시지 전송 실패: {e}")
    else:
        cs.send(f"MSG_RECV [SYSTEM] :{target_id}님을 찾을 수 없습니다.\n".encode())

def handle_join_room(cs, params):
    sender_id = get_user_id(cs)
    room_name = params[0]
    if room_name not in rooms:
        rooms[room_name] = set()
    rooms[room_name].add(cs)
    
    # 방에 있는 다른 사람들에게 입장 알림
    for client_socket in rooms[room_name]:
        if client_socket != cs:
            try:
                client_socket.send(f"ROOM_MSG_RECV {room_name} [SYSTEM] :{sender_id}님이 입장했습니다.\n".encode())
            except Exception as e:
                print(f"[SYSTEM] 채팅방 입장 알림 오류: {e}")

    cs.send(f"JOIN_SUCCESS {room_name} :' {room_name}' 채팅방에 입장했습니다.\n".encode())

def handle_leave_room(cs, params):
    sender_id = get_user_id(cs)
    room_name = params[0]
    if room_name in rooms and cs in rooms[room_name]:
        rooms[room_name].remove(cs)
        # 방에 남아있는 사람들에게 퇴장 알림
        for client_socket in rooms[room_name]:
            try:
                client_socket.send(f"ROOM_MSG_RECV {room_name} [SYSTEM] :{sender_id}님이 퇴장했습니다.\n".encode())
            except Exception as e:
                print(f"[SYSTEM] 채팅방 퇴장 알림 오류: {e}")

def handle_room_message(cs, params, trailing):
    sender_id = get_user_id(cs)
    room_name = params[0]
    if room_name in rooms and cs in rooms[room_name]:
        for client_socket in rooms[room_name]:
            if client_socket != cs:
                try:
                    client_socket.send(f"ROOM_MSG_RECV {room_name} {sender_id} :{trailing}\n".encode())
                except Exception as e:
                    print(f"[SYSTEM] 채팅방 메시지 전송 오류: {e}")

# --- Main Communication Logic ---

def handle_message(cs, msg):
    """클라이언트로부터 받은 메시지를 처리"""
    command, params, trailing = parse_message(msg)
    
    if command == 'LOGIN':
        return handle_login(cs, params)

    # --- 로그인 이후 명령어 ---
    sender_id = get_user_id(cs)
    if not sender_id:
        print("[SYSTEM] 비로그인 사용자로부터 메시지 수신, 무시함")
        return False
        
    print(f"[RECV] {sender_id}: {msg.strip()}")

    if command == 'SPELL_CHECK':
        handle_spell_check(cs, trailing)
    elif command == 'QUIZ':
        handle_quiz(cs, trailing)
    elif command == 'QUIZ_ANSWER':
        handle_quiz_answer(cs, trailing)
    elif command == 'P_MSG':
        handle_private_message(cs, params, trailing)
    elif command == 'JOIN_ROOM':
        handle_join_room(cs, params)
    elif command == 'LEAVE_ROOM':
        handle_leave_room(cs, params)
    elif command == 'ROOM_MSG':
        handle_room_message(cs, params, trailing)
    elif command == 'QUIT':
        return False
    
    return True

def client_communication_thread(cs, addr):
    """개별 클라이언트와의 통신을 처리하는 스레드"""
    print(f"[SYSTEM] 연결 수락: {addr} 에서 새로운 클라이언트가 연결되었습니다.")
    
    is_running = True
    try:
        while is_running and not event.is_set():
            msg = cs.recv(BUFSIZE).decode()
            if not msg:
                break
            for line in msg.strip().split('\n'):
                if line:
                    is_running = handle_message(cs, line)
                    if not is_running:
                        break
    except Exception:
        pass # 클라이언트 강제 종료 등
    
    # --- 스레드 종료 처리 ---
    disconnected_user = get_user_id(cs)
    if disconnected_user:
        print(f"[SYSTEM] 연결 종료: {disconnected_user} ({addr})")
        
        # 모든 채팅방에서 해당 유저 제거
        for room in rooms.values():
            room.discard(cs)

        del client_sockets[disconnected_user]
        update_user_list()

    cs.close()

def accept_thread(server_socket):
    """새로운 클라이언트의 연결을 수락하는 스레드"""
    while not event.is_set():
        try:
            client_socket, addr_info = server_socket.accept()
            thread = Thread(target=client_communication_thread, args=(client_socket, addr_info))
            thread.daemon = True
            thread.start()
        except Exception:
            break
    print("[SYSTEM] Accept thread 종료.")

def main():
    global word_set, freq_map
    # --- 맞춤법 검사기 초기화 ---
    if SPELL_CHECKER_LOADED:
        print("[SYSTEM] 맞춤법 검사 사전을 로드하는 중...")
        # chat/ 디렉토리 기준으로 경로 설정
        word_set = load_words('spell_checker/words.txt')
        freq_map = load_frequency_map('spell_checker/en_full.txt')
        if not word_set or not freq_map:
            print("[SYSTEM] 경고: 사전 파일 로드에 실패했습니다. 맞춤법 검사 기능이 비활성화됩니다.")
        else:
            print("[SYSTEM] 맞춤법 검사기 로드 완료.")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(ADDR)
    server_socket.listen(10)
    print(f"[SYSTEM] 서버가 {PORT} 포트에서 시작되었습니다.")

    accept_th = Thread(target=accept_thread, args=(server_socket,))
    accept_th.daemon = True
    accept_th.start()

    print("[SYSTEM] 서버를 종료하려면 'q'를 입력하세요.")
    try:
        while True:
            cmd = input()
            if cmd.lower() == 'q':
                break
    except (KeyboardInterrupt, EOFError):
        pass

    print("[SYSTEM] 서버를 종료합니다...")
    event.set()
    
    for sock in client_sockets.values():
        sock.close()
    
    server_socket.close()
    print("[SYSTEM] 서버가 종료되었습니다.")

if __name__ == "__main__":
    main()