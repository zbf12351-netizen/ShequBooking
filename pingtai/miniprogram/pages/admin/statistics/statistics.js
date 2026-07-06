// pages/admin/statistics/statistics.js
const app = getApp()

Page({
  data: {
    period: 'month',
    overview: {
      users: { total: 0 },
      facilities: 0,
      bookings: { total: 0, pending: 0, today_new: 0, today_checkins: 0 }
    },
    bookingStats: {
      total: 0,
      daily: [],
      status_distribution: {}
    },
    facilityUsage: [],
    userActivity: {
      new_users: 0,
      active_users: []
    },
    auditorWorkload: [],
    feedbackStats: {
      total: 0,
      status_distribution: {}
    }
  },

  onLoad: function() {
    this.loadAllStats()
  },

  onShow: function() {
    // 每次显示页面时刷新数据
    this.loadAllStats()
  },

  // 下拉刷新
  onPullDownRefresh: function() {
    this.loadAllStats()
    setTimeout(() => {
      wx.stopPullDownRefresh()
    }, 1000)
  },

  // 设置时间周期
  setPeriod: function(e) {
    const period = e.currentTarget.dataset.period
    this.setData({ period })
    this.loadAllStats()
  },

  // 加载所有统计数据
  loadAllStats: function() {
    this.loadOverview()
    this.loadBookingStats()
    this.loadFacilityUsage()
    this.loadUserActivity()
    this.loadAuditorWorkload()
    this.loadFeedbackStats()
  },

  // 加载数据概览
  loadOverview: function() {
    const token = wx.getStorageSync('token')
    wx.request({
      url: `${app.globalData.baseUrl}/admin/stats/overview`,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData({ overview: res.data.data })
        }
      }
    })
  },

  // 加载预约统计
  loadBookingStats: function() {
    const token = wx.getStorageSync('token')
    const period = this.data.period
    wx.request({
      url: `${app.globalData.baseUrl}/admin/stats/bookings?period=${period}`,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData({ bookingStats: res.data.data })
        }
      }
    })
  },

  // 加载设施使用率
  loadFacilityUsage: function() {
    const token = wx.getStorageSync('token')
    const period = this.data.period
    wx.request({
      url: `${app.globalData.baseUrl}/admin/stats/facilities/usage?period=${period}`,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData({ facilityUsage: res.data.data.rankings || [] })
        }
      }
    })
  },

  // 加载用户活跃度
  loadUserActivity: function() {
    const token = wx.getStorageSync('token')
    const period = this.data.period
    wx.request({
      url: `${app.globalData.baseUrl}/admin/stats/users/activity?period=${period}`,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData({ userActivity: res.data.data })
        }
      }
    })
  },

  // 加载审核员工作量
  loadAuditorWorkload: function() {
    const token = wx.getStorageSync('token')
    const period = this.data.period
    wx.request({
      url: `${app.globalData.baseUrl}/admin/stats/auditors/workload?period=${period}`,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData({ auditorWorkload: res.data.data.auditors || [] })
        }
      }
    })
  },

  // 加载反馈统计
  loadFeedbackStats: function() {
    const token = wx.getStorageSync('token')
    wx.request({
      url: `${app.globalData.baseUrl}/admin/stats/feedbacks`,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData({ feedbackStats: res.data.data })
        }
      }
    })
  }
})
