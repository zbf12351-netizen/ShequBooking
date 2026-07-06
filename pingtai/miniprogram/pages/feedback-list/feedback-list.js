// pages/feedback-list/feedback-list.js
const app = getApp()

Page({
  data: {
    feedbacks: [],
    isRefreshing: false,  // 下拉刷新状态
    typeText: {
      consultation: '咨询',
      complaint: '投诉',
      suggestion: '建议'
    },
    statusText: {
      pending: '待处理',
      replied: '已回复',
      closed: '已关闭'
    }
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadFeedbacks()
  },

  onShow() {
    this.loadFeedbacks()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.setData({ isRefreshing: true })
    this.loadFeedbacks().finally(() => {
      wx.stopPullDownRefresh()
      this.setData({ isRefreshing: false })
    })
  },

  async loadFeedbacks() {
    try {
      const res = await app.request({
        url: '/feedback/my-feedbacks',
        data: {
          page: 1,
          page_size: 100
        }
      })

      if (res.code === 200) {
        this.setData({
          feedbacks: res.data.feedbacks
        })
      }
    } catch (error) {
      console.error('加载反馈列表失败', error)
    }
  },

  createFeedback() {
    wx.navigateTo({
      url: '/pages/feedback/feedback'
    })
  }
})

