# HR Agent 前端项目

智能人力资源管理系统前端，基于 Vue 3 + Vite 构建。

## 项目概述

HR Agent 是一个智能化的人力资源管理系统，包含以下核心功能模块：
- 智能招聘：职位描述生成、简历筛选、智能面试
- 智能培训：试卷生成、考试管理
- 知识助理：知识问答、知识库管理
- 系统管理：用户管理、角色权限管理

## 技术栈

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由**: Vue Router
- **UI 组件库**: Element Plus
- **样式**: SCSS
- **HTTP 客户端**: Axios
- **代码规范**: ESLint + Prettier

## 目录结构

```
src/
├── api/           # 接口请求封装
├── assets/        # 静态资源文件
├── layouts/       # 页面布局组件
├── router/        # 路由配置
├── stores/        # 状态管理
├── utils/         # 工具函数
├── views/         # 页面视图
└── App.vue        # 根组件
└── main.js        # 入口文件
```

## 功能模块

### 1. 智能招聘
- JD 生成：自动生成职位描述
- 简历筛选：AI 辅助简历匹配
- 智能面试：自动化面试流程

### 2. 智能培训
- 试卷生成：根据知识点自动生成试卷
- 考试管理：考试发布与结果分析

### 3. 知识助理
- 知识问答：基于知识库的智能问答
- 知识库管理：知识内容维护与分类

### 4. 系统管理
- 用户管理：用户信息维护
- 角色管理：权限控制与分配

## 开发环境

### 环境要求
- Node.js >= 22.x
- npm >= 10.x

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

默认访问地址：http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 代码检查与格式化

```bash
# 代码检查
npm run lint

# 代码格式化
npm run format
```

## 项目配置

### 代理配置
开发环境下，API 请求会代理到 `http://localhost:8000`

### 主要依赖
- vue: 3.4.0
- vue-router: 4.2.5
- pinia: 2.1.7
- element-plus: 2.4.4
- axios: 1.6.2
- echarts: 5.4.3

## 浏览器支持

- Chrome >= 80
- Firefox >= 70
- Safari >= 13
- Edge >= 80

## 部署说明

1. 构建项目：`npm run build`
2. 将 `dist` 目录下的文件部署到 Web 服务器
3. 配置服务器指向 `index.html` 处理 SPA 路由

## 注意事项

1. 开发时请遵循现有代码风格
2. 新增功能需编写对应组件和路由
3. 接口请求统一在 `src/api` 目录下维护
4. 组件命名采用大驼峰命名法
5. 样式使用 SCSS 编写，并遵循 BEM 命名规范