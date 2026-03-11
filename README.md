# Windows Alarm Popup

간단한 윈도우 기반 팝업 알람 앱입니다.

## 실행

```bash
python windows_alarm_popup.py
```

최초 실행 시 `alarm_schedule.json` 파일이 자동 생성됩니다.

윈도우에서는 아래 파일을 더블클릭해서 쓰는 편이 더 간단합니다.

- `start_alarm.bat`: 알람 앱 시작
- `stop_alarm.bat`: 알람 앱 종료
- `start_alarm.vbs`: 콘솔창 없이 알람 앱 시작
- `stop_alarm.vbs`: 콘솔창 없이 알람 앱 종료

같은 앱을 여러 번 실행하면 중복 실행되지 않고 안내 메시지만 표시됩니다.
실행 중에는 메인 창 대신 시스템 트레이 아이콘으로 동작합니다.

트레이 아이콘 사용법:

- 왼쪽 더블클릭: 설정 파일 열기
- 오른쪽 클릭: `설정 파일 열기`, `상태 보기`, `종료`

명령줄에서도 아래처럼 사용할 수 있습니다.

```bash
python windows_alarm_popup.py start
python windows_alarm_popup.py stop
python windows_alarm_popup.py status
```

## 설정 파일 형식 (`alarm_schedule.json`)

```json
{
  "position": "center",
  "alarms": [
    {
      "type": "daily",
      "times": ["09:00", "13:30"],
      "title": "매일 알람",
      "message": "확인할 작업이 있어요."
    },
    {
      "type": "weekday",
      "weekdays": ["mon", "wed", "fri"],
      "times": ["08:40"],
      "title": "운동 알람",
      "message": "운동 갈 시간이에요!"
    },
    {
      "type": "once",
      "date": "2026-03-12",
      "times": ["15:00"],
      "title": "단일 알람",
      "message": "오늘만 울리는 알람"
    }
  ]
}
```

## 알람 타입

- `once`: 지정한 날짜(`date`)에만 울림
- `daily`: 매일 같은 시간에 울림
- `weekday`: 지정한 요일(`weekdays`)에 울림

`weekdays`는 아래 값들을 지원합니다.

- 숫자: `0~6` (`0=월`, `6=일`)
- 문자열: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`
- 한글 요일: `월`, `화`, `수`, `목`, `금`, `토`, `일`

## 기타

- 설정 JSON은 실행 중 자동으로 재로드됩니다.
- 잘못된 형식은 팝업으로 에러를 알려주고 기본 설정으로 fallback 합니다.
- 시간 값은 `16:27` 형식이 기본이며, 실수로 `16,27`처럼 써도 자동 보정합니다.
- 알람 팝업에서 `5분 후 다시` 버튼으로 스누즈할 수 있습니다.
