"""
验证码生成工具模块
"""
import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import base64
from typing import Tuple


def generate_captcha_code(length: int = 4) -> str:
    """
    生成验证码字符串
    
    Args:
        length: 验证码长度，默认4位
    
    Returns:
        验证码字符串
    """
    # 使用数字和大写字母，排除容易混淆的字符
    chars = string.digits + string.ascii_uppercase
    # 排除容易混淆的字符：0, O, 1, I
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    return ''.join(random.choice(chars) for _ in range(length))


def generate_captcha_image(code: str, width: int = 120, height: int = 40) -> str:
    """
    生成验证码图片（Base64编码）
    
    Args:
        code: 验证码字符串
        width: 图片宽度
        height: 图片高度
    
    Returns:
        Base64编码的图片字符串
    """
    # 创建图片
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 尝试加载字体，如果失败则使用默认字体
    try:
        # Windows系统字体路径
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        try:
            # Linux系统字体路径
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
    
    # 绘制干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)), width=1)
    
    # 绘制验证码字符
    char_width = width // len(code)
    for i, char in enumerate(code):
        x = i * char_width + random.randint(5, 15)
        y = random.randint(5, 15)
        # 随机颜色
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x, y), char, font=font, fill=color)
    
    # 添加噪点
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    # 转换为Base64
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

