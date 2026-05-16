import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/extract', methods=['POST'])
def extract_video():
    body = request.get_json(force=True, silent=True) or {}
    url = body.get("url")
    
    if not url:
        return jsonify({"status": "failed", "error": "URL is required"}), 400

    # ডিটেক্ট করা হচ্ছে এটি কোন সোশ্যাল মিডিয়া
    if "instagram.com" in url:
        target_api = "https://no-api.bbinl.site/render/instagram"
    elif "facebook.com" in url or "fb.watch" in url:
        target_api = "https://no-api.bbinl.site/render/facebook"
    else:
        return jsonify({"status": "failed", "error": "Only Instagram and Facebook URLs are supported"}), 400

    try:
        # থার্ড পার্টি এপিআই-তে রিকোয়েস্ট পাঠানো হচ্ছে
        res = requests.post(
            target_api,
            headers={"Content-Type": "application/json"},
            json={"url": url, "cookies": ""},
            timeout=30
        )
        
        if res.status_code != 200:
            return jsonify({"status": "failed", "error": "Failed to fetch media from source"}), res.status_code

        # HTML পার্সিং (আসল ভিডিও লিঙ্ক বের করা)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # ১. <source> ট্যাগ থেকে ভিডিওর মেইন ডিরেক্ট লিঙ্ক খোঁজা
        video_tag = soup.find('source')
        video_url = video_tag['src'] if video_tag and video_tag.has_attr('src') else None
        
        # ২. ভিডিও থাম্বনেইল বা পোস্টার ইমেজ খোঁজা
        main_player = soup.find('video')
        thumb_url = None
        if main_player and main_player.has_attr('poster'):
            # পোস্টার লিংক থেকে প্রক্সি অংশ বাদ দিয়ে অরিজিনাল লিঙ্কটি নেওয়া হচ্ছে
            poster = main_player['poster']
            if "/proxy/image?url=" in poster:
                from urllib.parse import unquote
                thumb_url = unquote(poster.split("/proxy/image?url=")[1])
            else:
                thumb_url = poster

        # যদি কোনো ভিডিও লিঙ্ক না পাওয়া যায়
        if not video_url:
            return jsonify({"status": "failed", "error": "No extractable video found"}), 404

        # সাকসেস রেসপন্স (টেলিগ্রাম বটের ফরম্যাটের সাথে মিল রেখে)
        return jsonify({
            "status": "done",
            "data": {
                "id": "extracted_media",
                "status": "done",
                "images": [video_url]  # বটের কোড যেন সরাসরি ভিডিও ডাউনলোড করতে পারে
            },
            "thumbnail": thumb_url
        }), 200

    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "FB & IG Video Extractor API is Running!",
        "usage": "POST /api/extract with JSON body {'url': 'YOUR_URL'}"
    })
      
