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

# Request delays
REQUEST_DELAY = 1
BATCH_DELAY = 0.5


def safe_request(method, url, max_retries=3, retry_delay=2, **kwargs):
    """Make HTTP request with retry logic"""
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=30, **kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, timeout=30, **kwargs)
            else:
                response = requests.request(method, url, timeout=30, **kwargs)

            if response.status_code == 429:
                wait_time = retry_delay * (attempt + 1)
                print(f"Rate limited. Waiting {wait_time}s...")
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

    headers = {
        "Content-Type": "application/json",
        "Client-Id": CLIENT_ID,
        "Client-Type": "WEB",
        "Client-Version": "6.0.0",
        "User-Agent": "Mozilla/5.0",
    }

    payload = {
        "username": phone_no,
        "countryCode": "+91",
        "organizationId": ORGANIZATION_ID,
    }

    try:
        response = safe_request("POST", url, params={"smsType": "0"}, headers=headers, json=payload)
        data = response.json()

        if response.status_code == 200:
            await message.reply_text("**✅ OTP Sent Successfully!**\n\nCheck your mobile.")
            return True
        else:
            error = data.get('message', 'Failed to send OTP')
            await message.reply_text(f"**❌ OTP Failed**\n\n`{error}`")
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

    headers = {
        "Content-Type": "application/json",
        "Randomid": "990963b2-aa95-4eba-9d64-56bb55fca9a9",
    }

    try:
        response = safe_request("POST", url, headers=headers, json=payload)
        data = response.json()

        if response.status_code == 200 and 'data' in data:
            token = data['data'].get('access_token')
            refresh = data['data'].get('refresh_token', '')
            return token, refresh
        else:
            error = data.get('message', 'Token generation failed')
            await message.reply_text(f"**❌ Failed**\n\n{error}")
            return None, None

    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")
        return None, None


