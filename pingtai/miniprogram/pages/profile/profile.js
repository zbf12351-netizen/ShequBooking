// pages/profile/profile.js
const app = getApp()

Page({
  data: {
    userInfo: null,
    isLoggedIn: false,
    unreadCount: 0,
    roleText: {
      resident: '居民用户',
      auditor: '审核员',
      admin: '管理员'
    },
    tabBarConfig: []
  },

  onLoad() {
    // 从全局获取 TabBar 配置
    this.setData({
      tabBarConfig: app.globalData.tabBarConfig
    })
    this.checkLoginStatus()
  },

  onTabChange(e) {
    const { path } = e.detail
    if (path) {
      wx.switchTab({ url: '/' + path })
    }
  },

  onShow() {
    // 每次显示都检查登录状态并刷新未读消息数
    this.checkLoginStatus()

    // 无论登录状态是否变化，都检查是否需要刷新未读消息计数
    if (app.globalData.needUnreadCountRefresh) {
      app.globalData.needUnreadCountRefresh = false
      this.getUnreadCount()
    }
  },

  // 检查登录状态
  checkLoginStatus() {
    const isLoggedIn = !!app.globalData.token
    const userInfo = app.globalData.userInfo
    
    // 无论状态是否变化，都更新数据
    if (isLoggedIn !== this.data.isLoggedIn || 
        JSON.stringify(userInfo) !== JSON.stringify(this.data.userInfo)) {
      this.setData({
        isLoggedIn,
        userInfo
      })
    }
    
    // 登录后获取未读消息数
    if (isLoggedIn) {
      this.getUnreadCount()
    }
  },

  async getUnreadCount() {
    if (!app.globalData.token) return
    
    try {
      const res = await app.request({
        url: '/notification/unread-count'
      })
      
      if (res.code === 200) {
        this.setData({ unreadCount: res.data.count })
      }
    } catch (error) {
      console.error('获取未读消息数量失败', error)
    }
  },

  goToNotifications() {
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/notification-list/notification-list'
      })
    })
  },

  editProfile() {
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/edit-profile/edit-profile'
      })
    })
  },

  goToBookings() {
    app.requireLogin(() => {
      wx.switchTab({
        url: '/pages/booking-list/booking-list'
      })
    })
  },

  goToFeedbacks() {
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/feedback-list/feedback-list'
      })
    })
  },

  goToFavorites() {
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/favorite-list/favorite-list'
      })
    })
  },

  goToAuditor() {
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/auditor/audit-list/audit-list'
      })
    })
  },

  goToAdmin() {
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/admin/dashboard/dashboard'
      })
    })
  },

  changePassword() {
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/change-password/change-password'
      })
    })
  },

  goToLogin() {
    wx.redirectTo({
      url: '/pages/login/login'
    })
  },

  goToRegister() {
    wx.navigateTo({
      url: '/pages/register/register'
    })
  },

  handleLogout() {
    wx.showModal({
      title: '提示',
      content: '确认退出登录？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          app.globalData.token = null
          app.globalData.userInfo = null
          
          this.setData({
            isLoggedIn: false,
            userInfo: null,
            unreadCount: 0
          })
          
          wx.showToast({
            title: '已退出登录',
            icon: 'success'
          })

          // 延迟跳转，避免Toast被覆盖
          setTimeout(() => {
            wx.reLaunch({
              url: '/pages/login/login'
            })
          }, 1500)
        }
      }
    })
  }
})
