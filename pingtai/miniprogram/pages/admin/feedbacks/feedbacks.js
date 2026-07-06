// pages/admin/feedbacks/feedbacks.js
const app = getApp()

Page({
  data: {
    feedbacks: [],
    pendingCount: 0,
    repliedCount: 0,
    activeTab: 'pending',
    typeFilter: '',
    typeText: {
      consultation: '咨询',
      complaint: '投诉',
      suggestion: '建议'
    }
  },

  onLoad: function() {
    if (!app.checkLogin()) return
    this.loadCounts()
    this.loadPendingFeedbacks()
  },

  onShow: function() {
    this.loadCounts()
    if (this.data.activeTab === 'pending') {
      this.loadPendingFeedbacks()
    } else {
      this.loadRepliedFeedbacks()
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.setData({ isRefreshing: true })
    
    // 并行加载统计和列表数据
    Promise.allSettled([
      this.loadCounts(),
      this.data.activeTab === 'pending' ? this.loadPendingFeedbacks() : this.loadRepliedFeedbacks()
    ]).finally(() => {
      wx.stopPullDownRefresh()
      this.setData({ isRefreshing: false })
    })
  },

  async loadCounts() {
    // 并行加载两个统计接口
    Promise.allSettled([
      app.request({ url: '/feedback/pending-count' }),
      app.request({ url: '/feedback/replied-count' })
    ]).then(([pendingRes, repliedRes]) => {
      if (pendingRes.status === 'fulfilled' && pendingRes.value.code === 200) {
        this.setData({ pendingCount: pendingRes.value.data.count })
      }
      if (repliedRes.status === 'fulfilled' && repliedRes.value.code === 200) {
        this.setData({ repliedCount: repliedRes.value.data.count })
      }
    }).catch(err => {
      console.error('加载统计数量失败', err)
    })
  },

  switchTab: function(e) {
    const tab = e.currentTarget.dataset.tab
    if (tab === this.data.activeTab) return
    
    this.setData({ activeTab: tab })
    
    if (tab === 'pending') {
      this.loadPendingFeedbacks()
    } else {
      this.loadRepliedFeedbacks()
    }
  },

  filterByType: function(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ typeFilter: type })
    
    if (this.data.activeTab === 'pending') {
      this.loadPendingFeedbacks()
    } else {
      this.loadRepliedFeedbacks()
    }
  },

  async loadPendingFeedbacks() {
    try {
      let url = '/feedback/pending?all=true'
      if (this.data.typeFilter) {
        url += `&type=${this.data.typeFilter}`
      }
      
      const res = await app.request({
        url: url
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
      let url = '/feedback/replied?all=true'
      if (this.data.typeFilter) {
        url += `&type=${this.data.typeFilter}`
      }
      
      const res = await app.request({
        url: url
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

  handleReply: function(e) {
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
              this.loadCounts()
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