async def pw_mobile(app, message):
    """Handle mobile-based login"""
    try:
        # Get phone number
        ask_phone = await app.ask(message.chat.id, text="**📱 Enter PW Mobile Number (10 digits)**")
        phone_no = ask_phone.text.strip()
        await ask_phone.delete()

        if not phone_no.isdigit() or len(phone_no) != 10:
            await message.reply_text("**❌ Invalid number!** Enter 10 digits.")
            return

        # Send OTP
        if not await get_otp(message, phone_no):
            return

        # Get OTP
        ask_otp = await app.ask(message.chat.id, text="**🔑 Enter OTP**")
        otp = ask_otp.text.strip()
        await ask_otp.delete()

        if not otp.isdigit():
            await message.reply_text("**❌ Invalid OTP!**")
            return

        # Generate token
        token, refresh = await get_token(message, phone_no, otp)

        if token:
            jwt_data = decode_jwt(token)
            user_data = jwt_data.get('data', {}) if jwt_data else {}

            msg = f"""**✅ LOGIN SUCCESS!**

**👤 Name:** `{user_data.get('firstName', '')} {user_data.get('lastName', '')}`
**📱 Mobile:** `{phone_no}`
**📧 Email:** `{user_data.get('email', 'N/A')}`

**🔐 TOKEN:**
`{token}`"""

            await message.reply_text(msg)

            time.sleep(REQUEST_DELAY)
            await fetch_and_show_batches(app, message, token)

    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def pw_token(app, message):
    """Handle token-based login"""
    try:
        ask_token = await app.ask(message.chat.id, text="**🔑 Enter PW Access Token**")
        token = ask_token.text.strip()
        await ask_token.delete()

        if not token:
            await message.reply_text("**❌ Token required!**")
            return

        status = await message.reply_text("**🔄 Verifying...**")

        jwt_data = decode_jwt(token)
        user_data = jwt_data.get('data', {}) if jwt_data else {}

        await status.delete()

        if user_data:
            msg = f"""**✅ TOKEN VERIFIED!**

**👤 Name:** `{user_data.get('firstName', '')} {user_data.get('lastName', '')}`
**📱 Mobile:** `{user_data.get('username', '')}`
**📧 Email:** `{user_data.get('email', 'N/A')}`
**🆔 ID:** `{user_data.get('_id', 'N/A')}`"""

            await message.reply_text(msg)

            time.sleep(REQUEST_DELAY)
            await fetch_and_show_batches(app, message, token)
        else:
            await message.reply_text("**❌ Invalid token!**")

    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def fetch_and_show_batches(app, message, token):
    """Fetch and display batches - WORKING VERSION"""
    
    try:
        status = await message.reply_text("**🔄 Fetching batches...**")

        # CORRECT HEADERS - Minimal and working
        headers = {
            "Authorization": token,  # Direct token
            "Content-Type": "application/json",
        }

        all_batches = []

        # Try multiple working endpoints
        endpoints = [
            # Primary - v1/batches/my-batch (WORKS!)
            {
                'url': f"{PW_API_BASE}/v1/batches/my-batch",
                'params': {'organizationId': ORGANIZATION_ID}
            },
            # Secondary - v2
            {
                'url': f"{PW_API_BASE}/v2/batches/my-batch",
                'params': {'organizationId': ORGANIZATION_ID}
            },
            # Tertiary - direct batches
            {
                'url': f"{PW_API_BASE}/v1/batches",
                'params': {
                    'organizationId': ORGANIZATION_ID,
                    'page': 1,
                    'limit': 100
                }
            },
        ]

        for endpoint in endpoints:
            try:
                print(f"\nTrying: {endpoint['url']}")
                
                response = safe_request("GET", endpoint['url'], 
                                       params=endpoint['params'],
                                       headers=headers,
                                       max_retries=2,
                                       retry_delay=1)

                print(f"Status: {response.status_code}")

                if response.status_code == 401:
                    await status.edit_text("**❌ Token expired!** Generate new token.")
                    return

                if response.status_code != 200:
                    print(f"Failed: {response.text[:100]}")
                    continue

                data = response.json()
                print(f"Keys: {list(data.keys())}")

                # Extract batches
                batches = []
                
                if isinstance(data.get('data'), list):
                    batches = data['data']
                elif isinstance(data.get('data'), dict):
                    if isinstance(data['data'].get('data'), list):
                        batches = data['data']['data']
                    elif isinstance(data['data'].get('batches'), list):
                        batches = data['data']['batches']
                    elif isinstance(data['data'].get('results'), list):
                        batches = data['data']['results']

                if batches:
                    print(f"✓ Found {len(batches)} batches!")
                    
                    for batch in batches:
                        batch_info = {
                            'name': batch.get('name', batch.get('batchName', 'Unknown')),
                            'slug': batch.get('slug', batch.get('_id', 'N/A')),
                            '_id': batch.get('_id', batch.get('id', 'N/A')),
                            'class': batch.get('class', ''),
                            'language': batch.get('language', ''),
                        }
                        
                        # Avoid duplicates
                        if not any(b['_id'] == batch_info['_id'] for b in all_batches):
                            all_batches.append(batch_info)
                    
                    break  # Found batches, stop trying

            except Exception as e:
                print(f"Error: {e}")
                continue

        await status.delete()

        if not all_batches:
            await message.reply_text("**⚠️ No batches found!**\n\nCheck:\n• Active subscriptions\n• Token validity\n• Account on pw.live")
            return

        # Display batches
        msg = f"**📚 YOUR BATCHES ({len(all_batches)}):**\n\n"
        
        for idx, batch in enumerate(all_batches, 1):
            msg += f"**{idx}. {batch['name']}**\n"
            msg += f"   ID: `{batch['_id']}`\n"
            msg += f"   Slug: `{batch['slug']}`\n"
            if batch.get('class'):
                msg += f"   Class: {batch['class']}\n"
            if batch.get('language'):
                msg += f"   Lang: {batch['language']}\n"
            msg += "\n"

        # Split if too long
        if len(msg) > 4000:
            parts = [msg[i:i+3900] for i in range(0, len(msg), 3900)]
            for part in parts:
                await message.reply_text(part)
        else:
            await message.reply_text(msg)

        # Ask selection
        ask_batch = await app.ask(message.chat.id, text="**📥 Send batch number (1,2,3...) or ID/Slug**")
        batch_input = ask_batch.text.strip()
        await ask_batch.delete()

        if not batch_input:
            await message.reply_text("**❌ Selection required!**")
            return

        # Find batch
        selected_batch = None

        try:
            num = int(batch_input)
            if 1 <= num <= len(all_batches):
                selected_batch = all_batches[num - 1]
        except ValueError:
            for batch in all_batches:
                if (batch_input == batch['_id'] or 
                    batch_input == batch['slug'] or
                    batch_input.lower() in batch['name'].lower()):
                    selected_batch = batch
                    break

        if not selected_batch:
            await message.reply_text("**❌ Batch not found!**")
            return

        time.sleep(REQUEST_DELAY)
        await show_download_options(app, message, token, selected_batch)

    except Exception as e:
        import traceback
        traceback.print_exc()
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def show_download_options(app, message, token, batch):
    """Show download options"""
    
    batch_id = batch['_id']
    batch_slug = batch['slug']
    batch_name = batch['name']

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    try:
        status = await message.reply_text("**🔄 Loading batch...**")

        # Get batch details
        batch_data = None
        subjects = []

        urls_to_try = [
            f"{PW_API_BASE}/v1/batches/{batch_slug}",
            f"{PW_API_BASE}/v1/batches/{batch_id}",
            f"{PW_API_BASE}/v2/batches/{batch_slug}",
        ]

        for url in urls_to_try:
            try:
                response = safe_request("GET", url, headers=headers, max_retries=2)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data:
                        batch_data = data['data'] if isinstance(data['data'], dict) else data
                    else:
                        batch_data = data
                    
                    if batch_data:
                        break
            except:
                continue

        if batch_data:
            subjects = (batch_data.get('subjects') or 
                       batch_data.get('subjectDetails') or [])

        await status.delete()

        if not subjects:
            await message.reply_text(f"**❌ No subjects in {batch_name}!**")
            return

        # Show preview
        msg = f"**📚 {batch_name}**\n\n**Subjects ({len(subjects)}):**\n\n"
        for idx, subj in enumerate(subjects[:8], 1):
            msg += f"{idx}. {subj.get('subject', subj.get('name', 'Unknown'))}\n"
        if len(subjects) > 8:
            msg += f"\n...and {len(subjects)-8} more\n"

        await message.reply_text(msg)

        batch_info = {
            'id': batch_id,
            'slug': batch_slug,
            'name': batch_name,
            'subjects': subjects
        }

        # Options
        options = """**📥 Download Options:**

1. Full Batch
2. By Date
3. By Subject

**Send: 1, 2, or 3**"""

        ask_opt = await app.ask(message.chat.id, text=options)
        opt = ask_opt.text.strip()
        await ask_opt.delete()

        if opt in ["1", "full", "all"]:
            await download_full_batch(app, message, token, batch_info)
        elif opt in ["2", "date", "today"]:
            await download_by_date(app, message, token, batch_info)
        elif opt in ["3", "subject"]:
            await download_by_subject(app, message, token, batch_info)
        else:
            await message.reply_text("**❌ Invalid option!**")

    except Exception as e:
        traceback.print_exc()
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def download_full_batch(app, message, token, batch_info):
    """Download full batch"""
    
    batch_slug = batch_info['slug']
    batch_name = batch_info['name']
    subjects = batch_info['subjects']

    # Show subjects
    msg = "**📖 Subjects:**\n\n"
    for idx, subj in enumerate(subjects, 1):
        name = subj.get('subject', subj.get('name', 'Unknown'))
        msg += f"{idx}. {name}\n"

    await message.reply_text(msg)

    # Ask selection
    ask_subj = await app.ask(message.chat.id, text="**Send numbers (1,2,3) or 'all':**")
    selection = ask_subj.text.strip()
    await ask_subj.delete()

    if selection.lower() == 'all':
        selected = subjects
    else:
        try:
            nums = [int(x.strip()) for x in selection.split(',')]
            selected = [subjects[n-1] for n in nums if 1 <= n <= len(subjects)]
        except:
            await message.reply_text("**❌ Invalid selection!**")
            return

    if not selected:
        await message.reply_text("**❌ No subjects selected!**")
        return

    # Download
    status = await message.reply_text(f"**🔄 Downloading...**")

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    output_file = f"batch_{batch_slug[:15]}.txt"
    if os.path.exists(output_file):
        os.remove(output_file)

    total = 0

    for subject in selected:
        subject_slug = subject.get('slug', '')
        subject_name = subject.get('subject', subject.get('name', 'Unknown'))

        if not subject_slug:
            continue

        await status.edit_text(f"**🔄 {subject_name}...**")

        page = 1
        while page <= 50:
            try:
                time.sleep(BATCH_DELAY)

                url = f"{PW_API_BASE}/v2/batches/{batch_slug}/subject/{subject_slug}/topics"
                response = safe_request("GET", url, params={'page': page}, headers=headers)

                if response.status_code != 200:
                    break

                data = response.json()
                topics = data.get('data', [])

                if not topics:
                    break

                total += len(topics)

                with open(output_file, 'a', encoding='utf-8') as f:
                    if page == 1:
                        f.write(f"\n{'='*60}\n")
                        f.write(f"SUBJECT: {subject_name}\n")
                        f.write(f"{'='*60}\n\n")

                    for topic in topics:
                        f.write(f"📖 {topic.get('name', 'N/A')}\n")
                        f.write(f"   ID: {topic.get('_id', 'N/A')}\n")

                        videos = topic.get('videos', [])
                        if videos:
                            f.write(f"   Videos: {len(videos)}\n")
                            for v in videos[:3]:
                                f.write(f"   • {v.get('topic', 'N/A')}\n")
                                if v.get('url'):
                                    f.write(f"     {v['url']}\n")

                        notes = topic.get('notes', [])
                        if notes:
                            f.write(f"   Notes: {len(notes)}\n")

                        f.write("-" * 60 + "\n")

                page += 1

            except Exception as e:
                print(f"Error: {e}")
                break

    await status.delete()

    if os.path.exists(output_file) and total > 0:
        await app.send_document(
            message.chat.id,
            document=output_file,
            caption=f"**✅ Complete!**\n\n{batch_name}\nTopics: {total}"
        )
        try:
            os.remove(output_file)
        except:
            pass
    else:
        await message.reply_text("**⚠️ No content found!**")


