<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <el-icon class="logo-icon"><TrendCharts /></el-icon>
          <span v-show="!sidebarCollapsed" class="logo-text">HR Agent</span>
        </div>
      </div>
      
      <nav class="sidebar-nav">
        <el-menu
          :default-active="activeMenu"
          :collapse="sidebarCollapsed"
          :unique-opened="true"
          router
          background-color="transparent"
          text-color="#ffffff"
          active-text-color="#409eff"
        >
          <template v-for="route in menuRoutes" :key="route.path">
            <!-- 单级菜单 -->
            <el-menu-item 
              v-if="!route.children || route.children.length === 0"
              :index="route.path"
              class="menu-item"
            >
              <el-icon><component :is="route.meta.icon" /></el-icon>
              <template #title>{{ route.meta.title }}</template>
            </el-menu-item>
            
            <!-- 多级菜单 -->
            <el-sub-menu 
              v-else
              :index="route.path"
              class="menu-item"
            >
              <template #title>
                <el-icon><component :is="route.meta.icon" /></el-icon>
                <span>{{ route.meta.title }}</span>
              </template>
              <el-menu-item
                v-for="child in route.children"
                :key="child.path"
                :index="child.path"
                class="sub-menu-item"
              >
                {{ child.meta.title }}
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </nav>
    </aside>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 顶部导航栏 -->
      <header class="header">
        <div class="header-left">
          <el-button
            type="text"
            @click="toggleSidebar"
            class="sidebar-toggle"
          >
            <el-icon><Expand v-if="sidebarCollapsed" /><Fold v-else /></el-icon>
          </el-button>
          
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item
              v-for="item in breadcrumbs"
              :key="item.path"
              :to="item.path"
            >
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <!-- 通知 -->
          <el-badge :value="12" class="notification-badge">
            <el-button type="text" class="header-btn">
              <el-icon><Bell /></el-icon>
            </el-button>
          </el-badge>
          
          <!-- 用户菜单 -->
          <el-dropdown @command="handleUserCommand" class="user-dropdown">
            <div class="user-info">
              <el-avatar :size="32" :src="userAvatar">
                <el-icon><User /></el-icon>
              </el-avatar>
              <span class="username">{{ user?.username || '用户' }}</span>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  系统设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="fade">
            <component :is="Component" :key="$route.fullPath" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'
import { TrendCharts, Fold, Expand, Bell, User, Setting, SwitchButton } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 响应式数据
const sidebarCollapsed = ref(false)

// 计算属性
const user = computed(() => authStore.user)
const userAvatar = computed(() => user.value?.avatar_url || '')

// 当前激活的菜单
const activeMenu = computed(() => {
  const matched = route.matched
  if (matched.length > 1) {
    return matched[matched.length - 1].path
  }
  return route.path
})

// 菜单路由
const menuRoutes = computed(() => {
  // 获取主布局下的子路由作为菜单项
  const mainLayoutRoute = router.getRoutes().find(route => route.path === '/')
  if (!mainLayoutRoute || !mainLayoutRoute.children) {
    return []
  }
  
  // 先添加工作台菜单项，然后添加其他菜单项
  const otherRoutes = mainLayoutRoute.children
    .filter(route => 
      route.meta?.title && 
      !route.meta?.hideInMenu &&
      route.path !== 'dashboard' // 工作台单独处理
    )
    .map(route => {
      // 权限：非超级管理员隐藏系统管理
      if (route.path === 'system' && !authStore.isAdminByRole) {
        return null
      }
      // 处理有子路由的菜单项
      if (route.children && route.children.length > 0) {
        return {
          ...route,
          path: `/${route.path}`, // 确保路径正确
          children: route.children
            .filter(child => 
              child.meta?.title && 
              !child.meta?.hideInMenu &&
              child.path !== '' // 过滤掉重定向路由
            )
            .map(child => ({
              ...child,
              path: `/${route.path}/${child.path}` // 构建完整路径
            }))
        }
      }
      return {
        ...route,
        path: `/${route.path}` // 确保路径正确
      }
    })
    .filter(Boolean)

  
  // 工作台菜单项放在最前面
  return [
    {
      path: '/dashboard',
      meta: { 
        title: '工作台',
        icon: 'House'
      }
    },
    ...otherRoutes
  ]
})

