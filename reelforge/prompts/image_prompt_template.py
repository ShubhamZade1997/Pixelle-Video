"""
Image prompt generation template
"""

import json
from typing import List, Optional


# ==================== PRESET IMAGE STYLES ====================
# Predefined visual styles for different use cases

IMAGE_STYLE_PRESETS = {
    "stick_figure": {
        "name": "火柴人简笔画",
        "description": "stick figure style sketch, black and white lines, pure white background, minimalist hand-drawn feel",
        "use_case": "通用场景，简单直观"
    },
    
    "minimal": {
        "name": "极简抽象",
        "description": "minimalist abstract art, geometric shapes, clean composition, modern design, soft pastel colors",
        "use_case": "现代感、艺术感"
    },
    
    "concept": {
        "name": "概念化视觉",
        "description": "conceptual visual metaphors, symbolic elements, thought-provoking imagery, artistic interpretation",
        "use_case": "深度内容、哲学思考"
    },
}

# Default preset
DEFAULT_IMAGE_STYLE = "stick_figure"


IMAGE_PROMPT_GENERATION_PROMPT = """# 角色定位
你是一个专业的视觉创意设计师，擅长为视频脚本创作富有表现力和象征性的图像提示词，将抽象概念转化为具象的视觉画面。

# 核心任务
基于已有的视频脚本，为每个分镜的"旁白内容"创作对应的**英文**图像提示词，确保视觉画面与叙述内容完美配合，增强观众的理解和记忆。

# 输入内容
{narrations_json}

# 输出要求

## 图像提示词规范
- 语言：**必须使用英文**（用于 AI 图像生成模型）
- 画面风格：{style_description}
- 描述结构：scene + character action + emotion + symbolic elements
- 描述长度：确保描述清晰完整且富有创意（建议 50-100 个英文单词）

## 视觉创意要求
- 每个图像都要准确反映对应旁白的具体内容和情感
- 使用象征手法将抽象概念视觉化（如用路径代表人生选择，用锁链代表束缚等）
- 画面要表现出丰富的情感和动作，增强视觉冲击力
- 通过构图和元素安排突出主题，避免过于直白的表现方式

## 关键英文词汇参考
- 象征元素：symbolic elements
- 表情：expression / facial expression
- 动作：action / gesture / movement
- 场景：scene / setting
- 氛围：atmosphere / mood

## 视觉与文案配合原则
- 图像要服务于文案，成为文案内容的视觉延伸
- 避免与文案内容无关或矛盾的视觉元素
- 选择最能增强文案说服力的视觉表现方式
- 确保观众能通过图像快速理解文案的核心观点

## 创意指导
1. **现象描述类文案**：用直观的场景表现社会现象
2. **原因分析类文案**：用因果关系的视觉比喻表现内在逻辑
3. **影响论证类文案**：用后果场景或对比手法表现影响程度
4. **深入探讨类文案**：用抽象概念的具象化表现深刻思考
5. **结论启发类文案**：用开放式场景或指引性元素表现启发性

# 输出格式
严格按照以下JSON格式输出，**图像提示词必须是英文**：

```json
{{
  "image_prompts": [
    "[detailed English image prompt following the style requirements]",
    "[detailed English image prompt following the style requirements]"
  ]
}}
```

# 重要提醒
1. 只输出JSON格式内容，不要添加任何解释说明
2. 确保JSON格式严格正确，可以被程序直接解析
3. 输入是 {{"narrations": [旁白数组]}} 格式，输出是 {{"image_prompts": [图像提示词数组]}} 格式
4. **图像提示词必须使用英文**（for AI image generation models）
5. 图像提示词必须准确反映对应旁白的具体内容和情感
6. 每个图像都要有创意性和视觉冲击力，避免千篇一律
7. 严格遵守上述指定的画面风格要求（{style_description}）
8. 确保视觉画面能增强文案的说服力和观众的理解度

现在，请为上述旁白创作对应的**英文**图像提示词。只输出JSON，不要其他内容。
"""


def build_image_prompt_prompt(
    narrations: List[str],
    min_words: int,
    max_words: int,
    image_style_preset: Optional[str] = None,
    image_style_description: Optional[str] = None
) -> str:
    """
    Build image prompt generation prompt
    
    Args:
        narrations: List of narrations
        min_words: Minimum word count
        max_words: Maximum word count
        image_style_preset: Preset style name (e.g., "minimal", "stick_figure", "concept")
                           Available presets: see IMAGE_STYLE_PRESETS
        image_style_description: Custom style description (overrides preset if provided)
                                Example: "warm scenes, soft lighting, professional photography"
    
    Returns:
        Formatted prompt
    
    Examples:
        # Use preset style
        >>> build_image_prompt_prompt(narrations, 50, 100, image_style_preset="minimal")
        
        # Use custom style
        >>> build_image_prompt_prompt(
        ...     narrations, 50, 100, 
        ...     image_style_description="cyberpunk style, neon colors, futuristic"
        ... )
        
        # Use default style (stick_figure)
        >>> build_image_prompt_prompt(narrations, 50, 100)
    """
    # Determine style description
    if image_style_description:
        # Custom description takes priority
        style_desc = image_style_description
    elif image_style_preset:
        # Use preset
        if image_style_preset not in IMAGE_STYLE_PRESETS:
            raise ValueError(
                f"Unknown preset '{image_style_preset}'. "
                f"Available presets: {list(IMAGE_STYLE_PRESETS.keys())}"
            )
        style_desc = IMAGE_STYLE_PRESETS[image_style_preset]["description"]
    else:
        # Use default preset
        style_desc = IMAGE_STYLE_PRESETS[DEFAULT_IMAGE_STYLE]["description"]
    
    narrations_json = json.dumps(
        {"narrations": narrations},
        ensure_ascii=False,
        indent=2
    )
    
    return IMAGE_PROMPT_GENERATION_PROMPT.format(
        narrations_json=narrations_json,
        min_words=min_words,
        max_words=max_words,
        style_description=style_desc
    )

