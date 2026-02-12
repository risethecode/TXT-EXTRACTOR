import requests, os, sys, re
import math
import json, asyncio
import subprocess
import datetime
import time
import random
import base64
from Extractor import app
from pyrogram import filters
from subprocess import getstatusoutput

# ============ API CONFIGURATION ============
PW_API_BASE = "https://api.penpencil.co"
ORGANIZATION_ID = "5eb393ee95fab7468a79d189"
CLIENT_ID = "5eb393ee95fab7468a79d189"

# Request delay configuration (in seconds)
REQUEST_DELAY = 2  # Delay between API calls
BATCH_DELAY = 1    # Delay between batch operations

# Headers for web requests
WEB_HEADERS = {
    "Content-Type": "application/json",
    "Client-Id": CLIENT_ID,
    "Client-Type": "WEB",
    "Client-Version": "6.0.0",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.pw.live",
    "Referer": "https://www.pw.live/",
}

# Headers for mobile requests
MOBILE_HEADERS = {
    'Host': 'api.penpencil.co',
    'client-id': CLIENT_ID,
    'client-version': '12.84',
    'user-agent': 'Android',
    'randomid': 'e4307177362e86f1',
    'client-type': 'MOBILE',
    'device-meta': '{APP_VERSION:12.84,DEVICE_MAKE:Asus,DEVICE_MODEL:ASUS_X00TD,OS_VERSION:6,PACKAGE_NAME:xyz.penpencil.physicswalb}',
    'content-type': 'application/json; charset=UTF-8',
}