async def download_by_subject(app, message, token, batch_info):
    """Same as full batch"""
    await download_full_batch(app, message, token, batch_info)


async def download_by_date(app, message, token, batch_info):
    """Download by date"""
    
    batch_slug = batch_info['slug']
    batch_name = batch_info['name']
    subjects = batch_info['subjects']

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # Ask date
    ask_date = await app.ask(message.chat.id, text=f"**📅 Enter date (YYYY-MM-DD)**\n\nToday: {today}\nOr send 'today'")
    date_input = ask_date.text.strip().lower()
    await ask_date.delete()

    if date_input == 'today':
        selected_date = today
    else:
        selected_date = date_input

    try:
        datetime.datetime.strptime(selected_date, "%Y-%m-%d")
    except:
        await message.reply_text("**❌ Invalid date! Use YYYY-MM-DD**")
        return

    # Show subjects
    msg = "**📚 Subjects:**\n\n"
    for idx, subj in enumerate(subjects, 1):
        msg += f"{idx}. {subj.get('subject', 'Unknown')}\n"

    await message.reply_text(msg)

    # Ask subjects
    ask_subj = await app.ask(message.chat.id, text="**Send numbers or 'all':**")
    subj_input = ask_subj.text.strip()
    await ask_subj.delete()

    if subj_input.lower() == 'all':
        selected = subjects
    else:
        try:
            nums = [int(x.strip()) for x in subj_input.split(',')]
            selected = [subjects[n-1] for n in nums if 1 <= n <= len(subjects)]
        except:
            await message.reply_text("**❌ Invalid!**")
            return

    if not selected:
        await message.reply_text("**❌ No subjects!**")
        return

    # Search
    status = await message.reply_text(f"**🔍 Searching {selected_date}...**")

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    output_file = f"class_{selected_date}.txt"
    if os.path.exists(output_file):
        os.remove(output_file)

    total_found = 0
    results = []

    for subject in selected:
        subject_slug = subject.get('slug', '')
        subject_name = subject.get('subject', 'Unknown')

        await status.edit_text(f"**🔍 {subject_name}...**")

        page = 1
        while page <= 15:
            try:
                time.sleep(BATCH_DELAY)

                url = f"{PW_API_BASE}/v2/batches/{batch_slug}/subject/{subject_slug}/topics"
                response = safe_request("GET", url, params={'page': page}, headers=headers)

                if response.status_code != 200:
                    break

                data = response.json()
                topics = data.get('data', [])

                if not topics:
                    break

                for topic in topics:
                    videos = topic.get('videos', [])
                    for video in videos:
                        video_date = video.get('date', '')
                        if video_date:
                            try:
                                v_date = video_date.split('T')[0] if 'T' in video_date else video_date[:10]
                                if v_date == selected_date:
                                    teachers = video.get('teachers', [])
                                    teacher = 'Unknown'
                                    if teachers and isinstance(teachers[0], dict):
                                        t = teachers[0]
                                        teacher = f"{t.get('firstName', '')} {t.get('lastName', '')}".strip()

                                    results.append({
                                        'subject': subject_name,
                                        'topic': topic.get('name', 'N/A'),
                                        'video': video.get('topic', 'N/A'),
                                        'teacher': teacher,
                                        'url': video.get('url', 'N/A'),
                                        'duration': video.get('videoDetails', {}).get('duration', 'N/A'),
                                    })
                                    total_found += 1
                            except:
                                pass

                page += 1

            except Exception as e:
                print(f"Error: {e}")
                break

    await status.delete()

    if total_found > 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*60}\n")
            f.write(f"DATE: {selected_date}\n")
            f.write(f"BATCH: {batch_name}\n")
            f.write(f"VIDEOS: {total_found}\n")
            f.write(f"{'='*60}\n\n")

            by_subj = {}
            for r in results:
                s = r['subject']
                if s not in by_subj:
                    by_subj[s] = []
                by_subj[s].append(r)

            for subj, vids in by_subj.items():
                f.write(f"\n{subj} ({len(vids)} videos)\n")
                f.write(f"{'-'*60}\n\n")

                for idx, v in enumerate(vids, 1):
                    f.write(f"{idx}. {v['topic']}\n")
                    f.write(f"   Video: {v['video']}\n")
                    f.write(f"   Teacher: {v['teacher']}\n")
                    f.write(f"   Duration: {v['duration']}\n")
                    f.write(f"   URL: {v['url']}\n\n")

        await app.send_document(
            message.chat.id,
            document=output_file,
            caption=f"**✅ Found {total_found} videos!**\n\nDate: {selected_date}"
        )
        try:
            os.remove(output_file)
        except:
            pass
    else:
        await message.reply_text(f"**⚠️ No classes on {selected_date}!**")
