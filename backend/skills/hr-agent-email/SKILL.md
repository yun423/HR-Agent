---
name: hr-agent-email
description: 为本项目中的HR Agent生成、确认和发送HR候选人邮件。适用于撰写面试邀请、笔试通知、候选人跟进邮件，或将草稿转为已确认的发送操作。
---

# HR Agent 邮件 Skill

使用此技能以一致的方式处理本项目的邮件工作流：

1. 生成面向候选人的邮件草稿。
2. 提取或询问收件人、主题和正文。
3. 发送前需要人工确认。
4. 通过配置的发件邮箱发送。

此技能专用于本项目中的HR Agent流程，不适用于其他项目中的通用外发邮件自动化。

## 使用场景

当用户提出以下任意要求时使用此技能：

- 撰写候选人邮件
- 发送面试邀请
- 发送笔试通知
- 通过邮件通知候选人
- 将邮件草稿转为已确认的发送流程
- 添加或修改HR Agent的邮件能力

## 项目工作流

遵循现有项目设计，而不是发明新的智能体框架：

1. 在现有HR Agent中，将邮件视为一个`email_notification`意图。
2. 首先生成草稿。
3. 返回包含`recipient_email`、`subject`和`body`的确认载荷。
4. 仅在得到明确确认后发送。
5. 从[config.txt](config.txt)读取发件邮箱设置。

## 配置文件

将发件邮箱配置存储在：

- [config.txt](config.txt)

将此文件视为本技能唯一的配置来源，包含：

- 发件邮箱地址
- 发件邮箱密码或应用专用密码
- 协议
- IMAP / POP3 服务器设置
- SMTP 服务器设置
- SSL 标志

## 运行时相关文件

优先检查以下文件：

- `backend/app/services/agent_service.py`
- `backend/app/services/agent_skills.py`
- `backend/app/services/email_service.py`
- `frontend/src/views/agent/HRAgent.vue`
- `backend/skills/hr-agent-email/config.txt`

如果需要更多实现细节，请阅读 [references/runtime-surfaces.md](references/runtime-surfaces.md)。

## 输出预期

对于实现工作，请保持流程符合以下形态：

- 草稿阶段输出：
  - `email_draft`
  - `email_send_request`
- 确认阶段输出：
  - `confirmed_requirements.action = "send_email"`
- 发送阶段输出：
  - `email_send_result`

对于解释性工作，请总结：

- 草稿是如何生成的
- 确认载荷是如何构建的
- SMTP 发送是如何触发的
- 发件邮箱配置如何存储在 `backend/skills/hr-agent-email/config.txt` 中
- 当配置或必需字段缺失时会发生什么

## 示例提示

示例 1：
输入：帮我给候选人写一封面试邀请邮件，并且确认后发送
输出：先起草稿，然后确认字段，再执行发送动作

示例 2：
输入：把 HR 智能体的发邮件流程整理成先草稿后确认发送
输出：保留现有的智能体流程，添加确认载荷，保持 SMTP 发送路径

## 注意事项

- 不要在生成草稿后立即自动发送。
- 不要绕过项目现有的 `steps` / `artifacts` / `requires_confirmation` 约定。
- 优先做小改动，保持当前 HR Agent架构不变。
- 将邮箱设置保留在 `backend/skills/hr-agent-email/config.txt` 中。