def safe_request(method, url, max_retries=3, retry_delay=3, **kwargs):
    """
    Make HTTP request with retry logic and proper delays
    """
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=30, **kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, timeout=30, **kwargs)
            else:
                response = requests.request(method, url, timeout=30, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                wait_time = retry_delay * (attempt + 1) + random.uniform(1, 2)
                print(f"Rate limited. Waiting {wait_time:.1f}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            
            return response
            
        except Exception as e:
            print(f"Request error: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise
    
    return response


def decode_jwt(token):
    """Decode JWT token to extract user info"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"JWT decode error: {e}")
        return None


async def get_otp(message, phone_no):
    """Send OTP to mobile number"""
    url = f"{PW_API_BASE}/v1/users/get-otp"
    
    headers = WEB_HEADERS.copy()
    headers["Integration-With"] = "Origin"
    
    payload = {
        "username": phone_no,
        "countryCode": "+91",
        "organizationId": ORGANIZATION_ID,
    }
    
    try:
        response = safe_request("POST", url, params={"smsType": "0"}, headers=headers, json=payload)
        data = response.json()
        
        if response.status_code == 200:
            await message.reply_text("**✅ OTP Sent Successfully!**\n\nCheck your mobile number.")
            return True
        else:
            error = data.get('message', f'Error {response.status_code}')
            await message.reply_text(f"**❌ Failed to Send OTP**\n\nReason: `{error}`")
            return False
            
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")
        return False


async def get_token(message, phone_no, otp):
    """Generate access token using OTP"""
    url = f"{PW_API_BASE}/v3/oauth/token"
    
    payload = {
        "username": phone_no,
        "otp": otp,
        "client_id": "system-admin",
        "client_secret": "KjPXuAVfC5xbmgreETNMaL7z",
        "grant_type": "password",
        "organizationId": ORGANIZATION_ID,
        "latitude": 0,
        "longitude": 0
    }
    
    headers = WEB_HEADERS.copy()
    headers["Randomid"] = "990963b2-aa95-4eba-9d64-56bb55fca9a9"
    
    try:
        response = safe_request("POST", url, headers=headers, json=payload)
        data = response.json()
        
        if response.status_code == 200 and 'data' in data:
            token = data['data'].get('access_token')
            refresh = data['data'].get('refresh_token', '')
            return token, refresh
        else:
            error = data.get('message', 'Unknown error')
            await message.reply_text(f"**❌ Token Generation Failed**\n\n{error}")
            return None, None
            
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")
        return None, None


async def pw_mobile(app, message):
    """Handle mobile-based login"""
    try:
        # Get phone number
        ask_phone = await app.ask(message.chat.id, text="**📱 ENTER YOUR PW MOBILE NO. WITHOUT COUNTRY CODE.**")
        phone_no = ask_phone.text.strip()
        await ask_phone.delete()
        
        if not phone_no.isdigit() or len(phone_no) != 10:
            await message.reply_text("**❌ Invalid Mobile Number!** Enter 10-digit number.")
            return
        
        # Send OTP
        if not await get_otp(message, phone_no):
            return
        
        # Get OTP
        ask_otp = await app.ask(message.chat.id, text="**🔑 ENTER OTP SENT TO YOUR MOBILE**")
        otp = ask_otp.text.strip()
        await ask_otp.delete()
        
        if not otp.isdigit():
            await message.reply_text("**❌ Invalid OTP!**")
            return
        
        # Generate token
        token, refresh = await get_token(message, phone_no, otp)
        
        if token:
            # Decode and show info
            jwt_data = decode_jwt(token)
            user_data = jwt_data.get('data', {}) if jwt_data else {}
            
            msg = f"""**✅ LOGIN SUCCESSFUL!**

**👤 User:** `{user_data.get('firstName', 'Unknown')} {user_data.get('lastName', '')}`
**📱 Mobile:** `{phone_no}`
**📧 Email:** `{user_data.get('email', 'N/A')}`

**🔐 ACCESS TOKEN:**
`{token}`

**📋 REFRESH TOKEN:**
`{refresh}`

**📅 Generated:** `{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`"""
            
            await message.reply_text(msg)
            
            # Delay before fetching batches
            time.sleep(REQUEST_DELAY)
            await fetch_and_show_batches(app, message, token)
        else:
            await message.reply_text("**❌ Failed to generate token.**")
            
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def pw_token(app, message):
    """Handle token-based login"""
    try:
        ask_token = await app.ask(message.chat.id, text="**🔑 ENTER YOUR PW ACCESS TOKEN**")
        token = ask_token.text.strip()
        await ask_token.delete()
        
        if not token:
            await message.reply_text("**❌ Token cannot be empty!**")
            return
        
        status = await message.reply_text("**🔄 Verifying token...**")
        
        # Decode JWT to get user info
        jwt_data = decode_jwt(token)
        user_data = jwt_data.get('data', {}) if jwt_data else {}
        
        await status.delete()
        
        if user_data:
            msg = f"""**✅ TOKEN VERIFIED!**

**👤 Name:** `{user_data.get('firstName', 'Unknown')} {user_data.get('lastName', '')}`
**📱 Mobile:** `{user_data.get('username', 'Unknown')}`
**📧 Email:** `{user_data.get('email', 'N/A')}`
**🆔 ID:** `{user_data.get('_id', 'N/A')}`

**📅 Verified:** `{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`

**✅ Token is valid! Proceeding...**"""
            
            await message.reply_text(msg)
            
            # Delay before fetching batches
            time.sleep(REQUEST_DELAY)
            await fetch_and_show_batches(app, message, token)
        else:
            await message.reply_text("**❌ Invalid Token Format!**")
            
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def fetch_and_show_batches(app, message, token):
    """Fetch and display user's batches using correct API endpoint"""
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.pw.live/",
        "Authorization": f"Bearer {token}",
        "Randomid": "990963b2-aa95-4eba-9d64-56bb55fca9a9"
    }
    
    try:
        status = await message.reply_text("**🔄 Fetching your batches...**")
        
        all_batches = []
        page = 1
        max_pages = 10  # Safety limit
        
        # Fetch all pages of batches
        while page <= max_pages:
            url = f"{PW_API_BASE}/batch-service/v1/batches/purchased-batches?amount=paid&page={page}&type=ALL"
            
            response = safe_request("GET", url, headers=headers, max_retries=2, retry_delay=2)
            data = response.json()
            
            if response.status_code == 401:
                await status.delete()
                await message.reply_text("**❌ Token Expired!** Generate a new token.")
                return
            
            # Check for successful response
            if data.get('success') and isinstance(data.get('data'), list):
                batches = data['data']
                if not batches:
                    break
                    
                for batch in batches:
                    all_batches.append({
                        'name': batch.get('name', 'Unknown'),
                        'slug': batch.get('slug', 'N/A'),
                        '_id': batch.get('_id', 'N/A'),
                        'startDate': batch.get('startDate', ''),
                        'endDate': batch.get('endDate', ''),
                        'expiryDate': batch.get('expiryDate', '')
                    })
                
                # If less than expected results, we've reached the end
                if len(batches) < 10:  # Assuming page size is 10
                    break
                    
                page += 1
                time.sleep(0.5)  # Small delay between pages
            else:
                break
        
        await status.delete()
        
        if not all_batches:
            await message.reply_text("**⚠️ No batches found!**\n\nMake sure you have purchased batches.")
            return
        
        # Display batches
        msg = f"**📚 YOUR BATCHES ({len(all_batches)} found):\n\nBatch Name | Batch ID | Slug**\n\n"
        for batch in all_batches:
            name = batch["name"]
            batch_id = batch["_id"]
            slug = batch["slug"]
            msg += f"**📖 {name}**\n`{batch_id}`\nSlug: `{slug}`\n\n"
        
        await message.reply_text(msg)
        
        # Store batches for later use
        user_batches = all_batches
        
        # Ask for batch ID or Slug
        ask_batch = await app.ask(message.chat.id, text="**📥 Send the Batch ID (or Slug) to download**")
        batch_input = ask_batch.text.strip()
        await ask_batch.delete()
        
        if not batch_input:
            await message.reply_text("**❌ Batch ID cannot be empty!**")
            return
        
        # Find batch by ID or slug
        selected_batch = None
        for batch in all_batches:
            if batch_input in [batch['_id'], batch['slug']]:
                selected_batch = batch
                break
        
        if not selected_batch:
            await message.reply_text("**❌ Batch not found!** Please check the ID/Slug and try again.")
            return
        
        # Delay before fetching batch details
        time.sleep(REQUEST_DELAY)
        await show_download_options(app, message, token, selected_batch)
        
    except Exception as e:
        await message.reply_text(f"**❌ Error fetching batches:** `{str(e)}`")


async def show_download_options(app, message, token, batch):
    """Show download options (Full Batch or Today Class)"""
    
    batch_id = batch['_id']
    batch_slug = batch['slug']
    batch_name = batch['name']
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.pw.live/",
        "Authorization": f"Bearer {token}",
        "Randomid": "990963b2-aa95-4eba-9d64-56bb55fca9a9"
    }
    
    try:
        # Fetch batch details using slug
        status = await message.reply_text("**🔄 Fetching batch details...**")
        
        url = f"{PW_API_BASE}/v3/batches/{batch_slug}/details"
        response = safe_request("GET", url, headers=headers, max_retries=2, retry_delay=2)
        
        await status.delete()
        data = response.json()
        
        if not data.get('data'):
            await message.reply_text("**❌ Invalid Batch ID or Slug!**\n\nPlease check and try again.")
            return
        
        batch_data = data['data']
        subjects = batch_data.get('subjects', [])
        
        if not subjects:
            await message.reply_text("**❌ No subjects found in this batch!**")
            return
        
        # Store batch info for later use
        batch_info = {
            'id': batch_id,
            'slug': batch_slug,
            'name': batch_name,
            'subjects': subjects
        }
        
        # Show options
        options = f"""**📥 Choose Download Option for {batch_name}:**

1️⃣ **Full Batch** - All subjects content

2️⃣ **Today Class** - Specific date content

**Send 1 or 2**"""
        
        ask_option = await app.ask(message.chat.id, text=options)
        option = ask_option.text.strip().lower()
        await ask_option.delete()
        
        if option in ["1", "full", "batch", "full batch"]:
            await download_full_batch(app, message, token, batch_info)
        elif option in ["2", "today", "date", "today class"]:
            await download_today_class(app, message, token, batch_info)
        else:
            await message.reply_text("**❌ Invalid option!** Send 1 or 2.")
            
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def download_full_batch(app, message, token, batch_info):
    """Download full batch content"""
    
    batch_slug = batch_info['slug']
    batch_name = batch_info['name']
    subjects = batch_info['subjects']
    
    # Show subjects
    msg = "**📖 SUBJECTS:\n\nSubject Name | Subject ID | Slug**\n\n"
    all_slugs = ""
    for subj in subjects:
        name = subj.get('subject', 'Unknown')
        sid = subj.get('_id', 'N/A')
        slug = subj.get('slug', 'N/A')
        msg += f"**{name}**\nID: `{sid}`\nSlug: `{slug}`\n\n"
        all_slugs += f"{slug}&"
    
    await message.reply_text(msg)
    
    # Ask for subject slugs (not IDs)
    ask_subjects = await app.ask(
        message.chat.id,
        text=f"**Send Subject Slugs to download (format: slug1&slug2&slug3)**\n\n**For all subjects, send:**\n`{all_slugs}`"
    )
    selected = ask_subjects.text.strip()
    await ask_subjects.delete()
    
    if not selected:
        await message.reply_text("**❌ Subject Slugs cannot be empty!**")
        return
    
    # Process download
    status = await message.reply_text("**🔄 Downloading batch content...**")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.pw.live/",
        "Authorization": f"Bearer {token}",
        "Randomid": "990963b2-aa95-4eba-9d64-56bb55fca9a9"
    }
    
    output_file = "batch_content.txt"
    if os.path.exists(output_file):
        os.remove(output_file)
    
    selected_slugs = [s.strip() for s in selected.split('&') if s.strip()]
    total_items = 0
    
    for subject_slug in selected_slugs:
        # Find subject info
        subject_info = None
        for s in subjects:
            if s.get('slug') == subject_slug:
                subject_info = s
                break
        
        if not subject_info:
            continue
        
        subject_name = subject_info.get('subject', 'Unknown')
        tag_count = subject_info.get('tagCount', 0)
        pages = max(1, math.ceil(tag_count / 20)) if tag_count else 1
        
        await status.edit_text(f"**🔄 Downloading {subject_name}...**")
        
        for page in range(1, pages + 1):
            try:
                # Delay between requests
                time.sleep(BATCH_DELAY)
                
                # Use correct v2 API endpoint with slugs
                url = f"{PW_API_BASE}/v2/batches/{batch_slug}/subject/{subject_slug}/topics?page={page}"
                response = safe_request("GET", url, headers=headers, max_retries=2, retry_delay=2)
                
                data = response.json()
                topics = data.get('data', [])
                
                if topics:
                    total_items += len(topics)
                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(f"\n{'='*50}\n")
                        f.write(f"Subject: {subject_name}\n")
                        f.write(f"Page: {page}\n")
                        f.write(f"{'='*50}\n\n")
                        
                        for topic in topics:
                            f.write(f"📚 Topic: {topic.get('name', 'N/A')}\n")
                            f.write(f"   ID: {topic.get('_id', 'N/A')}\n")
                            f.write(f"   Slug: {topic.get('slug', 'N/A')}\n")
                            
                            # Get videos info
                            videos = topic.get('videos', [])
                            if videos:
                                f.write(f"   🎥 Videos: {len(videos)}\n")
                                for v in videos:
                                    f.write(f"      - {v.get('topic', 'N/A')}\n")
                                    if v.get('url'):
                                        f.write(f"        URL: {v.get('url')}\n")
                            
                            # Get notes info
                            notes = topic.get('notes', [])
                            if notes:
                                f.write(f"   📝 Notes: {len(notes)}\n")
                            
                            f.write("-" * 40 + "\n")
                            
            except Exception as e:
                print(f"Error on page {page}: {e}")
                continue
    
    await status.delete()
    
    if os.path.exists(output_file) and total_items > 0:
        await app.send_document(
            message.chat.id,
            document=output_file,
            caption=f"**✅ Download Complete!**\n\n**Batch:** {batch_name}\n**Total Topics:** {total_items}"
        )
    else:
        await message.reply_text("**⚠️ No content found!**")


