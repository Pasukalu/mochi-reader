# 选题研究

核实日期：2026-11-11。这里比较的是项目定位与现有功能，**不保证项目能走红，也不将关注度等同于求职能力**。

## 为什么选择技术阅读助手

| 方向 | 能展示的 AI 应用能力 | 演示亮点 | 本次判断 |
| --- | --- | --- | --- |
| 二次元技术阅读搭子 | 网页抽取、分块检索、结构化生成、引用校验、评测 | 从正在读的文章，到有原文依据的讲解、知识卡与自测 | 第一版选择；视觉易理解，功能闭环可控制 |
| 岗位与真实经历匹配助手 | 文档解析、信息抽取、证据关联、可解释匹配 | 岗位要求逐项对应已有经历与缺口 | 需求明确，但同类较多，还需处理个人信息与文件解析 |
| AI 回答评测工作台 | 数据集、提示词版本、质量指标、延迟与成本比较 | 一次比较多个模型或提示词 | 工程价值高，但面向普通用户的演示门槛较高 |

上表是根据现有项目与实现成本作出的产品判断，不是市场调查或热度预测。

## 已有项目与差异化

- [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) 已提供 Live2D 形象与语音交互。仅增加角色外观，不足以构成本项目的技术区别。
- [Lumio](https://github.com/Iceeeeeeey/lumio) 已有 DeepSeek 阅读侧栏、划词解释、网页总结与术语表。因此 Mochi Reader 将重点放在检索证据、引用检查、学习卡与自测闭环，并提供可复现的本地评测。
- [Page Assist](https://github.com/n4ze3m/page-assist) 已提供本地模型浏览器侧栏。浏览器中使用 AI 并不是新功能，具体阅读流程才是本项目的落点。
- [Resume Matcher](https://github.com/srbhr/Resume-Matcher) 已覆盖简历与职位描述匹配、简历调整和面试准备。若后续选择求职工具方向，应进一步细化到中文技术岗位与真实经历证据。
- [promptfoo](https://github.com/promptfoo/promptfoo) 是现有的 Prompt、Agent 与 RAG 测试工具，可作为后续系统评测的参考。

本项目独立实现，以上项目用于选题比较；没有复制其代码、角色素材或品牌。

## 鲸鱼娘的社区语境

按本项目的产品方向，默认阅读搭子采用「鲸鱼娘 · 小汐」，同时保留糯米与学姐。蓝白配色、鲸尾和米饭元素参考社区拟人创作；「小汐」是项目别名，不能说成社区统一姓名或 DeepSeek 官方人设。

[鲸鱼娘角色图集](https://iphsiibl.github.io/deepseek-whale-girl-gallery/) 记录了视觉元素与作者出处，并标注图集素材的 CC BY-NC-SA 4.0 许可。[社区形象时间线](https://fight.bigbluefish.net/) 整理了角色演变与性格标签，但它不是官方发布，也不能直接据此计算角色的全网热度。本项目没有转载这些页面中的图片。更多取舍见 [角色说明](characters.md)。

角色用于降低技术阅读的距离感；差异化仍需落在证据引用、学习闭环和可重复验证上。角色一致性评测可以作为后续 AI 应用实验，不把“看起来可爱”当成模型质量指标。

## 技术依据

- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)：聊天端点为 `/chat/completions`，使用 API 密钥鉴权。
- [DeepSeek 模型说明](https://api-docs.deepseek.com/quick_start/pricing/)：核实时官方推荐的 Flash 模型名为 `deepseek-flash`。模型名和接口地址应保持可配置，不依赖旧模型别名。
- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)：使用 `response_format: {"type":"json_object"}`，提示词需要包含 JSON 要求和格式示例。仍需处理空内容、截断和应用层字段校验。
- [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)：核实时思考模式默认开启。短任务可以显式关闭，以控制演示延迟；这并不代表关闭思考后质量一定相同。
- [DeepSeek 错误码](https://api-docs.deepseek.com/quick_start/error_codes/)：需区分鉴权、余额、限流和服务端错误。
- [Chrome Side Panel API](https://developer.chrome.com/docs/extensions/reference/api/sidePanel) 与 [activeTab 权限](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab)：支持以浏览器侧栏交互，并在用户主动操作后临时访问当前标签页。
- [SQLite FTS5](https://www.sqlite.org/fts5.html)：官方提供全文检索及 BM25 相关文档，可供后续索引实现对照。当前具体检索实现见项目代码，不应仅凭使用 SQLite 就宣称使用了 FTS5。
- [Ragas Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)：答案是否受到上下文支持，与引用 ID 是否有效是不同的评价问题。

## 第一版的取舍

优先把“导入 → 检索 → 回答 → 查看证据 → 保存学习卡 → 自测 → 导出”做完整。使用可解释的 BM25 词法检索作为基线，不将其描述为向量检索。演示模式可以离线验证操作流程，但不能替代真实模型的质量、延迟或费用评测。

二次元视觉是让流程更容易记住的产品表达。真正值得在面试中展开的是：证据怎样选出来、无关问题怎样处理、输出怎样校验、错误如何呈现，以及评测到底测到了什么。
