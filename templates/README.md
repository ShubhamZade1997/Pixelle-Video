# HTML Templates Guide

## 📸 Preset Templates

ReelForge provides the following preset templates:

| Template | Style | Preview |
|----------|-------|---------|
| `classic` | Classic black & white, minimalist professional | Clean white background with elegant typography |
| `modern` | Modern gradient with glassmorphism effects | Purple-blue gradient with frosted glass style |
| `minimal` | Minimalist with ample whitespace | Light gray background with refined design |

### Usage

```python
from reelforge.service import reelforge

await reelforge.initialize()

# Use preset template
result = await reelforge.generate_video(
    topic="为什么阅读改变命运",
    frame_template="classic"  # or "modern", "minimal"
)
```

---

## 🎨 Creating Custom Templates

### Method 1: Generate with LLM (Recommended ⭐, Zero Code)

**For users who want unique styles but don't want to write code**

#### Step 1: Open Prompt File

Open [`prompts/generate_html_template.txt`](../prompts/generate_html_template.txt) in the project root directory.

Or view online: [View Prompt File](https://github.com/xxx/ReelForge/blob/main/prompts/generate_html_template.txt)

#### Step 2: Copy Prompt, Modify Style Description

Find this section in the prompt:
```
## Visual Style
[👉 Replace this section with your desired style]
```

Replace with your desired style, for example:
```
## Visual Style
Cyberpunk style with neon lights, dark background, purple and blue gradients
```

#### Step 3: Paste to LLM Platform

Copy the entire prompt and paste it into any of these platforms:
- 💬 ChatGPT: https://chat.openai.com
- 💬 Claude: https://claude.ai
- 💬 Tongyi Qianwen: https://tongyi.aliyun.com
- 💬 DeepSeek: https://chat.deepseek.com
- 💬 Doubao: https://www.doubao.com
- 💬 Or any LLM you prefer

#### Step 4: Save HTML

Copy the HTML code returned by the LLM.

⚠️ **Note:** If the LLM returns HTML wrapped in \`\`\`html\`\`\`, only copy the HTML inside (excluding \`\`\`html and \`\`\`)

Save as:
```
templates/my-cyberpunk.html
```

#### Step 5: Use Template

```python
await reelforge.generate_video(
    topic="...",
    frame_template="my-cyberpunk"  # Use your template
)
```

**🎉 Done! Your video now uses your custom style!**

---

### Example Style Descriptions

Here are some style descriptions you can use or adapt:

- "Cyberpunk style with neon lights, dark background, purple gradient"
- "Fresh and clean style, light blue background, rounded cards, soft shadows"
- "Professional business style, dark blue with gold accents, serious and dignified"
- "Cute cartoon style, pink theme, rounded fonts, rainbow gradient"
- "Vintage retro style, sepia tones, aged paper texture, rounded borders"
- "Tech minimalist style, pure white background, thin borders, subtle animations"
- "Warm reading style, beige background, book texture, soft lighting"

---

### Method 2: Write HTML Manually (Full Control)

**For users familiar with HTML/CSS**

Create an HTML file directly:

```html
<!-- templates/my-style.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            margin: 0;
            width: 1080px;
            height: 1920px;
            background: #ffffff;
            font-family: 'PingFang SC', 'Source Han Sans', 'Microsoft YaHei', sans-serif;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 60px;
            box-sizing: border-box;
        }
        
        .topic {
            font-size: 72px;
            font-weight: bold;
            color: #333;
            text-align: center;
        }
        
        .image-container {
            width: 100%;
            height: 900px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .image-container img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 20px;
        }
        
        .text {
            font-size: 42px;
            color: #666;
            text-align: center;
            line-height: 1.8;
        }
        
        .book-info {
            font-size: 36px;
            color: #999;
            text-align: center;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="topic">{{topic}}</div>
    
    <div class="image-container">
        <img src="{{image}}" alt="Frame Image">
    </div>
    
    <div>
        <div class="text">{{text}}</div>
        <div class="book-info">《{{book_title}}》 - {{book_author}}</div>
    </div>
</body>
</html>
```

**Available Variables:**

Required (always available):
- `{{topic}}` - Video topic
- `{{text}}` - Current frame narration text
- `{{image}}` - AI-generated image path

Optional (available via `ext` parameter):
- `{{book_title}}` - Book title
- `{{book_author}}` - Author
- `{{book_cover}}` - Book cover path
- `{{book_rating}}` - Book rating
- And any other custom fields you pass via `ext`

---

## 🤝 Share Your Templates

Created a beautiful template? Share it with the community!

1. Fork this repository
2. Add your HTML to `templates/community/`
3. Submit a Pull Request

Excellent templates will be featured in the official template gallery!

---

## ❓ FAQ

**Q: What if the HTML generated by LLM has syntax errors?**
A: Regenerate, or emphasize "ensure HTML syntax is correct" in the prompt

**Q: What if I'm not satisfied with the generated style?**
A: Modify the style description in the prompt, or manually edit the HTML file

**Q: Can I use external CSS frameworks (like Tailwind)?**
A: Yes, but you need CDN links. We recommend inline CSS for offline compatibility

**Q: Where should template files be placed?**
A: In the `templates/` directory. The filename is the template name (without .html extension)

**Q: What's the recommended canvas size?**
A: 1080x1920 (9:16 portrait for TikTok/Douyin)

**Q: Can I use custom fonts?**
A: Yes, but system fonts are recommended (PingFang SC, Microsoft YaHei, etc.) for compatibility

---

## 📚 Technical Details

### How HTML Rendering Works

1. Load HTML template file
2. Replace variables (`{{topic}}`, `{{text}}`, etc.) with actual data
3. Render HTML to image using `html2image` (Chrome headless)
4. Save as frame image

### Performance

- First render: ~1-2 seconds (browser initialization)
- Subsequent renders: ~0.5-1 second per frame
- For 5-frame videos: acceptable total time

### Browser Requirements

`html2image` uses Chrome/Chromium headless mode. It will automatically find:
- System Chrome
- System Chromium
- Or download a lightweight browser engine

---

## 💡 Tips

1. **Preview before generating**: Open HTML in browser to preview effect
2. **Maintain aspect ratio**: Keep 1080x1920 for best results
3. **Watch text length**: Ensure long text wraps properly (`word-wrap`, `overflow-wrap`)
4. **Consider contrast**: Ensure text is readable against background
5. **Use relative units**: `%` and `vh/vw` for better responsiveness

---

## 🎨 Inspiration Gallery

Looking for inspiration? Check out:
- [Official Template Gallery](https://reelforge.ai/templates) (coming soon)
- [Community Templates](./community/) (coming soon)
- Design sites: Dribbble, Behance, Pinterest

---

Need help? Open an [Issue](https://github.com/xxx/ReelForge/issues) or join our [Discord](https://discord.gg/xxx)!

