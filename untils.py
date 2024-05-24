import google.generativeai as genai
import asyncio
import edge_tts
import cv2
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
import os
from PIL import Image, ImageDraw, ImageFont
from data import edge_voice_data
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def generate_content(content):
    genai.configure(api_key="AIzaSyArae1nyjhAiRedUMkrUWd7p_-BJglXBNU")
    model = genai.GenerativeModel('gemini-1.0-pro-latest')
    response = model.generate_content(content, safety_settings = [
        {
            "category": "HARM_CATEGORY_DANGEROUS",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
    ])
    return response.text

def generate_to_voice(content, path):
    async def main() -> None:
        c = edge_tts.Communicate(content, edge_voice_data[6], rate="+5%", pitch="+20Hz")
        await c.save(path)
    asyncio.run(main())

def generate_image(link, out_path, out_blur_path):
    response = requests.get(link)
    if response.status_code == 200:
        with open(out_path, "wb") as f:
            f.write(response.content)
    else:
        print("Yêu cầu không thành công. Mã trạng thái:", response.status_code)

    image = cv2.imread(out_path)
    image = cv2.flip(image, 1)
    image = image[150:-150, 150:-150]

    border_thickness = 25
    border_color = (255, 255, 255)
    image = cv2.copyMakeBorder(image, border_thickness, border_thickness, border_thickness, border_thickness, cv2.BORDER_CONSTANT, value=border_color)

    # Làm mờ hình ảnh bằng Blur
    blurred_image = cv2.GaussianBlur(image, (0, 0), 15)

    cv2.imwrite(out_path, image)
    cv2.imwrite(out_blur_path, blurred_image)

def generate_video_by_image(zoom_in, in_path, blur_in_path, out_path, second, gif_path):
    clip_image = ImageClip(in_path).set_duration(second)
    clip_blurred_image = ImageClip(blur_in_path, duration= second).resize((1920, 1080))
    clip_blurred_image = clip_blurred_image.resize(lambda t: 1 + 0.3 * t/second)

    if not zoom_in:
        w_clip_image, h_clip_image = clip_image.size
        percent = (960 / w_clip_image) if (960 / w_clip_image) * h_clip_image < 720 else (720 / h_clip_image)
        clip_image = clip_image.resize((percent * w_clip_image, percent * h_clip_image))
        clip_image = clip_image.resize(lambda t: 1 + 0.4 * t/second)
    else:
        w_clip_image, h_clip_image = clip_image.size
        percent = ((1920 - 60) / w_clip_image) if ((1920 - 60) / w_clip_image) * h_clip_image < 1020 else (1020 / h_clip_image)
        clip_image = clip_image.resize((percent * w_clip_image, percent * h_clip_image))
        clip_image = clip_image.resize(lambda t: 1 - 0.3 * t/second)
    
    # add gif
    gif = VideoFileClip(gif_path, has_mask= True)
    gif = gif.resize((int(1920 * 0.8), int(1080 * 0.8)))
    while gif.duration < second:
        gif = concatenate_videoclips([gif, gif])
    gif = gif.subclip(0, second)

    
    # Tạo avatar clip
    avatar_clip = ImageClip('./public/avatar.png').resize((200, 200))
    avatar_clip = avatar_clip.set_opacity(0.7)
    avatar_clip = avatar_clip.set_position((1650,  50))

    final_clip = CompositeVideoClip([clip_blurred_image.set_position('center'), clip_image.set_position('center'), gif.set_position((0, 250)),  avatar_clip.set_duration(second)])

    final_clip.write_videofile(out_path, fps=24)

def concact_content_videos(audio_path, video_path_list, out_path):
    # Load âm thanh
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    duration_video = 0
    index = 0
    videos = [] 

    while duration_video < audio_duration:
        video = VideoFileClip(video_path_list[index])
        if(duration_video + video.duration > audio_duration):
            duration_end_video =  duration_video + video.duration - audio_duration
            video = video.subclip(0, duration_end_video)
            duration_video += duration_end_video
        else:
            duration_video += video.duration
        videos.append(video)
        if(index + 1 == video_path_list.__len__()):
            index = 0
        else:
            index += 1
    

    # Nối video lại với nhau
    final_video = concatenate_videoclips(videos).subclip(0,audio_duration)
    # Ghép video và âm thanh lại với nhau
    final_video = final_video.set_audio(audio)

    final_video.write_videofile(out_path)

    final_video.close()


def count_folders(path):
    # Kiểm tra xem đường dẫn tồn tại không
    if not os.path.exists(path):
        print("Đường dẫn không tồn tại")
        return
    
    # Đếm số lượng thư mục
    folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    return len(folders)

def generate_thumbnail(img_path, img_blur_path, img_person_path, out_path, text):
    text = text.upper()
    # Mở ảnh thứ nhất (ảnh nền chính)
    background = Image.open(img_path)
    bg_w, bg_h = background.size
    percent = ((1920 - 60) / bg_w) if ((1920 - 60) / bg_w) * bg_h < 1020 else (1020 / bg_h)
    background = background.resize((int(bg_w * percent),int(bg_h * percent)))

    # Mở ảnh thứ hai (ảnh nền phụ) và thay đổi kích thước
    background_2 = Image.open(img_blur_path)
    background_2 = background_2.resize((1920, 1080))

    # Mở ảnh overlay (PNG trong suốt)
    overlay = Image.open(img_person_path)
    overlay = overlay.resize((int(1920 * 0.8), int(1080 * 0.8)))
    overlay2 = Image.open('./public/bar.png')

    # Đảm bảo ảnh overlay có kênh alpha
    if overlay.mode != 'RGBA':
        overlay = overlay.convert('RGBA')

    # Tính toán vị trí để đặt ảnh nền chính vào giữa ảnh nền phụ
    bg2_w, bg2_h = background_2.size
    x = (bg2_w - int(bg_w * percent)) // 2
    y = (bg2_h - int(bg_h * percent)) // 2

    # Dán ảnh nền chính vào giữa ảnh nền phụ
    background_2.paste(background, (x, y))

    # Dán ảnh overlay lên ảnh nền chính
    background_2.paste(overlay, (0, 250), overlay)
    background_2.paste(overlay2, (0, 0), overlay2)
    
       # Thêm văn bản vào ảnh
    draw = ImageDraw.Draw(background_2)
    font = ImageFont.truetype("arial.ttf", 55)  # Đặt font và kích thước font
    max_width = 1350
    lines = []

    # Tách văn bản thành các dòng có độ dài tối đa là 1000 pixel
    words = text.split()
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        test_width = bbox[2] - bbox[0]
        if test_width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    # Tính tổng chiều cao của tất cả các dòng văn bản
    total_text_height = sum(draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines) + (len(lines) - 1) * 5

    # Tính toán vị trí y ban đầu để căn giữa theo chiều dọc
    box_height = 380
    y_text_start = bg2_h - box_height + (box_height - total_text_height) // 2

    # Vẽ các dòng văn bản vào ảnh
    x_text = 480  # Khoảng cách từ trái sang
    y_text = y_text_start

    for line in lines:  # Vẽ từ trên xuống dưới
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1]
        # Vẽ văn bản nhiều lần để làm đậm chữ
        for offset in [
    (0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1), (-1, 1),
    (2, 0), (0, 2), (2, 2), (-2, 0), (0, -2), (-2, -2), (2, -2), (-2, 2)
]:
            draw.text((x_text + offset[0], y_text + offset[1]), line, font=font, fill="white")
        y_text += int(line_height * 1.8)

    # Lưu ảnh kết quả
    background_2.save(out_path)


