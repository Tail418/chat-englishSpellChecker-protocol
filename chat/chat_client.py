# chat_client.py
import socket
from threading import Thread, Event
import sys

# --- 클라이언트 설정 ---
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
BUFSIZE = 1024

# --- 전역 변수 ---
event = Event()
my_id = None
current_mode = 'main'  # 'main' or 'room'
current_room = ''

def clear_line():
    """현재 줄을 지웁니다."""
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    sys.stdout.flush()

def show_prompt():
    """현재 모드에 맞는 프롬프트를 표시합니다."""
    if current_mode == 'room':
        prompt = f"({current_room}) > "
    else:
        prompt = "> "
    sys.stdout.write(prompt)
    sys.stdout.flush()

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
                clear_line()

                if command == 'MSG_RECV':
                    sender = params[0]
                    content = trailing
                    print(f"[{sender}] {content}")
                
                elif command == 'ROOM_MSG_RECV':
                    room_name, sender, content = params[0], params[1], trailing
                    print(f"[{room_name}|{sender}] {content}")

                elif command == 'USER_LIST':
                    users = trailing.split(',')
                    print(f"[SYSTEM] 현재 접속자: {', '.join(users)}")
                
                elif command == 'SPELL_RESULT':
                    print(f"[맞춤법 검사 결과] {trailing}")

                elif command == 'JOIN_SUCCESS':
                    global current_mode, current_room
                    current_mode = 'room'
                    current_room = params[0]
                    print(f"[SYSTEM] {trailing} (나가려면 /exit 입력)")

                elif command in ['LOGIN_SUCCESS', 'LOGIN_FAIL']:
                    print(f"[SYSTEM] {trailing}")
                    if command == 'LOGIN_FAIL':
                        event.set() # 로그인 실패 시 프로그램 종료
                
                else:
                    print(f"[SERVER] {msg}")
                
                show_prompt()

        except Exception:
            break
    
    clear_line()
    print("서버와의 연결이 끊어졌습니다. Enter를 눌러 종료하세요.")
    event.set()

def show_main_menu():
    print("\n--- 메뉴 ---")
    print("1. 맞춤법 검사")
    print("2. 영어 단어 퀴즈 출제 (전체)")
    print("3. 1:1 채팅")
    print("4. 영어 선생님 채팅방 입장")
    print("-----------")

def main():
    """메인 함수"""
    global my_id, current_mode, current_room

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

    # 로그인 성공/실패 기다리기
    while not my_id and not event.is_set():
        time.sleep(0.1)
    if event.is_set(): # 로그인 실패
        s.close()
        return

    show_main_menu()

    try:
        while not event.is_set():
            show_prompt()
            try:
                msg = input()
            except (EOFError, KeyboardInterrupt):
                break

            if event.is_set():
                break
            if not msg:
                continue

            # --- 채팅방 모드 ---
            if current_mode == 'room':
                if msg.lower() == '/exit':
                    s.send(f"LEAVE_ROOM {current_room}\n".encode())
                    current_mode = 'main'
                    current_room = ''
                    clear_line()
                    print(f"[SYSTEM] 채팅방에서 퇴장했습니다.")
                    show_main_menu()
                else:
                    s.send(f"ROOM_MSG {current_room} :{msg}\n".encode())
                continue

            # --- 메인 메뉴 모드 ---
            if msg.lower() == '/quit':
                break
            
            if msg == '1':
                text = input("맞춤법을 검사할 영어 문장을 입력하세요: ")
                s.send(f"SPELL_CHECK :{text}\n".encode())
            elif msg == '2':
                quiz = input("전체에게 보낼 퀴즈를 입력하세요: ")
                s.send(f"QUIZ :{quiz}\n".encode())
            elif msg == '3':
                target_id = input("메시지를 보낼 상대방의 ID를 입력하세요: ")
                p_msg = input(f"{target_id}님에게 보낼 메시지: ")
                s.send(f"P_MSG {target_id} :{p_msg}\n".encode())
            elif msg == '4':
                s.send(f"JOIN_ROOM english_teacher_room\n".encode())
            else:
                print("잘못된 메뉴 선택입니다. 메시지를 보내려면 메뉴를 선택하세요.")

    finally:
        if not event.is_set():
            print("\n프로그램을 종료합니다...")
            s.send(f"QUIT :Leaving\n".encode())
        
        event.set()
        s.close()

if __name__ == "__main__":
    import time
    main()
