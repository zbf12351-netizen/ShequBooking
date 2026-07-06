// pages/notification-detail/notification-detail.js
const app = getApp()

Page({
  data: {
    notification: {},
    typeNames: {
      booking: '预约',
      audit: '审核',
      system: '系统',
      reminder: '提醒'
    }
  },

  onLoad(options) {
    if (!app.checkLogin()) return
    if (options.id) {
      this.notificationId = options.id
      this.loadNotification(options.id)
    }
  },

  onPullDownRefresh() {
    if (this.notificationId) {
      this.loadNotification(this.notificationId)
    }
  },

  async loadNotification(id) {
    try {
      const res = await app.request({
        url: `/notification/detail/${id}`
      })

      wx.stopPullDownRefresh()

      if (res.code === 200) {
        this.setData({ notification: res.data })

        // 自动标记已读
        if (!res.data.is_read) {
          this.markAsRead(id)
        }
      } else {
        wx.showToast({ title: res.message || '加载失败', icon: 'none' })
      }
    } catch (error) {
      wx.stopPullDownRefresh()
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  async markAsRead(id) {
    try {
      await app.request({
        url: `/notification/read/${id}`,
        method: 'POST'
      })
      // 设置全局刷新标志，通知所有相关页面刷新未读计数
      app.globalData.needUnreadCountRefresh = true
      // 同时清除 TabBar 徽标
      wx.removeTabBarBadge({ index: 3 })
    } catch (error) {
      console.error('标记已读失败', error)
    }
  }
})
