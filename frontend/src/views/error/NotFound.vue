<template>
  <div class="not-found">
    <div class="not-found-container">
      <!-- 404 图标和动画 -->
      <div class="error-visual">
        <div class="error-number">
          <span class="four">4</span>
          <span class="zero">0</span>
          <span class="four">4</span>
        </div>
        
        <div class="error-illustration">
          <svg viewBox="0 0 200 200" class="floating-icon">
            <circle cx="100" cy="100" r="80" fill="none" stroke="var(--primary-light)" stroke-width="2" opacity="0.3"/>
            <circle cx="100" cy="100" r="60" fill="none" stroke="var(--primary)" stroke-width="2" opacity="0.5"/>
            <circle cx="100" cy="100" r="40" fill="var(--primary)" opacity="0.1"/>
            
            <!-- 搜索图标 -->
            <circle cx="85" cy="85" r="20" fill="none" stroke="var(--primary)" stroke-width="3"/>
            <line x1="101" y1="101" x2="115" y2="115" stroke="var(--primary)" stroke-width="3" stroke-linecap="round"/>
            
            <!-- X 标记 -->
            <line x1="75" y1="75" x2="95" y2="95" stroke="var(--danger)" stroke-width="2" stroke-linecap="round"/>
            <line x1="95" y1="75" x2="75" y2="95" stroke="var(--danger)" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
      </div>
      
      <!-- 错误信息 -->
      <div class="error-content">
        <h1 class="error-title">页面未找到</h1>
        <p class="error-description">
          抱歉，您访问的页面不存在或已被移动。
          <br>
          请检查URL是否正确，或返回首页继续浏览。
        </p>
        
        <!-- 可能的原因 -->
        <div class="error-reasons">
          <h3>可能的原因：</h3>
          <ul>
            <li>页面链接已过期或被删除</li>
            <li>URL地址输入错误</li>
            <li>您没有访问此页面的权限</li>
            <li>服务器临时维护中</li>
          </ul>
        </div>
        
        <!-- 操作按钮 -->
        <div class="error-actions">
          <el-button type="primary" size="large" @click="goHome">
            <el-icon><House /></el-icon>
            返回首页
          </el-button>
          
          <el-button size="large" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回上页
          </el-button>
          
          <el-button size="large" @click="refresh">
            <el-icon><Refresh /></el-icon>
            刷新页面
          </el-button>
        </div>
        
        <!-- 快速导航 -->
        <div class="quick-nav">
          <h3>快速导航：</h3>
          <div class="nav-links">
            <router-link to="/dashboard" class="nav-link">
              <el-icon><Monitor /></el-icon>
              <span>工作台</span>
            </router-link>
            
            <router-link to="/recruitment" class="nav-link">
              <el-icon><User /></el-icon>
              <span>智能招聘</span>
            </router-link>
            
            <router-link to="/training" class="nav-link">
              <el-icon><Reading /></el-icon>
              <span>智能培训</span>
            </router-link>
            
            <router-link to="/assistant" class="nav-link">
              <el-icon><ChatDotRound /></el-icon>
              <span>智能助理</span>
            </router-link>
          </div>
        </div>
        
        <!-- 联系支持 -->
        <div class="support-info">
          <p>如果问题持续存在，请联系技术支持：</p>
          <div class="support-contacts">
            <span class="support-item">
              <el-icon><Message /></el-icon>
              support@company.com
            </span>
            <span class="support-item">
              <el-icon><Phone /></el-icon>
              400-123-4567
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 背景装饰 -->
    <div class="background-decoration">
      <div class="decoration-circle circle-1"></div>
      <div class="decoration-circle circle-2"></div>
      <div class="decoration-circle circle-3"></div>
      <div class="decoration-dots">
        <span v-for="i in 20" :key="i" class="dot" :style="getDotStyle(i)"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 方法
const goHome = () => {
  router.push('/dashboard')
}

const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/dashboard')
  }
}

const refresh = () => {
  window.location.reload()
}

const getDotStyle = (index) => {
  const angle = (index * 18) % 360
  const radius = 50 + (index % 3) * 30
  const x = Math.cos(angle * Math.PI / 180) * radius
  const y = Math.sin(angle * Math.PI / 180) * radius
  
  return {
    left: `calc(50% + ${x}px)`,
    top: `calc(50% + ${y}px)`,
    animationDelay: `${index * 0.1}s`
  }
}
</script>

<style lang="scss" scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.not-found-container {
  max-width: 800px;
  width: 100%;
  text-align: center;
  position: relative;
  z-index: 2;
}

