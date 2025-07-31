from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from difflib import get_close_matches
import openai
import os
from dotenv import load_dotenv

# .envの読み込み
load_dotenv()

# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAIキー設定
openai.api_key = OPENAI_API_KEY

# Flask & LINE構成
app = Flask(__name__)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

# 固定FAQデータ（例）
faq_dict = {
    "イベントはいつありますか？": "次回のイベントは8月10日に開催予定です！",
    "持ち物は何ですか？": "筆記用具とメモ帳をご持参ください。",
    "誰が参加できますか？": "高校生以上のどなたでもご参加いただけます。",
}

# Webhookエンドポイント
@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature", "")
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("❌ Webhook処理エラー:", e)
        abort(400)
    return "OK"

# メッセージ受信処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    questions = list(faq_dict.keys())
    close_matches = get_close_matches(user_message, questions, n=1, cutoff=0.6)

    if close_matches:
        response_text = faq_dict[close_matches[0]]
    else:
        response_text = generate_fallback_with_openai(user_message)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response_text)]
            )
        )

# OpenAIによる補完
def generate_fallback_with_openai(user_input):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはFAQボットです。質問に簡潔に日本語で答えてください。"},
                {"role": "user", "content": user_input}
            ],
            max_tokens=200
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print("❌ OpenAIエラー:", e)
        return "申し訳ありません。うまく回答できませんでした。"

# 未処理イベントの受信ログ
@handler.default()
def default_handler(event):
    print("⚠️ 未処理イベント:", event)

# Render用設定
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
