# Chat & Spell Checker

이 프로젝트는 파이썬 소켓 프로그래밍을 이용한 다기능 채팅 애플리케이션입니다. 클라이언트는 서버를 통해 다른 클라이언트와 통신하며, 서버가 제공하는 영어 맞춤법 검사, 퀴즈 출제, 1:1 채팅, 그룹 채팅방 등의 기능을 사용할 수 있습니다.

## 주요 기능

*   **서버 기반 맞춤법 검사**: 클라이언트가 보낸 영어 문장의 맞춤법을 서버에서 검사하고 수정 제안을 보내줍니다.
*   **영어 단어 퀴즈**: 한 클라이언트가 퀴즈를 출제하면 모든 클라이언트에게 브로드캐스트됩니다.
*   **퀴즈 정답 도전**: 다른 클라이언트가 출제한 퀴즈의 정답을 맞출 수 있으며, 입력한 정답은 모든 사용자에게 공유됩니다.
*   **1:1 채팅**: 특정 사용자를 지정하여 개인적인 메시지를 주고받을 수 있습니다.
*   **그룹 채팅방**: '영어 선생님 채팅방'에 입장하여 해당 채팅방에 있는 모든 사람과 대화할 수 있습니다.

## 통신 프로토콜

클라이언트와 서버는 개행문자(`\n`)로 구분되는 텍스트 기반 명령어를 통해 통신합니다. 기본 형식은 다음과 같습니다.

`COMMAND param1 param2 ... :trailing_message`

### 클라이언트 -> 서버

*   **로그인**: `LOGIN <user_id>`
*   **맞춤법 검사 요청**: `SPELL_CHECK :<text_to_check>`
*   **퀴즈 출제**: `QUIZ :<question>`
*   **퀴즈 정답 도전**: `QUIZ_ANSWER :<answer>`
*   **1:1 메시지**: `P_MSG <target_user_id> :<message>`
*   **채팅방 입장**: `JOIN_ROOM <room_name>`
*   **채팅방 퇴장**: `LEAVE_ROOM <room_name>`
*   **채팅방 메시지**: `ROOM_MSG <room_name> :<message>`
*   **연결 종료**: `QUIT :<reason>`

### 서버 -> 클라이언트

*   **로그인 성공**: `LOGIN_SUCCESS :<message>`
*   **로그인 실패**: `LOGIN_FAIL :<message>`
*   **맞춤법 검사 결과**: `SPELL_RESULT :<corrected_text>`
*   **일반 메시지 수신 (퀴즈, 1:1, 시스템 메시지 등)**: `MSG_RECV <from_id> :<message>`
*   **채팅방 입장 성공**: `JOIN_SUCCESS <room_name> :<message>`
*   **채팅방 메시지 수신**: `ROOM_MSG_RECV <room_name> <from_id> :<message>`
*   **현재 접속자 목록**: `USER_LIST :<user1,user2,user3...>`

## 실행 방법

1.  **서버 실행**
    - 터미널을 열고 `chat` 디렉토리로 이동합니다.
    - `cd chat`
    - 다음 명령어로 서버를 실행합니다.
    - `python3 chat_server.py`

2.  **클라이언트 실행**
    - 별도의 새 터미널을 열고 `chat` 디렉토리로 이동합니다.
    - `cd chat`
    - 다음 명령어로 클라이언트를 실행합니다.
    - `python3 chat_client.py`
    - 안내에 따라 아이디를 입력하고 메뉴를 선택하여 프로그램을 사용합니다.