.error-visual {
  margin-bottom: 40px;
  
  .error-number {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin-bottom: 30px;
    
    span {
      font-size: 120px;
      font-weight: 800;
      background: linear-gradient(135deg, var(--primary), var(--primary-dark));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      text-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      animation: bounce 2s infinite;
      
      &.zero {
        animation-delay: 0.2s;
      }
      
      &:last-child {
        animation-delay: 0.4s;
      }
    }
  }
  
  .error-illustration {
    display: flex;
    justify-content: center;
    
    .floating-icon {
      width: 200px;
      height: 200px;
      animation: float 3s ease-in-out infinite;
    }
  }
}

.error-content {
  .error-title {
    font-size: 36px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 16px 0;
    animation: fadeInUp 0.8s ease-out;
  }
  
  .error-description {
    font-size: 18px;
    color: var(--text-secondary);
    line-height: 1.6;
    margin: 0 0 32px 0;
    animation: fadeInUp 0.8s ease-out 0.2s both;
  }
  
  .error-reasons {
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin: 32px 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    text-align: left;
    animation: fadeInUp 0.8s ease-out 0.4s both;
    
    h3 {
      margin: 0 0 16px 0;
      color: var(--text-primary);
      font-size: 18px;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
      
      li {
        color: var(--text-secondary);
        margin-bottom: 8px;
        line-height: 1.5;
        
        &:last-child {
          margin-bottom: 0;
        }
      }
    }
  }
  
  .error-actions {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin: 32px 0;
    animation: fadeInUp 0.8s ease-out 0.6s both;
    flex-wrap: wrap;
  }
  
  .quick-nav {
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin: 32px 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    animation: fadeInUp 0.8s ease-out 0.8s both;
    
    h3 {
      margin: 0 0 20px 0;
      color: var(--text-primary);
      font-size: 18px;
      text-align: left;
    }
    
    .nav-links {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      
      .nav-link {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 20px;
        border-radius: 8px;
        background: var(--bg-light);
        color: var(--text-primary);
        text-decoration: none;
        transition: all 0.3s ease;
        border: 2px solid transparent;
        
        &:hover {
          background: var(--primary-light);
          color: var(--primary);
          border-color: var(--primary);
          transform: translateY(-2px);
        }
        
        .el-icon {
          font-size: 24px;
        }
        
        span {
          font-size: 14px;
          font-weight: 500;
        }
      }
    }
  }
  
  .support-info {
    margin-top: 40px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 8px;
    animation: fadeInUp 0.8s ease-out 1s both;
    
    p {
      margin: 0 0 12px 0;
      color: var(--text-secondary);
    }
    
    .support-contacts {
      display: flex;
      justify-content: center;
      gap: 24px;
      flex-wrap: wrap;
      
      .support-item {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--primary);
        font-weight: 500;
        
        .el-icon {
          font-size: 16px;
        }
      }
    }
  }
}

.background-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  
  .decoration-circle {
    position: absolute;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--primary-light), transparent);
    opacity: 0.1;
    animation: rotate 20s linear infinite;
    
    &.circle-1 {
      width: 300px;
      height: 300px;
      top: 10%;
      left: -10%;
      animation-duration: 25s;
    }
    
    &.circle-2 {
      width: 200px;
      height: 200px;
      top: 60%;
      right: -5%;
      animation-duration: 30s;
      animation-direction: reverse;
    }
    
    &.circle-3 {
      width: 150px;
      height: 150px;
      bottom: 20%;
      left: 20%;
      animation-duration: 35s;
    }
  }
  
  .decoration-dots {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    
    .dot {
      position: absolute;
      width: 4px;
      height: 4px;
      background: var(--primary);
      border-radius: 50%;
      opacity: 0.3;
      animation: pulse 2s ease-in-out infinite;
    }
  }
}

// 动画定义
@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-10px);
  }
  60% {
    transform: translateY(-5px);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-20px);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.3;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.2);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .not-found-container {
    padding: 0 16px;
  }
  
  .error-visual .error-number span {
    font-size: 80px;
    gap: 10px;
  }
  
  .error-content {
    .error-title {
      font-size: 28px;
    }
    
    .error-description {
      font-size: 16px;
    }
    
    .error-actions {
      flex-direction: column;
      align-items: center;
      
      .el-button {
        width: 200px;
      }
    }
    
    .quick-nav .nav-links {
      grid-template-columns: repeat(2, 1fr);
    }
    
    .support-info .support-contacts {
      flex-direction: column;
      gap: 12px;
    }
  }
  
  .background-decoration {
    .decoration-circle {
      &.circle-1 {
        width: 200px;
        height: 200px;
      }
      
      &.circle-2 {
        width: 150px;
        height: 150px;
      }
      
      &.circle-3 {
        width: 100px;
        height: 100px;
      }
    }
  }
}

@media (max-width: 480px) {
  .error-visual .error-number span {
    font-size: 60px;
  }
  
  .error-content .error-title {
    font-size: 24px;
  }
  
  .quick-nav .nav-links {
    grid-template-columns: 1fr;
  }
}
</style>