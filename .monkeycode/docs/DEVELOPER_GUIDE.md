# 投标参数智能分析 Skill - 开发者指南

## 项目目的

投标参数智能分析 Skill 是基于 MonkeyCode 平台开发的智能投标辅助工具，用于自动化招标文件技术参数评审与投标决策分析。在 MonkeyCode 平台中作为可调用 Skill 模块运行。

**核心职责**:
- 招标文件智能解析（PDF/Word/OCR）
- 产品技术参数符合性自动比对
- 技术得分智能估算
- 投标决策建议与报告生成

## 环境搭建

### 前置条件

- Python >= 3.10
- pip 包管理器
- MonkeyCode 平台运行环境（用于 OCR、docparse、embedding 服务）

### 安装

```bash
# 进入项目目录
cd /workspace/bid-param-analyzer

# 安装依赖
pip install --break-system-packages -r requirements.txt

# 初始化数据库
python -c "from database.migrations import init_db; init_db()"
```

### 配置

| 配置文件 | 说明 |
|---------|------|
| `config/settings.py` | 全局配置：阈值、路径、限制参数 |
| `config/product_lines.yaml` | 产品线参数定义与别名 |
| `config/scoring_templates/` | 评分模板 JSON 文件 |

### 运行

```bash
# 验证配置加载
python -c "from config.settings import *; print('Config loaded OK')"

# 导入产品线参数
python -c "from database.repository import import_from_excel; import_from_excel('path/to/params.xlsx')"
```

## 开发工作流

### 代码质量标准

| 方面 | 标准 |
|------|------|
| 代码风格 | PEP 8 |
| 类型注解 | Python 类型提示 |
| 文档字符串 | 每个公开函数/类 |
| 错误处理 | 明确异常类型 + 用户友好消息 |

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块 | snake_case | `semantic_matcher.py` |
| 类 | PascalCase | `DeviationJudge` |
| 函数/方法 | snake_case | `calculate_similarity()` |
| 常量 | UPPER_SNAKE | `MAX_FILE_SIZE_MB` |

### 提交信息格式

```
feat: xxx         # 新功能
fix: xxx          # 修复
docs: xxx         # 文档
refactor: xxx     # 重构
chore: xxx        # 杂项
```

## 常见任务

### 添加新产品线参数

**需修改的文件**:
1. `config/product_lines.yaml` - 添加产品线定义与参数

**步骤**:
1. 在 YAML 中添加产品线节点，包含 name、parameters 列表
2. 为每个参数编写 aliases（别名列表），确保语义匹配覆盖
3. 设置 deviation_preset（数值范围/枚举值/布尔型/功能描述）

### 添加新评分模板

**需修改的文件**:
1. `config/scoring_templates/` - 添加 JSON 模板文件

**步骤**:
1. 按模板格式创建 JSON 文件
2. 设置 rule_type（quantitative/qualitative）
3. 定义 conditions 或 scoring 规则

### 扩展解析规则

**需修改的文件**:
1. `parsers/table_extractor.py` - 添加新解析规则

**步骤**:
1. 在 `locate_key_sections` 中增加章节关键词匹配
2. 在 `extract_parameters` 中增加参数格式识别
3. 不修改核心比对逻辑（`engine/` 目录）

## 错误处理规范

所有用户可见错误消息 SHALL 包含:
- 错误类别（解析/比对/得分/系统）
- 简要原因说明
- 建议操作

```python
class BidAnalysisError(Exception):
    """投标分析基础异常"""
    def __init__(self, category: str, reason: str, suggestion: str):
        self.category = category
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(f"[{category}] {reason}")
```

## 测试

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定模块测试
python -m pytest tests/test_parsers/
```

### 测试数据

| 目录 | 内容 |
|------|------|
| `tests/fixtures/bid_docs/` | 多格式招标文件样本 |
| `tests/fixtures/product_db/` | 产品参数库样本 |
| `tests/fixtures/scoring_rules/` | 评分规则样本 |
