// pages/admin/notifications/notifications.js
const app = getApp()

Page({
  data: {
    title: '',
    content: '',
    notificationTypes: ['系统通知', '预约通知'],
    notificationTypeValues: ['system', 'booking'],
    typeIndex: 0,
    notifications: [],
    page: 1,
    pageSize: 20
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadNotifications()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadNotifications()
    setTimeout(() => {
      wx.stopPullDownRefresh()
    }, 1000)
  },

  onTitleInput(e) {
    this.setData({ title: e.detail.value })
  },

  onContentInput(e) {
    this.setData({ content: e.detail.value })
  },

  onTypeChange(e) {
    this.setData({ typeIndex: e.detail.value })
  },

  async loadNotifications() {
    try {
      const res = await app.request({
        url: '/notification/admin/list'
      })
      
      if (res.code === 200) {
        this.setData({
          notifications: res.data.notifications || []
        })
      }
    } catch (error) {
      console.error('加载通知记录失败', error)
    }
  },

  async handleSubmit() {
    const { title, content, notificationTypeValues, typeIndex } = this.data
    
    if (!title.trim()) {
      wx.showToast({ title: '请输入通知标题', icon: 'none' })
      return
    }
    
    if (!content.trim()) {
      wx.showToast({ title: '请输入通知内容', icon: 'none' })
      return
    }
    
    wx.showLoading({ title: '发布中...' })
    
    try {
      const res = await app.request({
        url: '/notification/admin/publish',
        method: 'POST',
        data: {
          title: title.trim(),
          content: content.trim(),
          type: notificationTypeValues[typeIndex],
          target_type: 'all'
        }
      })
      
      wx.hideLoading()
      
      if (res.code === 200) {
        wx.showToast({
          title: '发布成功',
          icon: 'success'
        })
        
        // 清空表单并刷新列表
        this.setData({
          title: '',
          content: ''
        })
        this.loadNotifications()
      } else {
        wx.showToast({
          title: res.message || '发布失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: '发布失败',
        icon: 'none'
      })
    }
  }
})
