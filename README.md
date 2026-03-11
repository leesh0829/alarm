# Windows Alarm Popup

간단한 윈도우 기반 팝업 알람 앱입니다.

## 실행

```bash
python windows_alarm_popup.py
```

최초 실행 시 `alarm_schedule.json` 파일이 자동 생성됩니다.

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
- 알람 팝업에서 `5분 후 다시` 버튼으로 스누즈할 수 있습니다.
