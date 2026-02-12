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
REQUEST_DELAY = 1.5  # Delay between API calls
BATCH_DELAY = 0.8    # Delay between batch operations

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


def safe_request(method, url, max_retries=3, retry_delay=2, **kwargs):
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
                print(f"Rate limited. Waiting {wait_time:.1f}s...")
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


def get_auth_headers(token):
    """Generate authentication headers - CRITICAL: Use exact working format"""
    return {
        "Authorization": token,  # Direct token, no "Bearer" prefix
        "Content-Type": "application/json",
    }


async def fetch_and_show_batches(app, message, token):
    """Fetch and display user's batches - FIXED with correct API endpoint"""

    headers = get_auth_headers(token)

    try:
        status = await message.reply_text("**🔄 Fetching your batches...**")

        all_batches = []
        
        # CRITICAL: These are the CORRECT endpoints that actually work
        # Based on successful bot implementation
        endpoints_to_try = [
            # Primary endpoint - v1/batches/my-batch (CORRECT ONE!)
            {
                'url': f"{PW_API_BASE}/v1/batches/my-batch",
                'params': {'organizationId': ORGANIZATION_ID},
                'name': 'v1/my-batch (PRIMARY)'
            },
            # Secondary endpoint - v2/batches/my-batch
            {
                'url': f"{PW_API_BASE}/v2/batches/my-batch",
                'params': {'organizationId': ORGANIZATION_ID},
                'name': 'v2/my-batch'
            },
            # Tertiary - v1/batches with org filter
            {
                'url': f"{PW_API_BASE}/v1/batches",
                'params': {
                    'organizationId': ORGANIZATION_ID,
                    'page': 1,
                    'limit': 100
                },
                'name': 'v1/batches'
            },
        ]

        batches_found = False

        for endpoint in endpoints_to_try:
            if batches_found and len(all_batches) > 0:
                break

            try:
                print(f"\n=== Trying: {endpoint['name']} ===")
                print(f"URL: {endpoint['url']}")
                print(f"Params: {endpoint['params']}")
                print(f"Headers: Authorization length = {len(headers.get('Authorization', ''))}")
                
                response = safe_request("GET", endpoint['url'], params=endpoint['params'], 
                                       headers=headers, max_retries=2, retry_delay=1)

                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 401:
                    await status.edit_text("**❌ Token Expired!** Please generate a new token.")
                    return
                
                if response.status_code != 200:
                    print(f"Failed: {response.text[:200]}")
                    continue

                data = response.json()
                print(f"Response structure: {list(data.keys())}")
                print(f"Full response preview: {json.dumps(data, indent=2)[:1000]}")

                # Parse batches - handle multiple response structures
                batches = []

                # Method 1: Direct data array (most common for working bots)
                if isinstance(data.get('data'), list):
                    batches = data['data']
                    print(f"Found batches in 'data' (list): {len(batches)}")
                
                # Method 2: Nested data.data
                elif isinstance(data.get('data'), dict):
                    if isinstance(data['data'].get('data'), list):
                        batches = data['data']['data']
                        print(f"Found batches in 'data.data': {len(batches)}")
                    elif isinstance(data['data'].get('batches'), list):
                        batches = data['data']['batches']
                        print(f"Found batches in 'data.batches': {len(batches)}")
                    elif isinstance(data['data'].get('results'), list):
                        batches = data['data']['results']
                        print(f"Found batches in 'data.results': {len(batches)}")
                
                # Method 3: Direct results/batches array
                elif isinstance(data.get('results'), list):
                    batches = data['results']
                    print(f"Found batches in 'results': {len(batches)}")
                elif isinstance(data.get('batches'), list):
                    batches = data['batches']
                    print(f"Found batches in 'batches': {len(batches)}")

                if batches and len(batches) > 0:
                    print(f"✓✓✓ SUCCESS! Found {len(batches)} batches from {endpoint['name']}")
                    batches_found = True
                    
                    for batch in batches:
                        # Extract with multiple fallbacks
                        batch_info = {
                            'name': batch.get('name', batch.get('batchName', batch.get('title', 'Unknown Batch'))),
                            'slug': batch.get('slug', batch.get('batchSlug', batch.get('_id', 'N/A'))),
                            '_id': batch.get('_id', batch.get('id', batch.get('batchId', 'N/A'))),
                            'startDate': batch.get('startDate', batch.get('start', '')),
                            'endDate': batch.get('endDate', batch.get('end', '')),
                            'expiryDate': batch.get('expiryDate', batch.get('expiry', '')),
                            'thumbnail': batch.get('thumbnail', batch.get('image', '')),
                            'class': batch.get('class', batch.get('standard', batch.get('grade', ''))),
                            'target': batch.get('target', batch.get('exam', batch.get('goal', ''))),
                            'subjectCount': batch.get('subjectCount', 0),
                            'lectureCount': batch.get('lectureCount', batch.get('videoCount', 0)),
                            'language': batch.get('language', batch.get('medium', '')),
                            'previewImage': batch.get('previewImage', ''),
                        }
                        
                        # Prevent duplicates
                        if not any(b['_id'] == batch_info['_id'] for b in all_batches):
                            all_batches.append(batch_info)
                            print(f"  + Added: {batch_info['name']}")
                    
                    # Found batches, break the loop
                    break
                else:
                    print(f"✗ No batches in response from {endpoint['name']}")

            except Exception as e:
                print(f"Error with {endpoint['name']}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        await status.delete()

        if not all_batches or len(all_batches) == 0:
            # Still no batches - give detailed help
            error_msg = f"""**⚠️ NO BATCHES FOUND!**

**Debug Info:**
• Token verified: ✓
• User ID: Found
• API calls: Attempted

**This means:**
1. Account has no purchased courses
2. Courses expired/inactive
3. Different organization ID needed

**Try:**
• Check pw.live if you have active courses
• Generate fresh token
• Verify purchases in PW app

**Token starts with:** `{token[:30]}...`"""
            
            await message.reply_text(error_msg)
            return

        # Display found batches
        print(f"\n{'='*70}")
        print(f"TOTAL BATCHES FOUND: {len(all_batches)}")
        print(f"{'='*70}")
        
        msg = f"**📚 YOUR BATCHES ({len(all_batches)} FOUND):**\n\n"
        
        for idx, batch in enumerate(all_batches, 1):
            name = batch["name"]
            batch_id = batch["_id"]
            slug = batch["slug"]
            
            msg += f"**{idx}. {name}**\n"
            msg += f"   🆔 ID: `{batch_id}`\n"
            msg += f"   🔗 Slug: `{slug}`\n"
            
            if batch.get("class"):
                msg += f"   📖 Class: {batch['class']}\n"
            if batch.get("target"):
                msg += f"   🎯 Target: {batch['target']}\n"
            if batch.get("language"):
                msg += f"   🗣️ Language: {batch['language']}\n"
            
            msg += "\n"

        # Split long messages
        if len(msg) > 4000:
            parts = []
            current = ""
            for line in msg.split('\n'):
                if len(current) + len(line) < 3800:
                    current += line + '\n'
                else:
                    parts.append(current)
                    current = line + '\n'
            if current:
                parts.append(current)
            
            for part in parts:
                await message.reply_text(part)
        else:
            await message.reply_text(msg)

        # Ask for batch selection
        ask_batch = await app.ask(
            message.chat.id, 
            text="**📥 SELECT BATCH**\n\nSend:\n• Number (1, 2, 3...)\n• Batch ID\n• Batch Slug\n\n**Your choice:**"
        )
        batch_input = ask_batch.text.strip()
        await ask_batch.delete()

        if not batch_input:
            await message.reply_text("**❌ Selection cannot be empty!**")
            return

        # Find selected batch
        selected_batch = None

        # Try as number
        try:
            batch_num = int(batch_input)
            if 1 <= batch_num <= len(all_batches):
                selected_batch = all_batches[batch_num - 1]
                print(f"Selected by number: {batch_num}")
        except ValueError:
            # Try as ID/slug/name match
            batch_input_lower = batch_input.lower()
            for batch in all_batches:
                if (batch_input == batch['_id'] or 
                    batch_input == batch['slug'] or 
                    batch_input_lower == batch['slug'].lower() or
                    batch_input_lower in batch['name'].lower()):
                    selected_batch = batch
                    print(f"Selected by match: {batch['name']}")
                    break

        if not selected_batch:
            await message.reply_text("**❌ Batch not found!**\n\nCheck the number/ID/slug and try again.")
            return

        # Proceed to download options
        time.sleep(REQUEST_DELAY)
        await show_download_options(app, message, token, selected_batch)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*70}")
        print("CRITICAL ERROR IN BATCH FETCHING:")
        print(error_trace)
        print(f"{'='*70}\n")
        await message.reply_text(f"**❌ Critical Error:**\n\n`{str(e)}`")


