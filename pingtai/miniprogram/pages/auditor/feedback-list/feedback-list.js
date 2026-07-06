// pages/auditor/feedback-list/feedback-list.js
const app = getApp()

Page({
  data: {
    feedbacks: [],
    pendingCount: 0,
    repliedCount: 0,
    activeTab: 'pending',
    typeText: {
      consultation: '咨询',
      complaint: '投诉',
      suggestion: '建议'
    }
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadCounts()
    this.loadPendingFeedbacks()
  },

  onShow() {
    this.loadCounts()
  },

  // 下拉刷新
  onPullDownRefresh() {
    // 并行加载统计和列表数据
    Promise.allSettled([
      this.loadCounts(),
      this.data.activeTab === 'pending' ? this.loadPendingFeedbacks() : this.loadRepliedFeedbacks()
    ]).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadCounts() {
    // 并行加载两个统计接口
    Promise.allSettled([
      app.request({ url: '/auditor/feedbacks/pending' }),
      app.request({ url: '/auditor/feedbacks/replied' })
    ]).then(([pendingRes, repliedRes]) => {
      if (pendingRes.status === 'fulfilled' && pendingRes.value.code === 200) {
        this.setData({ pendingCount: pendingRes.value.data.total })
      }
      if (repliedRes.status === 'fulfilled' && repliedRes.value.code === 200) {
        this.setData({ repliedCount: repliedRes.value.data.total })
      }
    }).catch(err => {
      console.error('加载统计数量失败', err)
    })
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    if (tab === this.data.activeTab) return
    
    this.setData({ activeTab: tab })
    
    if (tab === 'pending') {
      this.loadPendingFeedbacks()
    } else {
      this.loadRepliedFeedbacks()
    }
  },

  async loadPendingFeedbacks() {
    try {
      const res = await app.request({
        url: '/auditor/feedbacks/pending'
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

  async loadRepliedFeedbacks() {
    try {
      const res = await app.request({
        url: '/auditor/feedbacks/replied'
      })

      if (res.code === 200) {
        this.setData({
          feedbacks: res.data.feedbacks
        })
      }
    } catch (error) {
      console.error('加载已处理反馈列表失败', error)
    }
  },

  handleReply(e) {
    const id = e.currentTarget.dataset.id
    
    wx.showModal({
      title: '回复反馈',
      content: '请输入回复内容',
      editable: true,
      placeholderText: '请输入回复内容',
      success: async (res) => {
        if (res.confirm) {
          if (!res.content) {
            wx.showToast({ title: '请输入回复内容', icon: 'none' })
            return
          }

          try {
            const result = await app.request({
              url: `/auditor/feedbacks/reply/${id}`,
              method: 'POST',
              data: {
                reply: res.content
              }
            })

            if (result.code === 200) {
              wx.showToast({ title: '回复成功', icon: 'success' })
              this.loadPendingFeedbacks()
            } else {
              wx.showToast({ title: result.message || '回复失败', icon: 'none' })
            }
          } catch (error) {
            wx.showToast({ title: '回复失败', icon: 'none' })
          }
        }
      }
    })
  }
})
