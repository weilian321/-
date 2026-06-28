# config/ 模块

全局配置与产品线参数管理。本项目所有可配置项、产品线定义和评分模板均在此模块中维护。

## 结构

```
config/
├── __init__.py
├── settings.py            # 全局配置项
├── product_lines.yaml     # 产品线参数定义（含别名）
└── scoring_templates/     # 评分模板 JSON 文件
    └── default.json
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `settings.py` | 全局配置：OCR引擎类型、语义匹配阈值(0.85)、文件大小上限(200MB)、数据库路径等 |
| `product_lines.yaml` | 产品线定义：每条产品线包含 id、name、参数模板及别名列表（用于语义匹配） |
| `scoring_templates/default.json` | 默认评分模板及多种预设模板（性能指标、功能清单、加权综合） |

## 依赖

**本模块依赖**: 无

**依赖本模块的**: 所有其他模块（通过 `from config.settings import ...`）

## 规范

### 配置项命名
- 使用 `UPPER_SNAKE_CASE`
- 阈值类: `*_THRESHOLD`
- 超时类: `*_TIMEOUT_SECONDS`
- 路径类: `*_DIR` 或 `*_PATH`

### 产品线 YAML 格式

```yaml
product_lines:
  - id: "pl_xxx"              # 产品线唯一标识
    name: "产品名称"           # 产品线显示名
    description: "描述"
    parameter_categories:      # 参数分类
      - "分类1"
    parameters:
      - name: "参数名称"       # 标准参数名
        unit: "单位"
        category: "分类"
        nominal_value: "标称值"
        acceptable_range: "可满足范围"
        deviation_preset: "数值范围"  # 数值范围/枚举值/布尔型/功能描述
        aliases:               # 语义匹配别名
          - "别名1"
          - "别名2"
```
