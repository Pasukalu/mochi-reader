<div align="center">

<img src="web/whale.png" width="150" alt="鲸鱼娘 · 小汐">

# Mochi Reader · 糯米

**把难懂的，变成你的。**

让鲸鱼娘陪你读懂技术文章：问问题、查原文、做卡片，再检查自己是否读懂。

Python · FastAPI · BM25 RAG · SQLite · Chrome MV3 · 原生 JavaScript

[English](README.en.md) · [快速开始](#快速开始) · [浏览器扩展](#浏览器扩展) · [角色设定](docs/characters.md) · [技术架构](docs/architecture.md) · [求职与改进建议](docs/job-search.md)

</div>

> 第一版 v0.1。无需 API Key 即可体验明确标注的演示模式；配置 DeepSeek 后启用真实模型生成。演示模式与真实模型效果分开呈现。

## 它能做什么

- **把当前材料读明白。** 粘贴技术文章，或通过浏览器扩展主动读取当前页与选中文本。
- **提问时带上证据。** 中英混合词法处理与 BM25 检索相关原文，回答附片段引用，方便回看。
- **把理解留住。** 生成最多 3 张学习卡与 3 道四选一自测题，导出 Markdown。
- **选择你的阅读搭子。** 默认「鲸鱼娘 · 小汐」，也可切换温柔糯米与严谨学姐。角色影响讲解口吻，原文依据与引用规则保持一致。
- **先在本机跑起来。** SQLite 保存阅读材料，前端无需安装依赖或构建，密钥仅在后端配置。

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

### 连接 DeepSeek

无需密钥也可以开始。要启用真实模型，在项目根目录创建 `.env`，写入：

```dotenv
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

保存后重启服务，检查「连接设置」及模式标记。`.env` 已被 Git 忽略，不要将密钥写入前端或提交到仓库。模型名以 [DeepSeek 官方文档](https://api-docs.deepseek.com/quick_start/pricing/) 为准，也可改成自己使用的兼容接口与模型。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 空 | 空值为演示模式，有值为真实模型模式 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | HTTPS API 基础地址，也允许本机 HTTP 兼容服务 |
| `DEEPSEEK_MODEL` | `deepseek-flash` | 提供商接受的模型名 |
| `MOCHI_DB_PATH` | `data/mochi.sqlite3` | 本地数据库路径 |
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

**启用 DeepSeek 后，问题与检索到的相关原文片段会发送至配置的模型提供商。** 本地保存资料不代表模型处理也在本地。网页读取、导入前会提示数据去向；密钥保留在本机后端。

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
