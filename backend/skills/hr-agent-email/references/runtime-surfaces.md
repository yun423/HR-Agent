# 运行时相关文件

本Skill映射到当前项目中的运行时实现。

## 后端

- `backend/app/services/agent_service.py`
  - 主 HR Agent编排
  - 意图路由
  - 草稿阶段响应
  - 确认阶段处理
  - 发送阶段响应

- `backend/app/services/agent_skills.py`
  - `AgentSkillDispatcher`
  - `AgentSkillBundle`
  - `ScriptedSkillPhase`
  - `skill.json` 清单扫描

- `backend/app/services/email_service.py`
  - `EmailSendService.send_agent_email()`
  - `_send_via_smtp()`

## 前端

- `frontend/src/views/agent/HRAgent.vue`
  - 草稿渲染
  - 邮件确认面板
  - 确认并发送动作
  - `email_confirm` 的消息类型映射

## 关键契约

邮件流程应保留以下设计：

1. 智能体识别 `email_notification` 意图。
2. 首先生成草稿。
3. 前端接收 `email_send_request`。
4. 用户确认或编辑载荷内容。
5. 后端接收 `confirmed_requirements.action = "send_email"`。
6. 仅在此之后才进行 SMTP 发送。

## 技能配置

- `backend/skills/hr-agent-email/config.txt`
  - 为技能包存储发件邮箱配置
  - 包含账号、协议、服务器、端口、密码和 SSL 字段

## 失败处理

预期的失败模式：

- 缺少收件人
- 缺少主题
- 缺少正文
- 缺失或无效的 `backend/skills/hr-agent-email/config.txt`
- 没有可用的 SMTP 配置
- SMTP 登录或发送失败

推荐的处理方式是返回一个包含失败步骤的普通智能体响应，而不是重新设计整个流程。
