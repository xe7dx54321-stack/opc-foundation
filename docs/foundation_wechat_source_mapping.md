# 微信公众号 Source → WeChat Archive 映射方案

> 版本：1.0  
> 生成时间：2026-06-26  
> 涉及源数：6  
> 状态：设计阶段，待配置验证

## 1. 概述

当前 Source Inventory 中有 6 个微信公众号源，`access_mode` 均为 `manual`，需要映射到 wechat_archive connector 后才能接入。

本文档记录每个微信源的映射设计，包括：
- 公众号名称与账号标识
- 建议映射到的 wechat_archive account_id
- 是否需要新增 account 配置
- 接入优先级建议

---

## 2. 微信源映射清单

| source_id | 公众号名称 | 原 URL 标识 | 建议 account_id | wechat_archive 配置状态 | 接入优先级 | 备注 |
|---|---|---|---|---|---|---|
| goldman_sachs_china_wechat | 高盛中国 | wechat:goldman_sachs_china | gs_china | 待配置 | S | 外资投行中文官方输出，质量高 |
| morgan_stanley_china_wechat | 摩根士丹利中国 | wechat:morgan_stanley_china | ms_china | 待配置 | S | 外资投行中文官方输出 |
| morgan_stanley_fund_wechat | 摩根士丹利基金研究报告 | wechat:morgan_stanley_fund | ms_fund | 待配置 | A | 合资基金研报，有一定价值 |
| yanbaoshe_wechat | 研报社 | wechat:yanbaoshe | yanbaoshe | 待配置 | B | 第三方研报解读，噪音较多 |
| touyan_circle_wechat | 投研圈类账号 | wechat:touyan_circle | touyan_circle | 待配置 | B | 第三方综合，质量参差 |
| wechat_secondary_broadcast | 部分微信公众号二次传播源 | wechat:secondary_broadcast | secondary_broadcast | 待配置 | C | 综合类，需进一步拆分 |

---

## 3. 各源详细说明

### 3.1 goldman_sachs_china_wechat（高盛中国）

- **公众号名称**：高盛中国（Goldman Sachs China）
- **来源机构**：Goldman Sachs 官方
- **内容类型**：宏观研究、市场观点、中国专题
- **建议 account_id**：`gs_china`
- **wechat_archive 配置状态**：待配置（`needs_wechat_account_config`）
- **接入优先级**：S
- **TRAE 试运行候选**：是，配置后可进入
- **备注**：官方账号，内容质量高，合规性好

### 3.2 morgan_stanley_china_wechat（摩根士丹利中国）

- **公众号名称**：摩根士丹利中国
- **来源机构**：Morgan Stanley 官方
- **内容类型**：宏观研究、市场策略、中国观点
- **建议 account_id**：`ms_china`
- **wechat_archive 配置状态**：待配置
- **接入优先级**：S
- **TRAE 试运行候选**：是，配置后可进入
- **备注**：官方账号

### 3.3 morgan_stanley_fund_wechat（摩根士丹利基金研究报告）

- **公众号名称**：摩根士丹利基金
- **来源机构**：摩根士丹利基金（合资）
- **内容类型**：基金研究报告、市场展望
- **建议 account_id**：`ms_fund`
- **wechat_archive 配置状态**：待配置
- **接入优先级**：A
- **TRAE 试运行候选**：第二梯队
- **备注**：合资基金公司，内容偏基金产品

### 3.4 yanbaoshe_wechat（研报社）

- **公众号名称**：研报社
- **来源机构**：第三方自媒体
- **内容类型**：研报解读、市场分析
- **建议 account_id**：`yanbaoshe`
- **wechat_archive 配置状态**：待配置
- **接入优先级**：B
- **TRAE 试运行候选**：暂不优先
- **备注**：第三方账号，内容质量需验证，噪音可能较多

### 3.5 touyan_circle_wechat（投研圈类账号）

- **公众号名称**：投研圈（及类似账号集合）
- **来源机构**：第三方
- **内容类型**：投研资讯、研报转载
- **建议 account_id**：`touyan_circle`
- **wechat_archive 配置状态**：待配置
- **接入优先级**：B
- **TRAE 试运行候选**：暂不优先
- **备注**：内容质量参差，需进一步拆分具体账号

### 3.6 wechat_secondary_broadcast（微信公众号二次传播）

- **公众号名称**：多个二次传播账号（集合）
- **来源机构**：各类自媒体
- **内容类型**：研报二次解读、转载
- **建议 account_id**：`secondary_broadcast`
- **wechat_archive 配置状态**：待配置
- **接入优先级**：C
- **TRAE 试运行候选**：否
- **备注**：此源过于宽泛，建议后续拆分为具体账号

---

## 4. 接入路径建议

### 第一阶段：先配 2 个 S 级官方账号
1. `goldman_sachs_china_wechat` → `gs_china`
2. `morgan_stanley_china_wechat` → `ms_china`

验证 wechat_archive connector 管道和数据质量。

### 第二阶段：再配 A/B 级
3. `morgan_stanley_fund_wechat` → `ms_fund`
4. `yanbaoshe_wechat` → `yanbaoshe`
5. `touyan_circle_wechat` → `touyan_circle`

### 第三阶段：拆分整理
6. `wechat_secondary_broadcast` → 拆分为具体账号后再接入

---

## 5. wechat_archive 配置要求

如果已有 wechat_archive production config，需要为每个公众号新增：

```yaml
accounts:
  - account_id: gs_china
    account_name: 高盛中国
    source_org: Goldman Sachs
    content_type: official_research
    priority: S
```

如果暂无 wechat_archive production config，标记为 `needs_wechat_account_config`，待后续配置。

---

## 6. 风险与注意事项

1. **微信公众号内容版权**：公众号文章版权归原作者所有，仅做元数据索引
2. **内容质量参差**：第三方账号内容质量不如官方，需做过滤
3. **账号迁移风险**：公众号可能改名、迁移或被封，需定期验证
4. **去重需求**：同一篇研报可能被多个公众号转载，需要去重
5. **合规**：遵守微信平台规则和著作权法，不存储全文
