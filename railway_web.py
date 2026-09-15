import os
import json
import urllib.parse
import urllib.request
import urllib.error
from flask import Flask, request, render_template_string

app = Flask(__name__)

BASE_URL = os.environ.get("API_URL", "http://notessub.duckdns.org/")
TIMEOUT = float(os.environ.get("API_TIMEOUT", "30"))

HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NotesSub</title>
<style>
body{font-family:Arial;max-width:520px;margin:40px auto;padding:20px}
input,button{width:100%;padding:13px;margin:7px 0;box-sizing:border-box}
button{cursor:pointer}
pre{white-space:pre-wrap;word-break:break-word}
.box{padding:15px;border:1px solid #ddd;border-radius:10px}
</style>
</head>
<body>
<h2>NotesSub</h2>
<div class="box">
<form method="post">
<input name="number" placeholder="Enter number" value="{{number}}" required>
{% if otp_requested %}
<input name="otp" placeholder="Enter OTP" required>
{% endif %}
<button type="submit">{{ "Verify OTP" if otp_requested else "Send OTP" }}</button>
</form>
{% if message %}<p>{{message}}</p>{% endif %}
{% if result %}<pre>{{result}}</pre>{% endif %}
{% if link %}<p><b>Your link:</b></p><a href="{{link}}" target="_blank">{{link}}</a>{% endif %}
</div>
</body>
</html>
"""

def api_request(number, otp=None):
    params = {"number": number}
    if otp is not None:
        params["otp"] = otp
    separator = "&" if "?" in BASE_URL else "?"
    url = BASE_URL + separator + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent":"NotesSub-Web/1.0","Accept":"application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw)

def find_link(data):
    if isinstance(data, dict):
        for key in ("unique_link", "link"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://","https://")):
                return value
        for value in data.values():
            found = find_link(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_link(item)
            if found:
                return found
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    number = ""
    otp_requested = False
    message = ""
    result = ""
    link = ""

    if request.method == "POST":
        number = request.form.get("number", "").strip()
        otp = request.form.get("otp", "").strip()

        try:
            if not otp:
                response = api_request(number)
                otp_requested = True
                message = response.get("message", "OTP request completed.") if isinstance(response, dict) else "OTP request completed."
                result = json.dumps(response, indent=2, ensure_ascii=False)
            else:
                response = api_request(number, otp)
                result = json.dumps(response, indent=2, ensure_ascii=False)
                link = find_link(response)
                message = "OTP verification completed."
                if link:
                    with open("links.txt", "a", encoding="utf-8") as f:
                        f.write(link.rstrip("\r\n") + "\n")
                else:
                    message = "Response received, but no link was found."
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            message = f"Request failed: {e}"

    return render_template_string(
        HTML, number=number, otp_requested=otp_requested,
        message=message, result=result, link=link
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
