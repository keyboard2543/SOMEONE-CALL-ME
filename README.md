# SOMEONE-CALL-ME

ฟังไมโครโฟนของเครื่อง แล้ว**แจ้งเตือน**เมื่อได้ยินชื่อของคุณ  
รองรับเสียงไกล / เบา และคำที่ออกเสียงคล้ายชื่อ

> Windows · Python 3.10+ · Offline STT (Whisper)

## Features

- ฟังไมค์ต่อเนื่อง (chunk + overlap)
- ถอดเสียงด้วย **faster-whisper** (ออฟไลน์)
- จับชื่อแบบคลุมเครือ: fuzzy + phonetic + ตัวสะกดไทยที่ฟังคล้ายกัน
- แจ้งเตือน: บี๊บ · Windows toast · พูดด้วย TTS
- ตั้งค่าชื่อ / ความไว / ไมค์ ใน `config.yaml`

## Quick start

### 1) ติดตั้ง

```powershell
git clone https://github.com/keyboard2543/SOMEONE-CALL-ME.git
cd SOMEONE-CALL-ME
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

ถ้า PowerShell บล็อก `Activate.ps1`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### 2) ตั้งชื่อของคุณ

แก้ `config.yaml`:

```yaml
names:
  - "ชื่อจริงของคุณ"
  - "ชื่อเล่น"

aliases:          # คำที่คนมักเรียกผิด / ออกเสียงคล้าย
  - "คำคล้าย1"

sensitivity: 68   # ต่ำ = จับง่าย | สูง = เข้มงวด
language: "th"    # th | en | auto
whisper_model: "base"  # tiny | base | small | medium
```

### 3) รัน

```powershell
python main.py
```

ดูรายการไมค์:

```powershell
python main.py --list-mics
```

แล้วใส่เลขใน `config.yaml` → `microphone_index` ถ้าต้องการ

## Alerts

เมื่อจับชื่อได้ โปรแกรมจะ:

1. **เสียงบี๊บ** (Windows Beep)
2. **Toast notification** มุมขวาล่าง
3. **พูดออกเสียง** ผ่าน Windows SAPI TTS

ปรับได้ใน `config.yaml` → `alert`

## How it works

```
ไมโครโฟน → ตัดเสียงเป็นช่วง ๆ
         → ขยายเสียงเบา (normalize)
         → Whisper ถอดเสียงเป็นข้อความ
         → จับคู่ชื่อแบบคลุมเครือ
         → แจ้งเตือน (+ cooldown กันแจ้งซ้ำ)
```

## Tuning tips

| ปัญหา | แก้ |
|--------|-----|
| จับไม่ค่อยติด | ลด `sensitivity` (เช่น 55–65) หรือเพิ่ม `aliases` |
| แจ้งเตือนมั่ว | เพิ่ม `sensitivity` (เช่น 75–85) |
| เสียงไกล/เบา | ลด `energy_threshold` (เช่น 0.008) · ใช้ `whisper_model: small` |
| มีเสียงรบกวน | เพิ่ม `energy_threshold` เล็กน้อย |
| ช้า | ใช้ `whisper_model: tiny` หรือ `base` |

## Requirements

- Windows (toast + beep + SAPI TTS)
- ไมโครโฟน
- ครั้งแรกจะดาวน์โหลดโมเดล Whisper (~70MB–500MB ตามขนาด)

## CLI

```powershell
python main.py -v              # log ละเอียด
python main.py -c my.yaml      # ใช้ config อื่น
python main.py --list-mics     # รายการไมค์
```

## Tests

```powershell
$env:PYTHONPATH = "."
python tests/test_matcher.py
```

## License

[MIT](LICENSE)
