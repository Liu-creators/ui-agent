# UI-Agent

> 🤖 基于 Python 的 UI Agent，使用 LLM + Playwright 控制浏览器，自动完成复杂网页任务。

## 特性

- 🧠 **LLM 驱动**：支持 OpenAI / DeepSeek / Ollama 等多种模型
- 🌐 **浏览器控制**：基于 Playwright，支持截图、点击、输入、滚动等操作
- 🔄 **ReAct 循环**：Thought → Action → Observation 自动推理循环
- 📸 **视觉感知**：支持截图 + DOM 双模式感知页面状态
- 🛡️ **安全机制**：内置敏感操作确认、最大步数限制
- 📝 **任务记忆**：支持多步骤任务的上下文记忆
- 🔌 **可扩展**：工具插件化设计，方便自定义新 Action

## 工程结构

```
ui-agent/
├── main.py                  # 入口：CLI 运行
├── agent/
│   ├── __init__.py
│   ├── agent.py             # 核心 Agent 循环
│   ├── planner.py           # 任务规划器
│   └── memory.py            # 任务记忆模块
├── browser/
│   ├── __init__.py
│   ├── browser_env.py       # 浏览器环境封装
│   └── dom_parser.py        # DOM 解析工具
├── llm/
│   ├── __init__.py
│   ├── base.py              # LLM 基类
│   ├── openai_llm.py        # OpenAI / DeepSeek 接入
│   └── ollama_llm.py        # Ollama 本地模型接入
├── prompts/
│   ├── system_prompt.py     # 核心系统提示词
│   ├── action_prompt.py     # 动作决策提示词
│   └── planner_prompt.py    # 任务规划提示词
├── tools/
│   ├── __init__.py
│   ├── click_tool.py
│   ├── input_tool.py
│   ├── navigate_tool.py
│   ├── scroll_tool.py
│   ├── screenshot_tool.py
│   └── extract_tool.py
├── config/
│   └── config.yaml          # 配置文件
├── examples/
│   ├── search_task.py       # 示例：搜索任务
│   └── form_fill_task.py    # 示例：表单填写
├── requirements.txt
└── .env.example
```

## 快速开始

### 安装

```bash
git clone https://github.com/Liu-creators/ui-agent.git
cd ui-agent
pip install -r requirements.txt
playwright install chromium
```

### 配置

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 运行

```bash
# 执行一个任务
python main.py --task "在百度搜索 Python Playwright 教程，找到第一个结果并提取标题"

# 使用配置文件
python main.py --task "your task" --config config/config.yaml

# 开启 headless 模式
python main.py --task "your task" --headless
```

## 配置说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 (`openai`/`deepseek`/`ollama`) | `openai` |
| `LLM_MODEL` | 模型名称 | `gpt-4o` |
| `MAX_STEPS` | 最大执行步数 | `20` |
| `HEADLESS` | 是否无头模式 | `false` |
| `SCREENSHOT_MODE` | 截图感知模式 | `true` |

## 支持的 Action

| Action | 说明 |
|--------|------|
| `navigate` | 跳转到指定 URL |
| `click` | 点击页面元素 |
| `type` | 输入文本 |
| `scroll` | 滚动页面 |
| `screenshot` | 截图观察当前状态 |
| `extract` | 提取页面文本/元素信息 |
| `wait` | 等待页面加载 |
| `back` | 浏览器后退 |
| `done` | 任务完成 |

## License

MIT
