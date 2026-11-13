#!/usr/bin/env python3
"""Reference webhook for an AliGenie custom story skill.

POST /skill implements the AliGenie protocol:
  utterance + slot values -> episode number -> audioPlayGenieSource action.

Fill in EPISODE_AUDIO / BLOCK_AUDIO with your own audio IDs from the
platform's audio library (see README). Run behind nginx on a server
inside mainland China, reachable by its IP address (an unfiled domain
will be blocked by the cloud provider).

Logs every request body to /var/log/miao-skill.log — the log is your
main diagnostic: no new entry after an online test means the request
never reached this backend.
"""
import json, re, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = "/var/log/miao-skill.log"

# episode number -> platform audio ID (fill in after uploading)
EPISODE_AUDIO = {2: 100001, 3: 100002, 4: 100003, 5: 100004}
# block start episode -> (audio ID of the merged 5-episode file, reply text)
BLOCK_AUDIO = {1: (100000, "好的，给你播放第1到5集，五集连着放。")}
SERIES_NAME = "我的故事"

def log(*a):
    line = time.strftime("%F %T ") + " ".join(str(x) for x in a)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)

def make_resp(rv):
    base = {"reply": "", "resultType": "RESULT", "actions": [], "properties": {},
            "executeCode": "SUCCESS", "msgInfo": "", "askedInfos": []}
    base.update(rv)
    return {"returnCode": "0", "returnErrorSolution": "", "returnMessage": "",
            "returnValue": base}

CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}

def cn_to_int(s):
    """Chinese numeral -> int. Handles compositional (五十一, 一百零二)
    and digit-string (一七六七) forms. Returns None if unparsable."""
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if all(c in CN_DIGITS for c in s) and len(s) >= 2 and not any(u in s for u in CN_UNITS):
        return int("".join(str(CN_DIGITS[c]) for c in s))
    total, section, number = 0, 0, 0
    for c in s:
        if c in CN_DIGITS:
            number = CN_DIGITS[c]
        elif c in CN_UNITS:
            unit = CN_UNITS[c]
            if unit == 10000:
                section = (section + number) * unit
                total += section
                section, number = 0, 0
            else:
                if number == 0:
                    number = 1
                section += number * unit
                number = 0
        else:
            return None
    return total + section + number

CN_CHARS = "零一二两三四五六七八九十百千万"

def extract_number(text):
    """First number in text, Arabic or Chinese."""
    mm = re.search(r"\d+", text or "")
    if mm:
        return int(mm.group(0))
    mm = re.search(rf"[{CN_CHARS}]+", text or "")
    if mm:
        return cn_to_int(mm.group(0))
    return None

def handle_skill(req):
    utt = str(req.get("utterance") or "")
    slots = {}
    for s in (req.get("slotEntities") or []):
        if isinstance(s, dict) and s.get("intentParameterName"):
            slots[s["intentParameterName"]] = s.get("standardValue") or s.get("originalValue") or ""
    ep = None
    for v in slots.values():
        n = extract_number(str(v))
        if n is not None:
            ep = n
            break
    if ep is None:
        mm = re.search(rf"第\s*([0-9{CN_CHARS}]+)\s*集", utt)
        if mm:
            ep = cn_to_int(mm.group(1)) if not mm.group(1).isdigit() else int(mm.group(1))
    if ep is not None:
        blk = BLOCK_AUDIO.get(ep)
        if blk is not None:
            return make_resp({"reply": blk[1], "actions": [
                {"name": "audioPlayGenieSource", "properties": {"audioGenieId": str(blk[0])}}]})
        aid = EPISODE_AUDIO.get(ep)
        if aid is not None:
            return make_resp({"reply": f"好的，给你播放{SERIES_NAME}第{ep}集。", "actions": [
                {"name": "audioPlayGenieSource", "properties": {"audioGenieId": str(aid)}}]})
        return make_resp({"reply": f"第{ep}集还没有传上来。"})
    if ("停" in utt) or ("暂停" in utt):
        return make_resp({"reply": "好的，停了。"})
    return make_resp({"reply": "想听第几集？跟我说，播放第几集，就可以了。",
                      "resultType": "ASK_INF"})

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json;charset=UTF-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/health"):
            self._json({"ok": True})
        else:
            self.send_response(404)
            self.send_header("Content-Length", "9")
            self.end_headers()
            self.wfile.write(b"not found")

    do_HEAD = do_GET

    def do_POST(self):
        if self.path in ("/skill", "/skill/"):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            log("ALIGENIE_REQ", raw.decode("utf-8", "replace"))
            try:
                req = json.loads(raw.decode("utf-8", "replace") or "{}")
            except Exception:
                req = {}
            self._json(handle_skill(req))
        else:
            self.send_response(404)
            self.send_header("Content-Length", "9")
            self.end_headers()
            self.wfile.write(b"not found")

if __name__ == "__main__":
    log("miao-skilld starting on 127.0.0.1:3927")
    ThreadingHTTPServer(("127.0.0.1", 3927), H).serve_forever()
