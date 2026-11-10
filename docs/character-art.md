# 鲸鱼娘角色插画

`web/whale.png` 是为本项目新生成的 AI 插画，用作技术阅读搭子的界面角色。它采用社区鲸鱼娘常见的蓝发、鲸尾、蓝白女仆装和白饭意象，结合阅读笔记本；这是原创同人演绎，不是 DeepSeek 官方吉祥物，也不代表官方背书。

制作方式：内置图像生成工具，透明背景模式。没有下载或直接使用社区画师作品作为素材。原始生成图片保留了 RGBA 透明通道，尺寸为 1214 × 1296 像素。

## 最终生成提示词

```text
Use case: stylized-concept.
Asset type: transparent PNG character illustration for a desktop technical-reading companion app.
Primary request: Create an original fan interpretation inspired by the Chinese community DeepSeek whale-girl archetype, never an official mascot. One clearly adult anime woman, cute chibi adult proportions, intelligent playful expression, slight tsundere confidence with warm kindness.
Subject: long flowing rich ocean-blue hair, large blue eyes, a white maid headband, modest elegant blue-and-white maid-style dress with full covered bodice and frilled apron, and one clearly visible blue whale tail. She is reading an open notebook and holds a small white bowl of plain white rice; arrange the notebook on her lap so the hands are anatomically natural.
Style/medium: polished Japanese anime illustration, crisp clean linework, delicate cel shading, expressive face, refined appealing professional app mascot art.
Composition/framing: a single full-body seated character in a gentle three-quarter pose, face looking toward viewer, complete head, hair, tail, hands, skirt and feet fully inside the canvas, comfortable transparent padding, recognizable silhouette even as a small sidebar image.
Color palette: blue and white with a subtle soft mint-green accent; soft gentle light.
Scene/backdrop: genuinely transparent alpha background with nothing behind the character; no floor, no scenery, no enclosing circle or frame.
Constraints: one character only, nonsexual, modest clothing, adult character, natural hands, no readable writing on notebook, no text, no logos, no watermark, no fake checkerboard background. Deliver a real transparent PNG cutout.
```

## 视觉检查

- 蓝色长发、蓝眼、白色发箍、蓝白裙装、鲸尾、饭碗及阅读笔记本齐全。
- 角色为端庄成年动漫形象，完整坐姿，无文字、标识或水印。
- RGBA 透明度范围 0–255，背景真实透明。
- 身体、鞋子和尾鳍可见；顶部发梢与左侧尾鳍接近画布边缘，应用内应使用 `object-fit: contain`，并由布局提供外边距。