def upload_yt(chrome_path, user_data_dir, title, description, tags, video_path, video_thumbnail):
    # chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    # user_data_dir = "C:/Path/To/Chrome/news-us"

    subprocess.Popen([chrome_path, f'--remote-debugging-port=9223', f'--user-data-dir={user_data_dir}'])
    time.sleep(5)

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "localhost:9223")

    # Tạo đối tượng driver
    browser = webdriver.Chrome(options=chrome_options)

    browser.get("https://studio.youtube.com/")

    # await browser load end
    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'create-icon'))
    )



    browser.find_element(By.ID, 'create-icon').click()
    time.sleep(1)

    browser.find_element(By.ID, 'text-item-0').click()
    time.sleep(3)

    # upload video
    file_input = browser.find_elements(By.TAG_NAME, 'input')[1]
    file_input.send_keys(video_path)
    time.sleep(3)

    # upload thumbnail
    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'file-loader'))
    )
    thumbnail_input = browser.find_element(By.ID, 'file-loader')
    thumbnail_input.send_keys(video_thumbnail)
    time.sleep(3)

    # enter title
    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'textbox'))
    )
    title_input = browser.find_element(By.ID, 'textbox')
    title_input.clear()
    title_input.send_keys(title)
    time.sleep(1)

    # enter description
    des_input = browser.find_elements(By.ID, 'textbox')[1]
    des_input.clear()
    des_input.send_keys(description)
    time.sleep(1)

    # enter hiển thị thêm
    # Đợi cho phần tử scrollable-content xuất hiện
    scrollable_element = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "scrollable-content"))
    )
    # Scroll xuống cuối cùng của phần tử scrollable-content
    browser.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable_element)
    time.sleep(2)

    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'toggle-button'))
    )
    show_more_btn = browser.find_element(By.ID, 'toggle-button')
    show_more_btn.click()
    time.sleep(2)

    # enter tags
    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'text-input'))
    )
    tags_input = browser.find_element(By.ID, 'text-input')
    tags_input.send_keys(tags)
    time.sleep(2)

    # next btn
    browser.find_element(By.ID, 'next-button').click()
    time.sleep(2)

    # add end screens
    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'endscreens-button'))
    )
    browser.find_element(By.ID, 'endscreens-button').click()
    time.sleep(2)
    canvas_element = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.TAG_NAME, "canvas"))
    )
    browser.execute_script("arguments[0].click();", canvas_element)
    time.sleep(2)
    browser.find_element(By.ID, 'save-button').click()
    time.sleep(4)

    # next
    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'next-button'))
    )
    browser.find_element(By.ID, 'next-button').click()
    time.sleep(2)
    browser.find_element(By.ID, 'next-button').click()
    time.sleep(3)

    # done
    WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.ID, 'done-button'))
    )
    browser.find_element(By.ID, 'done-button').click()

    time.sleep(5)
    browser.quit()
    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], check=True)

