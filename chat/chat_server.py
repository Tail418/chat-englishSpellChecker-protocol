# chat_server_irc.py
from socket import *
from threading import Thread, Event
import sys

# --- 서버 설정 ---
HOST = ''
PORT = 5001
ADDR = (HOST, PORT)
BUFSIZE = 1024

# --- 전역 변수 ---
event = Event()
client_sockets = {}  # { 'id': socket }

def parse_message(msg_str):
    """IRC 스타일 메시지를 파싱합니다: CMD param1 param2 ... :trailing"""
    msg_str = msg_str.strip()
    
    if ' :' in msg_str:
        parts, trailing = msg_str.split(' :', 1)
    else:
        parts, trailing = msg_str, None
        
    tokens = parts.split()
    command = tokens[0].upper()
    params = tokens[1:]
    
    return command, params, trailing

def broadcast(message):
    """모든 클라이언트에게 메시지를 인코딩하여 전송"""
    for sock in client_sockets.values():
        try:
            sock.send(message.encode())
        except Exception as e:
            print(f"브로드캐스트 오류: {e}")

def update_user_list():
    """모든 클라이언트에게 현재 사용자 목록을 브로드캐스트"""
    user_list = ",".join(client_sockets.keys())
    broadcast(f"USER_LIST :{user_list}")

def handle_message(cs, msg):
    """클라이언트로부터 받은 IRC 스타일 메시지를 처리"""
    command, params, trailing = parse_message(msg)

    if command == 'LOGIN':
        user_id = params[0]
        if user_id not in client_sockets:
            client_sockets[user_id] = cs
            print(f"로그인: {user_id}님이 접속했습니다.")
            cs.send("LOGIN_SUCCESS :서버에 성공적으로 접속했습니다.\n".encode())
            update_user_list()
            return True
        else:
            cs.send("LOGIN_FAIL :이미 사용 중인 ID입니다.\n".encode())
            return False

    elif command == 'MSG_ALL':
        from_id = params[0]
        content = trailing
        print(f"브로드캐스트: {from_id} -> {content}")
        # 다른 모든 사용자에게 메시지 전달
        for uid, sock in client_sockets.items():
            if sock != cs:
                sock.send(f"MSG_RECV {from_id} :{content}\n".encode())
        return True

    elif command == 'QUIT':
        user_id = params[0]
        if user_id in client_sockets:
            print(f"로그아웃: {user_id}님이 연결을 종료했습니다.")
            del client_sockets[user_id]
            cs.close()
            update_user_list()
        return False
    
    return True

def client_communication_thread(cs, addr):
    """개별 클라이언트와의 통신을 처리하는 스레드"""
    print(f"연결 수락: {addr} 에서 새로운 클라이언트가 연결되었습니다.")
    
    try:
        while not event.is_set():
            msg = cs.recv(BUFSIZE).decode()
            if not msg:
                break
            # 여러 메시지가 한번에 올 경우를 대비해 개행으로 분리
            for line in msg.strip().split('\n'):
                if line:
                    if not handle_message(cs, line):
                        break
    except Exception:
        pass
    
    # --- 스레드 종료 처리 ---
    disconnected_user = None
    for user_id, sock in list(client_sockets.items()):
        if sock == cs:
            disconnected_user = user_id
            del client_sockets[user_id]
            break
            
    if disconnected_user:
        print(f"연결 종료: {disconnected_user} ({addr})")
        update_user_list()

    cs.close()

def accept_thread():
    """새로운 클라이언트의 연결을 수락하는 스레드"""
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(ADDR)
    server_socket.listen(10)
    print(f"서버가 {PORT} 포트에서 시작되었습니다.")

    while not event.is_set():
        try:
            client_socket, addr_info = server_socket.accept()
            thread = Thread(target=client_communication_thread, args=(client_socket, addr_info))
            thread.daemon = True
            thread.start()
        except Exception:
            break
    
    server_socket.close()

def main():
    accept_th = Thread(target=accept_thread)
    accept_th.daemon = True
    accept_th.start()

    print("서버를 종료하려면 'q'를 입력하세요.")
    try:
        while True:
            cmd = input()
            if cmd.lower() == 'q':
                break
    except (KeyboardInterrupt, EOFError):
        pass

    print("서버를 종료합니다...")
    event.set()
    
    for sock in client_sockets.values():
        sock.close()
    
    try:
        with socket(AF_INET, SOCK_STREAM) as s:
            s.connect(ADDR)
    except:
        pass

    print("서버가 종료되었습니다.")

if __name__ == "__main__":
    main()
