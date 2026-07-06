// pages/notification-list/notification-list.js
const app = getApp()

Page({
  data: {
    notifications: [],
    page: 1,
    pageSize: 10,
    hasMore: true,
    loading: false,
    unreadCount: 0,
    isFirstLoad: true,  // 标记是否是首次加载
    typeNames: {
      booking: '预约',
      audit: '审核',
      system: '系统',
      reminder: '提醒'
    }
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadNotifications(true)
    this.getUnreadCount()
  },

  onShow() {
    // 如果是首次加载，由 onLoad 负责
    if (this.data.isFirstLoad) {
      return
    }

    // 检测是否有需要刷新的标志
    if (app.globalData.needUnreadCountRefresh) {
      app.globalData.needUnreadCountRefresh = false
      this.loadNotifications(true)  // 强制刷新
      this.getUnreadCount()
    } else {
      this.getUnreadCount()
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.setData({ page: 1 })  // 重置页码
    this.loadNotifications(true).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadNotifications(reset = false) {
    if (this.data.loading) return

    this.setData({ loading: true })

    const page = reset ? 1 : this.data.page

    try {
      const res = await app.request({
        url: '/notification/list',
        data: {
          page,
          page_size: this.data.pageSize
        }
      })

      if (res.code === 200) {
        const newList = reset ? res.data.notifications : [...this.data.notifications, ...res.data.notifications]

        this.setData({
          notifications: newList,
          page: page,
          isFirstLoad: false,  // 标记首次加载完成
          hasMore: newList.length >= this.data.pageSize && (page * this.data.pageSize) < res.data.total,
          loading: false,
          unreadCount: res.data.unread_count || 0
        })
      } else {
        this.setData({ loading: false })
      }
    } catch (error) {
      console.error('加载通知失败', error)
      this.setData({ loading: false })
    }
  },

  loadMore() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({
        page: this.data.page + 1
      })
      this.loadNotifications()
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

        // 更新TabBar徽标
        if (res.data.count > 0) {
          wx.setTabBarBadge({
            index: 3,  // "我的" tab
            text: String(res.data.count)
          })
        } else {
          wx.removeTabBarBadge({ index: 3 })
        }
      }
    } catch (error) {
      console.error('获取未读数量失败', error)
    }
  },

  async markAllRead() {
    wx.showLoading({ title: '正在标记...' })

    try {
      const res = await app.request({
        url: '/notification/read-all',
        method: 'POST'
      })

      wx.hideLoading()

      if (res.code === 200) {
        // 更新列表状态
        const updatedList = this.data.notifications.map(n => ({
          ...n,
          is_read: true
        }))

        this.setData({
          notifications: updatedList,
          unreadCount: 0
        })

        wx.removeTabBarBadge({ index: 3 })
        wx.showToast({ title: '已全部已读', icon: 'success' })

        // 设置刷新标志，通知其他页面
        app.globalData.needUnreadCountRefresh = true
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/notification-detail/notification-detail?id=${id}`
    })
  }
})
