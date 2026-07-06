// pages/auditor/audit-list/audit-list.js
const app = getApp()

Page({
  data: {
    bookings: []
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadPendingBookings()
  },

  onShow() {
    this.loadPendingBookings()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadPendingBookings().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadPendingBookings() {
    try {
      const res = await app.request({
        url: '/auditor/bookings/pending'
      })

      if (res.code === 200) {
        this.setData({
          bookings: res.data.bookings
        })
      }
    } catch (error) {
      console.error('加载待审核列表失败', error)
    }
  },

  handleApprove(e) {
    const id = e.currentTarget.dataset.id
    
    wx.showModal({
      title: '审核通过',
      content: '确认通过此预约？',
      editable: true,
      placeholderText: '可输入审核意见（选填）',
      success: async (res) => {
        if (res.confirm) {
          try {
            const result = await app.request({
              url: `/auditor/bookings/audit/${id}`,
              method: 'POST',
              data: {
                action: 'approve',
                comment: res.content || ''
              }
            })

            if (result.code === 200) {
              wx.showToast({ title: '审核成功', icon: 'success' })
              this.loadPendingBookings()
            } else {
              wx.showToast({ title: result.message || '审核失败', icon: 'none' })
            }
          } catch (error) {
            wx.showToast({ title: '审核失败', icon: 'none' })
          }
        }
      }
    })
  },

  handleReject(e) {
    const id = e.currentTarget.dataset.id
    
    wx.showModal({
      title: '审核拒绝',
      content: '请输入拒绝理由',
      editable: true,
      placeholderText: '请输入拒绝理由',
      success: async (res) => {
        if (res.confirm) {
          if (!res.content) {
            wx.showToast({ title: '请输入拒绝理由', icon: 'none' })
            return
          }

          try {
            const result = await app.request({
              url: `/auditor/bookings/audit/${id}`,
              method: 'POST',
              data: {
                action: 'reject',
                comment: res.content
              }
            })

            if (result.code === 200) {
              wx.showToast({ title: '审核成功', icon: 'success' })
              this.loadPendingBookings()
            } else {
              wx.showToast({ title: result.message || '审核失败', icon: 'none' })
            }
          } catch (error) {
            wx.showToast({ title: '审核失败', icon: 'none' })
          }
        }
      }
    })
  },

  goToAudited() {
    wx.navigateTo({
      url: '/pages/auditor/audited-list/audited-list'
    })
  },

  goToFeedbacks() {
    wx.navigateTo({
      url: '/pages/auditor/feedback-list/feedback-list'
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
          
          wx.reLaunch({
            url: '/pages/login/login'
          })
        }
      }
    })
  }
})

