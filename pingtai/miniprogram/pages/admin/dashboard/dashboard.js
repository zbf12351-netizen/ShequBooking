// pages/admin/dashboard/dashboard.js
const app = getApp()

Page({
  data: {
    statistics: {
      users: { total: 0 },
      facilities: { total: 0 },
      bookings: { total: 0, pending: 0 }
    }
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadStatistics()
  },

  onPullDownRefresh() {
    this.loadStatistics().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadStatistics() {
    try {
      const res = await app.request({
        url: '/admin/statistics/overview'
      })

      if (res.code === 200) {
        this.setData({
          statistics: res.data
        })
      }
    } catch (error) {
      console.error('加载统计数据失败', error)
    }
  },

  goToUsers() {
    wx.navigateTo({
      url: '/pages/admin/users/users'
    })
  },

  goToFacilities() {
    wx.navigateTo({
      url: '/pages/admin/facilities/facilities'
    })
  },

  goToRules() {
    wx.navigateTo({
      url: '/pages/admin/rules/rules'
    })
  },

  goToFeedbacks() {
    wx.navigateTo({
      url: '/pages/admin/feedbacks/feedbacks'
    })
  },

  goToLogs() {
    wx.navigateTo({
      url: '/pages/admin/logs/logs'
    })
  },

  goToNotifications() {
    wx.navigateTo({
      url: '/pages/admin/notifications/notifications'
    })
  },

  goToStatistics() {
    wx.navigateTo({
      url: '/pages/admin/statistics/statistics'
    })
  },

  goToExport() {
    wx.navigateTo({
      url: '/pages/admin/export/export'
    })
  },

  handleLogout() {
    wx.showModal({
      title: '提示',
      content: '确认退出管理员？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          app.globalData.token = null
          app.globalData.userInfo = null
          wx.reLaunch({
            url: '/pages/login/login'
          })
        }
      }
    })
  }
})