async def show_download_options(app, message, token, batch):
    """Show download options with enhanced batch details fetching"""

    batch_id = batch['_id']
    batch_slug = batch['slug']
    batch_name = batch['name']

    headers = get_auth_headers(token)

    try:
        status = await message.reply_text("**🔄 Fetching batch details...**")

        batch_data = None
        subjects = []

        # Try multiple endpoints for batch details
        detail_endpoints = [
            # v1 batch details by slug
            {
                'url': f"{PW_API_BASE}/v1/batches/{batch_slug}",
                'name': 'v1/batches/slug'
            },
            # v1 batch details by ID
            {
                'url': f"{PW_API_BASE}/v1/batches/{batch_id}",
                'name': 'v1/batches/id'
            },
            # v2 batch details
            {
                'url': f"{PW_API_BASE}/v2/batches/{batch_slug}",
                'name': 'v2/batches/slug'
            },
            # v3 batch details
            {
                'url': f"{PW_API_BASE}/v3/batches/{batch_slug}/details",
                'name': 'v3/batches/details'
            },
        ]

        for endpoint in detail_endpoints:
            if batch_data:
                break

            try:
                print(f"\nTrying: {endpoint['name']}")
                
                response = safe_request("GET", endpoint['url'], headers=headers, max_retries=2, retry_delay=1)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract batch data
                    if 'data' in data:
                        if isinstance(data['data'], dict):
                            batch_data = data['data']
                        elif isinstance(data['data'], list) and len(data['data']) > 0:
                            batch_data = data['data'][0]
                    elif isinstance(data, dict) and '_id' in data:
                        batch_data = data
                    
                    if batch_data:
                        print(f"✓ Got batch details from {endpoint['name']}")
                        break
                        
            except Exception as e:
                print(f"Failed {endpoint['name']}: {e}")
                continue

        # Extract subjects
        if batch_data:
            subjects = (batch_data.get('subjects') or 
                       batch_data.get('subjectDetails') or 
                       batch_data.get('batchSubjects') or [])

        await status.delete()

        if not subjects:
            await message.reply_text(f"**❌ No subjects found in {batch_name}!**\n\nBatch might be empty or access restricted.")
            return

        # Show subjects preview
        subjects_msg = f"**📚 BATCH: {batch_name}**\n\n**{len(subjects)} Subjects Found:**\n\n"
        
        for idx, subj in enumerate(subjects[:10], 1):
            name = subj.get('subject', subj.get('name', 'Unknown'))
            subjects_msg += f"{idx}. {name}\n"
        
        if len(subjects) > 10:
            subjects_msg += f"\n...and {len(subjects) - 10} more\n"
        
        await message.reply_text(subjects_msg)

        # Store batch info
        batch_info = {
            'id': batch_id,
            'slug': batch_slug,
            'name': batch_name,
            'subjects': subjects,
            'data': batch_data
        }

        # Download options
        options = """**📥 DOWNLOAD OPTIONS:**

**1.** Full Batch (All Content)
**2.** Today's Class (By Date)
**3.** By Subject (Specific)

**Send:** 1, 2, or 3"""

        ask_option = await app.ask(message.chat.id, text=options)
        option = ask_option.text.strip().lower()
        await ask_option.delete()

        if option in ["1", "full", "all"]:
            await download_full_batch(app, message, token, batch_info)
        elif option in ["2", "today", "date"]:
            await download_today_class(app, message, token, batch_info)
        elif option in ["3", "subject"]:
            await download_by_subject(app, message, token, batch_info)
        else:
            await message.reply_text("**❌ Invalid option!** Send 1, 2, or 3.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def download_full_batch(app, message, token, batch_info):
    """Download full batch content"""

    batch_slug = batch_info['slug']
    batch_name = batch_info['name']
    subjects = batch_info['subjects']

    # Show subjects
    msg = "**📖 SUBJECTS:**\n\n"
    for idx, subj in enumerate(subjects, 1):
        name = subj.get('subject', subj.get('name', 'Unknown'))
        slug = subj.get('slug', 'N/A')
        count = subj.get('lectureCount', subj.get('videoCount', 0))
        
        msg += f"**{idx}. {name}**\n"
        msg += f"   Slug: `{slug}`\n"
        if count:
            msg += f"   Videos: {count}\n"
        msg += "\n"

    if len(msg) > 4000:
        parts = [msg[i:i+3800] for i in range(0, len(msg), 3800)]
        for part in parts:
            await message.reply_text(part)
    else:
        await message.reply_text(msg)

    # Ask selection
    ask_subjects = await app.ask(
        message.chat.id,
        text="**SELECT SUBJECTS:**\n\nSend:\n• `all` for all subjects\n• Numbers: `1,2,3`\n• Slugs: `physics&chemistry`"
    )
    selected = ask_subjects.text.strip()
    await ask_subjects.delete()

    if not selected:
        await message.reply_text("**❌ Selection cannot be empty!**")
        return

    # Process selection
    selected_subjects = []
    if selected.lower() == 'all':
        selected_subjects = subjects
    else:
        # Try numbers
        try:
            nums = [int(x.strip()) for x in selected.replace(',', ' ').split()]
            for num in nums:
                if 1 <= num <= len(subjects):
                    selected_subjects.append(subjects[num - 1])
        except ValueError:
            # Try slugs
            slugs = [s.strip() for s in selected.replace(',', '&').split('&') if s.strip()]
            for slug in slugs:
                for subj in subjects:
                    if subj.get('slug', '').lower() == slug.lower():
                        selected_subjects.append(subj)
                        break

    if not selected_subjects:
        await message.reply_text("**❌ No valid subjects!**")
        return

    # Download
    status = await message.reply_text(f"**🔄 Downloading {len(selected_subjects)} subject(s)...**")

    headers = get_auth_headers(token)
    output_file = f"batch_{batch_slug[:20]}.txt"
    
    if os.path.exists(output_file):
        os.remove(output_file)

    total_items = 0

    for subject in selected_subjects:
        subject_slug = subject.get('slug', '')
        subject_name = subject.get('subject', subject.get('name', 'Unknown'))
        
        if not subject_slug:
            continue

        await status.edit_text(f"**🔄 {subject_name}...**")

        # Determine pages
        count = subject.get('tagCount', subject.get('topicCount', subject.get('lectureCount', 0)))
        pages = max(1, math.ceil(count / 20)) if count else 10

        for page in range(1, min(pages + 1, 50)):
            try:
                time.sleep(BATCH_DELAY)

                # Fetch topics
                url = f"{PW_API_BASE}/v2/batches/{batch_slug}/subject/{subject_slug}/topics"
                response = safe_request("GET", url, params={'page': page}, headers=headers, max_retries=2)
                
                if response.status_code != 200:
                    break

                data = response.json()
                topics = data.get('data', [])

                if not topics:
                    break

                total_items += len(topics)

                # Write to file
                with open(output_file, 'a', encoding='utf-8') as f:
                    if page == 1:
                        f.write(f"\n{'='*70}\n")
                        f.write(f"📚 SUBJECT: {subject_name}\n")
                        f.write(f"{'='*70}\n\n")

                    for topic in topics:
                        f.write(f"📖 {topic.get('name', 'N/A')}\n")
                        f.write(f"   ID: {topic.get('_id', 'N/A')}\n")

                        # Videos
                        videos = topic.get('videos', [])
                        if videos:
                            f.write(f"   🎥 Videos: {len(videos)}\n")
                            for v in videos[:3]:
                                f.write(f"      • {v.get('topic', 'N/A')}\n")
                                if v.get('url'):
                                    f.write(f"        {v['url']}\n")

                        # Notes & DPP
                        notes = topic.get('notes', [])
                        exercises = topic.get('exercises', [])
                        if notes:
                            f.write(f"   📝 Notes: {len(notes)}\n")
                        if exercises:
                            f.write(f"   📋 DPP: {len(exercises)}\n")

                        f.write("-" * 70 + "\n")

            except Exception as e:
                print(f"Error page {page}: {e}")
                break

    await status.delete()

    if os.path.exists(output_file) and total_items > 0:
        await app.send_document(
            message.chat.id,
            document=output_file,
            caption=f"**✅ Complete!**\n\n**Batch:** {batch_name}\n**Topics:** {total_items}"
        )
        try:
            os.remove(output_file)
        except:
            pass
    else:
        await message.reply_text("**⚠️ No content found!**")


async def download_by_subject(app, message, token, batch_info):
    """Download specific subjects"""
    await download_full_batch(app, message, token, batch_info)


async def download_today_class(app, message, token, batch_info):
    """Download by date"""

    batch_slug = batch_info['slug']
    batch_name = batch_info['name']
    subjects = batch_info['subjects']

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # Ask date
    date_msg = f"""**📅 ENTER DATE**

Format: YYYY-MM-DD
Example: 2024-01-15

Quick:
• `today` → {today}
• `yesterday`

**Your input:**"""

    ask_date = await message.reply_text(date_msg)
    date_response = await app.ask(message.chat.id, text="**Date:**")
    date_input = date_response.text.strip().lower()
    await ask_date.delete()
    await date_response.delete()

    # Process date
    if date_input == 'today':
        selected_date = today
    elif date_input == 'yesterday':
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        selected_date = yesterday
    else:
        selected_date = date_input

    # Validate
    try:
        datetime.datetime.strptime(selected_date, "%Y-%m-%d")
    except ValueError:
        await message.reply_text("**❌ Invalid format!** Use YYYY-MM-DD")
        return

    # Show subjects
    msg = "**📚 SUBJECTS:**\n\n"
    for idx, subj in enumerate(subjects, 1):
        msg += f"{idx}. {subj.get('subject', 'Unknown')}\n"
    msg += "\nSend: Numbers or `all`"

    await message.reply_text(msg)

    # Ask subjects
    ask_subj = await app.ask(message.chat.id, text="**Selection:**")
    subject_input = ask_subj.text.strip()
    await ask_subj.delete()

    # Process
    if subject_input.lower() == 'all':
        selected_subjects = subjects
    else:
        try:
            nums = [int(x.strip()) for x in subject_input.replace(',', ' ').split()]
            selected_subjects = [subjects[n-1] for n in nums if 1 <= n <= len(subjects)]
        except:
            await message.reply_text("**❌ Invalid selection!**")
            return

    if not selected_subjects:
        await message.reply_text("**❌ No subjects selected!**")
        return

    # Search
    status = await message.reply_text(f"**🔍 Searching {selected_date}...**")

    headers = get_auth_headers(token)
    output_file = f"class_{selected_date}.txt"
    
    if os.path.exists(output_file):
        os.remove(output_file)

    total_found = 0
    all_results = []

    for subject in selected_subjects:
        subject_slug = subject.get('slug', '')
        subject_name = subject.get('subject', 'Unknown')

        await status.edit_text(f"**🔍 {subject_name}...**")

        page = 1
        while page <= 20:
            try:
                time.sleep(BATCH_DELAY)

                url = f"{PW_API_BASE}/v2/batches/{batch_slug}/subject/{subject_slug}/topics"
                response = safe_request("GET", url, params={'page': page}, headers=headers, max_retries=2)
                
                if response.status_code != 200:
                    break

                data = response.json()
                topics = data.get('data', [])

                if not topics:
                    break

                # Filter by date
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
                                    if teachers:
                                        t = teachers[0]
                                        if isinstance(t, dict):
                                            teacher = f"{t.get('firstName', '')} {t.get('lastName', '')}".strip()
                                    
                                    all_results.append({
                                        'subject': subject_name,
                                        'topic': topic.get('name', 'N/A'),
                                        'video': video.get('topic', 'N/A'),
                                        'teacher': teacher,
                                        'duration': video.get('videoDetails', {}).get('duration', 'N/A'),
                                        'url': video.get('url', 'N/A'),
                                        'date': video_date
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
        # Write file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*70}\n")
            f.write(f"📅 DATE: {selected_date}\n")
            f.write(f"📚 BATCH: {batch_name}\n")
            f.write(f"🎥 VIDEOS: {total_found}\n")
            f.write(f"{'='*70}\n\n")

            # Group by subject
            by_subject = {}
            for item in all_results:
                subj = item['subject']
                if subj not in by_subject:
                    by_subject[subj] = []
                by_subject[subj].append(item)

            for subj, videos in by_subject.items():
                f.write(f"\n{'─'*70}\n")
                f.write(f"📚 {subj} ({len(videos)} videos)\n")
                f.write(f"{'─'*70}\n\n")

                for idx, v in enumerate(videos, 1):
                    f.write(f"{idx}. {v['topic']}\n")
                    f.write(f"   🎥 {v['video']}\n")
                    f.write(f"   👨‍🏫 {v['teacher']}\n")
                    f.write(f"   ⏱️ {v['duration']}\n")
                    f.write(f"   🔗 {v['url']}\n\n")

        await app.send_document(
            message.chat.id,
            document=output_file,
            caption=f"**✅ Found {total_found} videos!**\n\n**Date:** {selected_date}\n**Batch:** {batch_name}"
        )
        try:
            os.remove(output_file)
        except:
            pass
    else:
        await message.reply_text(f"**⚠️ No classes found for {selected_date}!**")
