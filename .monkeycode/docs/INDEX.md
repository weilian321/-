# 投标参数智能分析智能体 - 文档索引

基于 MonkeyCode 平台开发的自主投标辅助智能体，具备任务规划、工具调度、双层记忆与异常主动交互能力，实现招标文件自动解析、参数自动比对、技术得分估算、投标决策建议。

**快速链接**: [架构](./ARCHITECTURE.md) | [接口](./INTERFACES.md) | [开发者指南](./DEVELOPER_GUIDE.md)

---

## 核心文档

### [架构](./ARCHITECTURE.md)
系统设计、技术栈、项目结构和数据流。了解系统整体设计的起点。

### [接口](./INTERFACES.md)
所有模块的公开 API 接口定义与核心数据模型。集成或开发的参考文档。

### [开发者指南](./DEVELOPER_GUIDE.md)
环境搭建、编码规范、常见任务和错误处理规则。开发人员的必读文档。

---

## 模块

| 模块 | 描述 | README |
|------|------|--------|
| `agent/` | 智能体核心中枢：任务规划、工具调度、记忆系统、异常处理、自校验 | [README](./模块/agent.md) |
| `config/` | 全局配置、产品线定义、评分模板 | [README](./模块/config.md) |
| `parsers/` | 招标文件解析与结构化提取 | [README](./模块/parsers.md) |
| `database/` | SQLite 数据模型与 CRUD | [README](./模块/database.md) |
| `engine/` | 语义匹配、偏离判定、得分计算、决策推理 | [README](./模块/engine.md) |
| `reports/` | 偏离表与投标分析报告生成 | [README](./模块/reports.md) |
| `storage/` | 文件临时存储与历史任务管理 | [README](./模块/storage.md) |

---

## 核心概念

理解这些领域概念有助于导航代码库：

| 概念 | 描述 |
|------|------|
| [招标参数 (ParsedParameter)](./专有概念/招标参数.md) | 从招标文件中提取的结构化技术参数 |
| [产品参数 (ParameterRecord)](./专有概念/产品参数.md) | 产品基准库中存储的自有产品技术参数 |
| [参数偏离](./专有概念/参数偏离.md) | 招标要求与投标响应的差异状态判定 |
| [技术得分](./专有概念/技术得分.md) | 基于评分规则的投标技术得分计算 |
| [投标决策](./专有概念/投标决策.md) | 基于综合分析的三级决策结论 |

---

## 入门指南

### 项目新人

按此路径学习：
1. **[架构](./ARCHITECTURE.md)** - 了解全局设计
2. **[核心概念](#核心概念)** - 学习领域术语
3. **[接口](./INTERFACES.md)** - 理解模块接口
4. **[开发者指南](./DEVELOPER_GUIDE.md)** - 搭建开发环境

### 需要集成

1. **[接口](./INTERFACES.md)** - 模块接口与数据模型
2. **[架构](./ARCHITECTURE.md)** - 系统边界和数据流

### 首次贡献

1. **[开发者指南](./DEVELOPER_GUIDE.md)** - 环境搭建和编码规范
2. **[常见任务](./DEVELOPER_GUIDE.md#常见任务)** - 分步指南

---

## 快速参考

### 命令

```bash
pip install --break-system-packages -r requirements.txt    # 安装依赖
python -c "from database.migrations import init_db; init_db()"  # 初始化数据库
python -m pytest tests/              # 运行测试
```

### 重要文件

| 文件 | 目的 |
|------|------|
| `config/settings.py` | 全局配置项 |
| `config/product_lines.yaml` | 产品线参数定义 |
| `requirements.txt` | Python 依赖声明 |