// 面包屑导航
const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta && item.meta.title)
  const breadcrumbs = []
  
  // 只显示最后一级路由作为面包屑
  if (matched.length > 0) {
    const lastMatch = matched[matched.length - 1]
    if (lastMatch.path !== '/') {
      breadcrumbs.push({
        path: lastMatch.path,
        title: lastMatch.meta.title
      })
    }
  }
  
  return breadcrumbs
})

// 方法
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const handleUserCommand = async (command) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      // TODO: 实现设置页面
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        authStore.logout()
        router.push('/login')
      } catch {
        // 用户取消
      }
      break
  }
}

// 监听路由变化，自动收起移动端侧边栏
watch(route, () => {
  if (window.innerWidth <= 768) {
    sidebarCollapsed.value = true
  }
})
</script>

<style lang="scss" scoped>
.main-layout {
  display: flex;
  height: 100vh;
  background: var(--bg-color-page);
}

.sidebar {
  width: 240px;
  background: linear-gradient(180deg, #304156 0%, #2c3e50 100%);
  transition: width 0.3s ease;
  overflow: hidden;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  
  &.collapsed {
    width: 64px;
  }
  
  .sidebar-header {
    height: 60px;
    display: flex;
    align-items: center;
    padding: 0 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    
    .logo {
      display: flex;
      align-items: center;
      color: white;
      font-size: 18px;
      font-weight: 600;
      
      .logo-icon {
        font-size: 24px;
        color: #409eff;
        margin-right: 12px;
      }
      
      .logo-text {
        transition: opacity 0.3s ease;
      }
    }
  }
  
  .sidebar-nav {
    height: calc(100% - 60px);
    overflow-y: auto;
    
    :deep(.el-menu) {
      border: none;
      
      .el-menu-item,
      .el-sub-menu__title {
        height: 48px;
        line-height: 48px;
        margin: 4px 12px;
        border-radius: 6px;
        transition: all 0.3s ease;
        
        &:hover {
          background: rgba(255, 255, 255, 0.1);
        }
        
        &.is-active {
          background: var(--primary-color);
          color: white !important;
        }
      }
      
      .el-sub-menu .el-menu-item {
        margin: 2px 12px;
        padding-left: 48px !important;
        height: 40px;
        line-height: 40px;
        
        &.is-active {
          background: rgba(64, 158, 255, 0.2);
        }
      }
    }
  }
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 60px;
  background: white;
  border-bottom: 1px solid var(--border-lighter);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  
  .header-left {
    display: flex;
    align-items: center;
    
    .sidebar-toggle {
      margin-right: 16px;
      font-size: 18px;
      color: var(--text-regular);
      
      &:hover {
        color: var(--primary-color);
      }
    }
    
    .breadcrumb {
      :deep(.el-breadcrumb__item) {
        .el-breadcrumb__inner {
          color: var(--text-regular);
          font-weight: normal;
          
          &:hover {
            color: var(--primary-color);
          }
        }
        
        &:last-child .el-breadcrumb__inner {
          color: var(--text-primary);
          font-weight: 500;
        }
      }
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .notification-badge {
      .header-btn {
        font-size: 18px;
        color: var(--text-regular);
        
        &:hover {
          color: var(--primary-color);
        }
      }
    }
    
    .user-dropdown {
      .user-info {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 6px;
        transition: background 0.3s ease;
        
        &:hover {
          background: var(--bg-color-page);
        }
        
        .username {
          font-size: 14px;
          color: var(--text-primary);
          font-weight: 500;
        }
        
        .dropdown-icon {
          font-size: 12px;
          color: var(--text-secondary);
          transition: transform 0.3s ease;
        }
      }
    }
  }
}

.page-content {
  flex: 1;
  overflow: auto;
  background: var(--bg-color-page);
}

// 响应式设计
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1000;
    height: 100vh;
    
    &.collapsed {
      transform: translateX(-100%);
    }
  }
  
  .main-content {
    margin-left: 0;
  }
  
  .header {
    padding: 0 16px;
    
    .breadcrumb {
      display: none;
    }
  }
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>