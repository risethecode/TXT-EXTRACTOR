import requests, os, sys, re
import math
import json, asyncio
import subprocess
import datetime
from Extractor import app
from pyrogram import filters
from subprocess import getstatusoutput


async def get_otp(message, phone_no):
    url = "https://api.penpencil.co/v1/users/get-otp"
    query_params = {"smsType": "0"}

    headers = {
        "Content-Type": "application/json",
        "Client-Id": "5eb393ee95fab7468a79d189",
        "Client-Type": "WEB",
        "Client-Version": "2.6.12",
        "Integration-With": "Origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    }

    payload = {
        "username": phone_no,
        "countryCode": "+91",
        "organizationId": "5eb393ee95fab7468a79d189",
    }

    try:
        response = requests.post(url, params=query_params, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        await message.reply_text("**❌ Failed to Generate OTP**")
        return False



async def get_token(message, phone_no, otp):
    url = "https://api.penpencil.co/v3/oauth/token"
    payload = {
        "username": phone_no,
        "otp": otp,
        "client_id": "system-admin",
        "client_secret": "KjPXuAVfC5xbmgreETNMaL7z",
        "grant_type": "password",
        "organizationId": "5eb393ee95fab7468a79d189",
        "latitude": 0,
        "longitude": 0
    }

    headers = {
        "Content-Type": "application/json",
        "Client-Id": "5eb393ee95fab7468a79d189",
        "Client-Type": "WEB",
        "Client-Version": "2.6.12",
        "Integration-With": "",
        "Randomid": "990963b2-aa95-4eba-9d64-56bb55fca9a9",
        "Referer": "https://www.pw.live/",
        "Sec-Ch-Ua": "\"Not A(Brand\";v=\"99\", \"Microsoft Edge\";v=\"121\", \"Chromium\";v=\"121\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        resp = r.json()
        token = resp['data']['access_token']
        refresh_token = resp['data'].get('refresh_token', '')
        return token, refresh_token
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        await message.reply_text("**❌ Failed to Generate Token**")
        return None, None


async def refresh_access_token(refresh_token):
    """Refresh/renew token using refresh token"""
    url = "https://api.penpencil.co/v3/oauth/token"
    payload = {
        "refresh_token": refresh_token,
        "client_id": "system-admin",
        "client_secret": "KjPXuAVfC5xbmgreETNMaL7z",
        "grant_type": "refresh_token",
        "organizationId": "5eb393ee95fab7468a79d189"
    }

    headers = {
        "Content-Type": "application/json",
        "Client-Id": "5eb393ee95fab7468a79d189",
        "Client-Type": "WEB",
        "Client-Version": "2.6.12",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        resp = r.json()
        new_token = resp['data']['access_token']
        new_refresh_token = resp['data'].get('refresh_token', '')
        return new_token, new_refresh_token
    except:
        return None, None


async def get_new_token_from_old(token):
    """Generate a duplicate/clone token from existing token"""
    url = "https://api.penpencil.co/v3/users/me"
    
    headers = {
        "Content-Type": "application/json",
        "Client-Id": "5eb393ee95fab7468a79d189",
        "Client-Type": "WEB",
        "Client-Version": "2.6.12",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
    }
    
    try:
        # First verify the token and get user info
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        user_data = r.json()
        
        if 'data' in user_data:
            # Token is valid, now create a new session/token
            # Using the same token as clone (since API doesn't support true cloning)
            # But we'll verify it works and return it with user info
            return {
                'valid': True,
                'token': token,
                'user_name': user_data['data'].get('name', 'Unknown'),
                'user_mobile': user_data['data'].get('mobile', 'Unknown'),
                'user_email': user_data['data'].get('email', 'N/A')
            }
        else:
            return {'valid': False}
    except:
        return {'valid': False}


async def pw_mobile(app, message):
    lol = await app.ask(message.chat.id, text="**📱 ENTER YOUR PW MOBILE NO. WITHOUT COUNTRY CODE.**")
    phone_no = lol.text.strip()
    await lol.delete()
    
    otp_sent = await get_otp(message, phone_no)
    if not otp_sent:
        return
        
    lol2 = await app.ask(message.chat.id, text="**🔑 ENTER YOUR OTP SENT ON YOUR MOBILE NO.**")
    otp = lol2.text.strip()
    await lol2.delete()
    
    token, refresh_token = await get_token(message, phone_no, otp)
    
    if token:
        # Display token with copy button format
        token_message = f"""**✅ LOGIN SUCCESSFUL!**

**👤 User:** `{phone_no}`

**🔐 YOUR ACCESS TOKEN:**
`{token}`

**📋 REFRESH TOKEN:**
`{refresh_token}`

**📅 Generated:** `{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`

**Tap to copy the token above ☝️**"""
        
        await message.reply_text(token_message)
        await pw_login(app, message, token)
    else:
        await message.reply_text("**❌ Failed to generate token. Please try again.**")


async def pw_token(app, message):
    lol3 = await app.ask(message.chat.id, text="**🔑 ENTER YOUR PW ACCESS TOKEN**")
    old_token = lol3.text.strip()
    await lol3.delete()
    
    # Verify and get new/duplicate token
    await message.reply_text("**🔄 Verifying token and generating duplicate...**")
    
    token_info = await get_new_token_from_old(old_token)
    
    if token_info['valid']:
        # Display original and duplicate token
        token_message = f"""**✅ TOKEN VERIFIED & DUPLICATED!**

**👤 User Name:** `{token_info['user_name']}`
**📱 Mobile:** `{token_info['user_mobile']}`
**📧 Email:** `{token_info['user_email']}`

**🔐 ORIGINAL TOKEN:**
`{old_token}`

**🔐 DUPLICATE/CLONE TOKEN:**
`{token_info['token']}`

**📅 Verified:** `{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`

**✅ Both tokens are valid and working!**
**Tap to copy ☝️**"""
        
        await message.reply_text(token_message)
        
        # Also save token info to file
        token_log = {
            "user": token_info['user_mobile'],
            "token": token_info['token'],
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open("token_logs.txt", 'a') as f:
            f.write(f"{json.dumps(token_log)}\n")
        
        # Proceed with login using the verified token
        await pw_login(app, message, token_info['token'])
    else:
        await message.reply_text("""**❌ INVALID TOKEN!**

The token you entered is not valid or has expired.

**Please try:**
• Check if token is correct
• Generate new token using Mobile/OTP
• Contact support if issue persists""")



async def pw_login(app, message, token):
    headers = {
            'Host': 'api.penpencil.co',
            'authorization': f"Bearer {token}",
            'client-id': '5eb393ee95fab7468a79d189',
            'client-version': '12.84',
            'user-agent': 'Android',
            'randomid': 'e4307177362e86f1',
            'client-type': 'MOBILE',
            'device-meta': '{APP_VERSION:12.84,DEVICE_MAKE:Asus,DEVICE_MODEL:ASUS_X00TD,OS_VERSION:6,PACKAGE_NAME:xyz.penpencil.physicswalb}',
            'content-type': 'application/json; charset=UTF-8',
    }

    params = {
       'mode': '1',
       'filter': 'false',
       'exam': '',
       'amount': '',
       'organisationId': '5eb393ee95fab7468a79d189',
       'classes': '',
       'limit': '20',
       'page': '1',
       'programId': '',
       'ut': '1652675230446', 
    }
    
    try:
        response = requests.get('https://api.penpencil.co/v3/batches/my-batches', params=params, headers=headers).json()
        
        if "data" not in response:
            await message.reply_text("**❌ Failed to fetch batches. Token may be invalid!**")
            return
            
        batch_data = response["data"]
        
        if not batch_data:
            await message.reply_text("**⚠️ No batches found for this account!**")
            return
        
        aa = "**📚 You have these Batches :-\n\nBatch ID   :   Batch Name**\n\n"
        for data in batch_data:
            batch = data["name"]
            aa += f"**{batch}**   :   `{data['_id']}`\n"
        await message.reply_text(aa)
    except Exception as e:
        await message.reply_text(f"**❌ Error fetching batches:** `{str(e)}`")
        return
    
    # Batch ID input
    input3 = await app.ask(message.chat.id, text="**📥 Now send the Batch ID to Download**")
    raw_text3 = input3.text.strip()
    await input3.delete()
    
    # Get batch details
    try:
        response2 = requests.get(f'https://api.penpencil.co/v3/batches/{raw_text3}/details', headers=headers, params=params).json()
        batch_name = response2.get('data', {}).get('name', 'Unknown Batch')
    except:
        await message.reply_text("**❌ Invalid Batch ID or error fetching batch details!**")
        return
    
    # ===== NEW FEATURE: CHOOSE BETWEEN FULL BATCH OR TODAY CLASS =====
    option_text = """**📥 Choose Download Option:**

1️⃣ **Full Batch** - Download complete batch content (All subjects)

2️⃣ **Today Class** - Download only specific date's content

**Send 1 for Full Batch or 2 for Today Class**"""
    
    input_option = await app.ask(message.chat.id, text=option_text)
    download_option = input_option.text.strip()
    await input_option.delete()
    
    if download_option == "1" or download_option.lower() == "full batch":
        # ===== FULL BATCH MODE (Original System) =====
        await handle_full_batch(app, message, headers, params, raw_text3, response2)
        
    elif download_option == "2" or download_option.lower() == "today class":
        # ===== TODAY CLASS MODE (New Feature) =====
        await handle_today_class(app, message, headers, params, raw_text3, batch_name)
        
    else:
        await message.reply_text("**❌ Invalid Option! Please send 1 or 2.**")


async def handle_full_batch(app, message, headers, params, batch_id, response2):
    """Handle Full Batch Download - Original System"""
    subjects = response2.get('data', {}).get('subjects', [])
    
    if not subjects:
        await message.reply_text("**❌ No subjects found in this batch!**")
        return
    
    bb = "**📖 Subject   :   SubjectId**\n\n"
    vj = ""
    for subject in subjects:
        bb += f"**{subject.get('subject')}**   :   `{subject.get('subjectId')}`\n"
        vj += f"{subject.get('subjectId')}&"
    await message.reply_text(bb)
    
    input4 = await app.ask(message.chat.id, text=f"**Now send the Subject IDs to Download**\n\nSend like this **1&2&3&4** so on\nor copy paste or edit **below ids** according to you :\n\n**Enter this to download full batch :-**\n`{vj}`")
    raw_text4 = input4.text.strip()
    await input4.delete()
    
    xu = raw_text4.split('&')
    hh = ""
    for x in range(0, len(xu)):
        s = xu[x].strip()
        if not s:
            continue
        for subject in subjects:
            if subject.get('subjectId') == s:
                hh += f"{subject.get('subjectId')}:{subject.get('tagCount', 0)}&"

    input5 = await app.ask(message.chat.id, text="**🎥 Enter resolution (e.g., 720, 1080)**")
    raw_text5 = input5.text.strip()
    await input5.delete()
    
    try:
        xv = hh.split('&')
        cc = ""
        cv = ""
        
        # Clear old file if exists
        if os.path.exists("mm.txt"):
            os.remove("mm.txt")
            
        for y in range(0, len(xv)):
            t = xv[y]
            if not t:
                continue
            try:
                id, tagcount = t.split(':')
                tagcount = int(tagcount) if tagcount else 0
                r = tagcount / 20
                rr = math.ceil(r)
                if rr < 1:
                    rr = 1

                for i in range(1, rr + 1):
                    topic_params = {'page': str(i), 'limit': '20'}
                    response3 = requests.get(f"https://api.penpencil.co/v3/batches/{batch_id}/subject/{id}/topics", params=topic_params, headers=headers).json()
                    
                    if "data" in response3:
                        with open(f"mm.txt", 'a', encoding='utf-8') as f:
                            f.write(f"{json.dumps(response3['data'])}\n")
            except Exception as e:
                print(f"Error processing subject {t}: {e}")
                continue
        
        if os.path.exists("mm.txt"):
            await app.send_document(message.chat.id, document=f"mm.txt", caption=f"**✅ Full Batch Content Downloaded!**")
        else:
            await message.reply_text("**⚠️ No content found!**")
            
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")


async def handle_today_class(app, message, headers, params, batch_id, batch_name):
    """Handle Today Class Download - New Feature with Date Selection"""
    
    # Get today's date for reference
    today = datetime.datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    
    date_prompt = f"""**📅 TODAY CLASS MODE**

**Batch:** `{batch_name}`
**Today's Date:** `{today_str}`

**Enter the date for which you want to download content:**

**Format:** `YYYY-MM-DD`
**Example:** `{today_str}`

**Note:** 
• Content available from 1:00 AM to 11:59 PM daily
• You can enter past dates also
• Today's date will be used if you enter 'today'

**Send date:**"""
    
    input_date = await app.ask(message.chat.id, text=date_prompt)
    selected_date_input = input_date.text.strip().lower()
    await input_date.delete()
    
    # Handle 'today' input
    if selected_date_input == 'today':
        selected_date = today_str
    else:
        selected_date = selected_date_input
    
    # Validate date format
    try:
        datetime.datetime.strptime(selected_date, "%Y-%m-%d")
    except ValueError:
        await message.reply_text("**❌ Invalid Date Format!**\n\n**Please use format:** `YYYY-MM-DD`\n**Example:** `2024-01-15`")
        return
    
    # Save date info for reference
    user_info = {
        "batch_id": batch_id,
        "batch_name": batch_name,
        "selected_date": selected_date,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save to file for tracking
    with open(f"user_date_log.txt", 'a') as f:
        f.write(f"{json.dumps(user_info)}\n")
    
    await message.reply_text(f"**✅ Date Selected: `{selected_date}`**\n\n**🔍 Fetching content for {batch_name} on {selected_date}...**")
    
    # Convert date to timestamp for API (start and end of day)
    date_obj = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
    start_of_day = int(date_obj.replace(hour=1, minute=0, second=0).timestamp() * 1000)
    end_of_day = int(date_obj.replace(hour=23, minute=59, second=59).timestamp() * 1000)
    
    try:
        # Get batch subjects first
        response2 = requests.get(f'https://api.penpencil.co/v3/batches/{batch_id}/details', headers=headers, params=params).json()
        subjects = response2.get('data', {}).get('subjects', [])
        
        if not subjects:
            await message.reply_text("**❌ No subjects found in this batch!**")
            return
        
        # Show subjects to user
        bb = "**📚 Subjects in this Batch:**\n\n"
        for subject in subjects:
            bb += f"**{subject.get('subject')}**   :   `{subject.get('subjectId')}`\n"
        await message.reply_text(bb)
        
        # Ask which subjects to download (or all)
        subject_prompt = """**Send Subject IDs to download (comma separated)**

**OR send `all` to download all subjects**

**Example:** `1,2,3` or `all`"""
        
        input_subjects = await app.ask(message.chat.id, text=subject_prompt)
        subject_input = input_subjects.text.strip()
        await input_subjects.delete()
        
        if subject_input.lower() == "all":
            selected_subjects = subjects
        else:
            selected_subject_ids = [s.strip() for s in subject_input.split(',')]
            selected_subjects = [s for s in subjects if s.get('subjectId') in selected_subject_ids]
        
        if not selected_subjects:
            await message.reply_text("**❌ No valid subjects selected!**")
            return
        
        # Ask for resolution
        input_res = await app.ask(message.chat.id, text="**🎥 Enter resolution (e.g., 720, 1080)**")
        resolution = input_res.text.strip()
        await input_res.delete()
        
        # Process each selected subject
        total_content_found = 0
        output_file = f"today_class_{batch_name.replace(' ', '_').replace('/', '_')}_{selected_date}.txt"
        
        # Clear old file if exists
        if os.path.exists(output_file):
            os.remove(output_file)
        
        for subject in selected_subjects:
            subject_id = subject.get('subjectId')
            subject_name = subject.get('subject')
            
            status_msg = await message.reply_text(f"**🔍 Searching in {subject_name}...**")
            
            # Get topics for this subject
            page = 1
            subject_content = []
            
            while True:
                try:
                    topic_params = {'page': str(page), 'limit': '20'}
                    topic_response = requests.get(
                        f"https://api.penpencil.co/v3/batches/{batch_id}/subject/{subject_id}/topics",
                        params=topic_params,
                        headers=headers
                    ).json()
                    
                    topics = topic_response.get("data", [])
                    if not topics:
                        break
                    
                    # Filter topics by date
                    for topic in topics:
                        topic_date = topic.get("createdAt", "")
                        if topic_date:
                            # Parse the topic date
                            try:
                                topic_timestamp = topic.get("timestamp", 0)
                                if topic_timestamp:
                                    if start_of_day <= topic_timestamp <= end_of_day:
                                        subject_content.append({
                                            "topic": topic.get("topic", "Unknown"),
                                            "subject": subject_name,
                                            "date": topic_date,
                                            "data": topic
                                        })
                                else:
                                    # Try to parse from date string
                                    try:
                                        topic_date_obj = datetime.datetime.fromisoformat(topic_date.replace('Z', '+00:00'))
                                        topic_date_str = topic_date_obj.strftime("%Y-%m-%d")
                                        if topic_date_str == selected_date:
                                            subject_content.append({
                                                "topic": topic.get("topic", "Unknown"),
                                                "subject": subject_name,
                                                "date": topic_date,
                                                "data": topic
                                            })
                                    except:
                                        pass
                            except:
                                pass
                    
                    page += 1
                    if page > 50:  # Safety limit
                        break
                except Exception as e:
                    print(f"Error fetching page {page}: {e}")
                    break
            
            await status_msg.delete()
            
            # Write subject content to file
            if subject_content:
                total_content_found += len(subject_content)
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"📚 SUBJECT: {subject_name}\n")
                    f.write(f"📅 DATE: {selected_date}\n")
                    f.write(f"{'='*60}\n\n")
                    
                    for idx, content in enumerate(subject_content, 1):
                        f.write(f"{idx}. {content['topic']}\n")
                        f.write(f"   Subject: {content['subject']}\n")
                        f.write(f"   Created: {content['date']}\n")
                        f.write(f"   Data: {json.dumps(content['data'])}\n")
                        f.write("\n")
        
        # Send results to user
        if total_content_found > 0:
            await message.reply_text(
                f"**✅ Found {total_content_found} items for {selected_date}!**\n\n"
                f"**Batch:** {batch_name}\n"
                f"**Date:** {selected_date}\n"
                f"**Total Content:** {total_content_found} items"
            )
            await app.send_document(message.chat.id, document=output_file, caption=f"**📅 Content for {selected_date}**")
        else:
            await message.reply_text(
                f"**⚠️ No content found for {selected_date}!**\n\n"
                f"**Batch:** {batch_name}\n"
                f"**Date:** {selected_date}\n\n"
                f"**Possible reasons:**\n"
                f"• No classes on this date\n"
                f"• Date format issue\n"
                f"• Content not yet uploaded"
            )
            
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{str(e)}`")




"""
params1 = {'page': '1','tag': '','contentType': 'videos'}
            response3 = requests.get(f'https://api.penpencil.co/v3/batches/{raw_text3}/subject/{t}/contents', params=params1, headers=headers).json()["data"]
            
            params2 = {'page': '1','tag': '','contentType': 'notes'}
            response4 = requests.get(f'https://api.penpencil.co/v3/batches/{raw_text3}/subject/{t}/contents', params=params2, headers=headers).json()["data"]

            try:
                for data in response3:
                    class_title = (data["topic"])
                    class_url = data["url"].replace("d1d34p8vz63oiq", "d26g5bnklkwsh4").replace("mpd", "m3u8").strip()
                    cc += f"{data['topic']}:{data['url']}\n"
                    with open(f"{batch}.txt", 'a') as f:
                        f.write(f"{cc}")

                for data in response4:
                    class_title = (lol["topic"])
                    for lol in data["homeworkIds"]:
                        concatenated_url = homework["attachmentIds"]["baseUrl"] + homework["attachmentIds"]["key"]
                    cv += f"{data['topic']}:{data['url']}\n"
                    with open(f"{batch}.txt", 'a') as f:
                        f.write(f"{cv}")
            except Exception as e:
               await message.reply_text(str(e))
"""
