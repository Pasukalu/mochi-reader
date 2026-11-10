<div align="center">

<img src="web/whale.png" width="150" alt="鲸鱼娘 · 小汐">

# Mochi Reader · 糯米

**把难懂的，变成你的。**

Mochi Reader：鲸鱼娘陪你读技术文档，网页配置 DeepSeek / 兼容 API，带原文引用的问答、学习卡与自测。

Python · FastAPI · BM25 RAG · SQLite · Chrome MV3 · 原生 JavaScript

[English](README.en.md) · [快速开始](#快速开始) · [浏览器扩展](#浏览器扩展) · [角色设定](docs/characters.md) · [技术架构](docs/architecture.md) · [求职与改进建议](docs/job-search.md)

</div>

> 第一版 v0.1。无需 API Key 即可体验明确标注的演示模式；配置 DeepSeek 后启用真实模型生成。演示模式与真实模型效果分开呈现。

## 它能做什么

- **把当前材料读明白。** 粘贴技术文章，或通过浏览器扩展主动读取当前页与选中文本。
- **提问时带上证据。** 中英混合词法处理与 BM25 检索相关原文，回答附片段引用，方便回看。
- **把理解留住。** 生成最多 3 张学习卡与 3 道四选一自测题，导出 Markdown。
- **选择你的阅读搭子。** 默认「鲸鱼娘 · 小汐」，也可切换温柔糯米与严谨学姐。角色影响讲解口吻，原文依据与引用规则保持一致。
- **在网页连接你的模型。** 在「API 连接设置」填写 API Key、接口地址和模型，保存后立即生效；也可不填密钥直接体验演示模式。
- **先在本机跑起来。** SQLite 保存阅读材料，前端无需安装依赖或构建，模型配置保存在本机服务。

鲸鱼娘的蓝白配色、鲸尾与米饭元素受社区拟人创作启发。「小汐」是本项目为阅读搭子取的别名，不是社区统一名称，也不表示 DeepSeek 官方联名或官方人设。角色与素材说明见 [characters.md](docs/characters.md)。当前没有 Live2D 或语音交互。

## 30 秒演示

启动服务后打开工作台：

1. **0–5 秒**：点击「先试试示例文章」。
2. **5–15 秒**：让鲸鱼娘「讲解重点」，查看回答及其原文依据。
3. **15–25 秒**：点击「生成学习卡」，进入卡片页做一道自测。
4. **25–30 秒**：点击「导出 Markdown」，保存本篇阅读成果。

无密钥时，输出来自原文摘录与固定逻辑，用于演示流程；自然语言讲解效果需配置模型后体验。

## 快速开始

需要 Python 3.11 或更新版本。先下载仓库并进入项目目录。

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

如果系统不允许激活脚本，可以直接使用虚拟环境中的解释器：

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

打开 [http://127.0.0.1:8765](http://127.0.0.1:8765)。保持服务运行，即可使用网页工作台和扩展。

### 在网页连接 DeepSeek / 兼容 API

无需密钥也可以开始。要启用真实模型：

1. 打开网页或扩展中的「API 连接设置」。
2. 填写 **API Key**、**接口 Base URL** 和 **模型**。DeepSeek 默认地址为 `https://api.deepseek.com`，默认模型为 `deepseek-flash`。
3. 保存配置，立即用于后续请求，无需重启服务。
4. 可点击「测试连接」检查模型列表接口是否可用；它只请求提供商的 `GET /models`，不生成回答，也不发送文章。测试通过不代表该模型的生成功能或余额已经验证。

API Key 输入框留空会保留已有密钥；要回到演示模式，请使用显式的「清除密钥」操作。切换服务的域名、协议或端口时，请重新填写该服务的密钥，或显式清除旧密钥。

密钥在保存时经本机服务写入**明文配置文件**，浏览器不会把它存入 `localStorage`，重新打开设置也不会读回完整密钥。配置文件默认与 SQLite 数据库同目录，通常为 `data/provider-settings.json`，已忽略默认 `data/` 目录。

兼容服务需支持 Chat Completions 的 SSE 问答；生成学习卡还需支持 `response_format: {"type":"json_object"}`。填写 API 基础地址（例如服务要求的 `https://…/v1`），应用会在其后请求 `chat/completions` 与 `models`。部分服务不提供模型列表，连接测试失败时可手动检查问答，不能仅据此认定聊天接口不可用。

### 高级选项：环境变量 / .env

也可以在项目根目录创建 `.env`，提供初始默认值：

```dotenv
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

修改环境变量后重启服务。**网页已保存的配置优先于环境变量默认值**，因此修改 `.env` 不会覆盖已保存的网页设置。`.env` 已被 Git 忽略。模型名以 [DeepSeek 官方文档](https://api-docs.deepseek.com/quick_start/pricing/) 为准，兼容接口请使用其支持的地址和模型名。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 空 | 初始密钥；未保存网页配置时，空值为演示模式 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 初始 HTTPS API 基础地址，也允许本机 HTTP 兼容服务 |
| `DEEPSEEK_MODEL` | `deepseek-flash` | 初始模型名 |
| `MOCHI_DB_PATH` | `data/mochi.sqlite3` | 本地数据库路径 |
| `MOCHI_SETTINGS_PATH` | 数据库同目录的 `provider-settings.json` | 可选：覆盖本机模型配置文件位置 |
| `MOCHI_CORS_ORIGINS` | `http://127.0.0.1:8765,http://localhost:8765` | 允许的网页来源，以逗号分隔；使用内置工作台无需修改 |

## 浏览器扩展

需要 Chrome 116 或更新版本。Edge 等 Chromium 浏览器取决于其侧栏 API 支持情况。第一版以未打包扩展方式安装，尚未上架扩展商店。

1. 按上面的步骤启动本机服务。
2. 在项目根目录运行 `python scripts/package_extension.py`，复制共享界面并生成安装包。
3. 打开 `chrome://extensions` 或 `edge://extensions`，开启「开发者模式」。
4. 点击「加载已解压的扩展程序」，选择本仓库的 **`extension` 文件夹**；也可以解压生成的 `dist/mochi-reader-extension.zip` 后加载。
5. 打开要阅读的普通网页，点击扩展图标打开侧栏。
6. 点击「导入阅读材料」→「读取当前网页 / 选中文本」，查看文字后导入。

读取由你主动触发。扩展使用 `activeTab`、`scripting` 与 `sidePanel`，访问服务的权限限于本机，没有 `<all_urls>`。浏览器内部页、商店页等受限制页面可能无法读取，可改用粘贴正文。

修改 `web/` 后重新运行打包脚本，并在扩展管理页刷新。更多细节见 [扩展安装说明](docs/extension.md)。

## 数据去向

阅读正文与来源信息存入本机 SQLite。后端不将问答历史与学习卡保存为长期知识库；具体实现见 [架构文档](docs/architecture.md)。项目不包含遥测。

**启用真实模型后，问题与检索到的相关原文片段会发送至配置的模型提供商。** 本地保存资料不代表模型处理也在本地。网页读取、导入前会提示数据去向；密钥由本机后端保存，并用于向配置的提供商鉴权。网页设置的明文配置文件默认位于 `data/provider-settings.json`。

工作台提供删除文档的入口；本地数据库文件位置由 `MOCHI_DB_PATH` 决定。

## 这个项目体现什么能力

这是一条完整但边界明确的 AI 应用链路：

```text
主动导入 → 原文分块 → 中文 / 英文词项 → BM25 检索
    → 受约束生成 → 引用检查 → 学习卡 / 自测 → Markdown
```

- **检索基线**：中文双字片段与英文词项，纯 Python BM25 排序，保留稳定的片段 ID。
- **应用边界**：输入长度与类型检查、结构化学习内容检查、提供商错误处理。
- **交互实现**：SSE 来源、正文增量与完成事件，原生 ES modules、浏览器侧栏与主动页面读取。
- **可验证性**：本地测试与固定评测样本；演示结果不冒充真实模型质量。

详细取舍见 [技术架构](docs/architecture.md)，选题与竞品来源见 [研究记录](docs/research.md)。求职描述、面试问题和后续实验路线见 [求职与改进建议](docs/job-search.md)。

## 测试与评测

在虚拟环境中执行：

```bash
python -m pytest tests -q
python -m evals.run
python scripts/package_extension.py
```

测试不需要真实 API Key。检索评测使用仓库内固定样本，不能替代真实模型的回答质量与事实性评测。运行条件与指标应和结果一起保留，不把演示模式数字写成模型准确率。

## 已知边界

- 当前是 **BM25 词法 RAG**，没有 embedding、向量索引或 reranker。同义问法、跨语言问题和过短查询可能召回不到证据。
- 引用检查提供可追踪性，不保证回答每个推论都正确；请结合原文核对。
- 问答通过 SSE 逐步接收正文；学习卡在结构校验完成后返回。生成学习内容目前使用前 6 个正文优先片段，长文后部信息可能未覆盖，规则见架构文档。
- 这是个人本机应用，默认绑定 `127.0.0.1`，尚无多用户账户与数据隔离。
- 真实模型调用需要你自己的可用密钥，费用由模型提供商收取；仓库不提供共享密钥。

## License

代码采用 [MIT](LICENSE) © 2026 Pasukalu。糯米 SVG 为本项目原创素材；鲸鱼娘的社区启发与素材来源另见 [角色说明](docs/characters.md)。
