# chat_client_irc.py
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
            
            # 여러 메시지가 한번에 올 수 있으므로 개행으로 분리
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

def main():
    """메인 함수"""
    global my_id
    
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

    # ID 등록 요청
    s.send(f"LOGIN {my_id}\n".encode())

    listener_thread = Thread(target=listen_for_messages, args=(s,))
    listener_thread.daemon = True
    listener_thread.start()

    print("\n채팅 시작! 메시지를 입력하세요. 종료하려면 '/quit'을 입력하세요.")
    print("> ", end="")

    try:
        while not event.is_set():
            msg_to_send = input()
            
            if event.is_set():
                break

            if msg_to_send.lower() == '/quit':
                s.send(f"QUIT {my_id} :Leaving\n".encode())
                break
            
            # 브로드캐스트 메시지 전송
            s.send(f"MSG_ALL {my_id} :{msg_to_send}\n".encode())
            print("> ", end="")

    except (KeyboardInterrupt, EOFError):
        s.send(f"QUIT {my_id} :Leaving by force\n".encode())
    
    finally:
        print("\n프로그램을 종료합니다...")
        event.set()
        s.close()

if __name__ == "__main__":
    main()