async def download_today_class(app, message, token, batch_info):
    """Download content for a specific date"""
    
    batch_slug = batch_info['slug']
    batch_name = batch_info['name']
    subjects = batch_info['subjects']
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Ask for date
    ask_date_text = await message.reply_text(
        f"**📅 Enter date (YYYY-MM-DD)**\n\n**Today:** `{today}`\n**Or send 'today'**"
    )
    date_response = await app.ask(message.chat.id, text="**Send date:**")
    date_input = date_response.text.strip().lower()
    await ask_date_text.delete()
    await date_response.delete()
    
    if date_input == 'today':
        selected_date = today
    else:
        selected_date = date_input
    
    # Validate date
    try:
        datetime.datetime.strptime(selected_date, "%Y-%m-%d")
    except ValueError:
        await message.reply_text("**❌ Invalid date format!** Use YYYY-MM-DD")
        return
    
    # Show subjects
    msg = "**📚 SUBJECTS:**\n\n"
    for subj in subjects:
        msg += f"**{subj.get('subject')}** | Slug: `{subj.get('slug')}`\n"
    
    await message.reply_text(msg)
    
    # Ask which subjects
    ask_subj = await message.reply_text("**Send Subject Slugs (comma separated) or 'all'**")
    subject_response = await app.ask(message.chat.id, text="**Send:**")
    subject_input = subject_response.text.strip()
    await ask_subj.delete()
    await subject_response.delete()
    
    if subject_input.lower() == 'all':
        selected_subjects = subjects
    else:
        slugs = [s.strip() for s in subject_input.split(',')]
        selected_subjects = [s for s in subjects if s.get('slug') in slugs]
    
    if not selected_subjects:
        await message.reply_text("**❌ No valid subjects selected!**")
        return
    
    # Start downloading
    status = await message.reply_text(f"**🔄 Searching content for {selected_date}...**")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.pw.live/",
        "Authorization": f"Bearer {token}",
        "Randomid": "990963b2-aa95-4eba-9d64-56bb55fca9a9"
    }
    
    output_file = f"content_{selected_date}.txt"
    if os.path.exists(output_file):
        os.remove(output_file)
    
    total_found = 0
    
    for subject in selected_subjects:
        subject_slug = subject.get('slug')
        subject_name = subject.get('subject', 'Unknown')
        
        await status.edit_text(f"**🔄 Searching in {subject_name}...**")
        
        page = 1
        subject_content = []
        max_pages = 50  # Safety limit
        
        while page <= max_pages:
            try:
                # Delay between requests
                time.sleep(BATCH_DELAY)
                
                # Use correct v2 API endpoint
                url = f"{PW_API_BASE}/v2/batches/{batch_slug}/subject/{subject_slug}/topics?page={page}"
                response = safe_request("GET", url, headers=headers, max_retries=2, retry_delay=2)
                
                data = response.json()
                topics = data.get('data', [])
                
                if not topics:
                    break
                
                # Filter by date - check video dates
                for topic in topics:
                    videos = topic.get('videos', [])
                    for video in videos:
                        video_date = video.get('date', '')
                        if video_date:
                            # Parse date from ISO format
                            try:
                                v_date = video_date.split('T')[0] if 'T' in video_date else video_date[:10]
                                if v_date == selected_date:
                                    subject_content.append({
                                        'topic': topic.get('name', 'N/A'),
                                        'video_topic': video.get('topic', 'N/A'),
                                        'date': video_date,
                                        'url': video.get('url', 'N/A'),
                                        'duration': video.get('videoDetails', {}).get('duration', 'N/A'),
                                        'teacher': video.get('teachers', [{}])[0].get('firstName', 'Unknown') if video.get('teachers') else 'Unknown'
                                    })
                            except:
                                pass
                
                page += 1
                
            except Exception as e:
                print(f"Error: {e}")
                break
        
        # Write to file
        if subject_content:
            total_found += len(subject_content)
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"📚 SUBJECT: {subject_name}\n")
                f.write(f"📅 DATE: {selected_date}\n")
                f.write(f"{'='*50}\n\n")
                
                for idx, item in enumerate(subject_content, 1):
                    f.write(f"{idx}. {item['topic']}\n")
                    f.write(f"   Video: {item['video_topic']}\n")
                    f.write(f"   Teacher: {item['teacher']}\n")
                    f.write(f"   Date: {item['date']}\n")
                    f.write(f"   Duration: {item['duration']}\n")
                    f.write(f"   URL: {item['url']}\n\n")
    
    await status.delete()
    
    if total_found > 0:
        await app.send_document(
            message.chat.id,
            document=output_file,
            caption=f"**✅ Found {total_found} videos for {selected_date}!**\n\n**Batch:** {batch_name}"
        )
    else:
        await message.reply_text(f"**⚠️ No content found for {selected_date}!**")
