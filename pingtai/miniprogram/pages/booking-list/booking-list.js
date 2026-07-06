// pages/booking-list/booking-list.js
const app = getApp()

Page({
  data: {
    activeStatus: '',
    bookings: [],
    page: 1,
    pageSize: 20,
    loading: false,
    hasMore: true,
    isFirstLoad: true,  // 标记是否是首次加载
    statusText: {
      draft: '待提交',
      pending: '待审核',
      approved: '已通过',
      rejected: '已拒绝',
      cancelled: '已取消',
      completed: '已完成'
    },
    tabBarConfig: []
  },

  onLoad() {
    // 从全局获取 TabBar 配置
    this.setData({
      tabBarConfig: app.globalData.tabBarConfig
    })
    
    if (!app.checkLogin()) return
    this.loadBookings(true)
  },

  onTabChange(e) {
    const { path } = e.detail
    if (path) {
      wx.switchTab({ url: '/' + path })
    }
  },

  onShow() {
    // 使用防重复机制
    // 如果 isFirstLoad 为 true，说明 onLoad 已经或将要加载数据，跳过 onShow 的加载
    // 只有 isFirstLoad 为 false 且需要刷新时才加载
    if (this.data.isFirstLoad) {
      // 首次加载由 onLoad 负责
      return
    }

    // 检测是否有需要刷新的标志
    const needRefresh = app.globalData.needBookingListRefresh
    if (needRefresh) {
      app.globalData.needBookingListRefresh = false
      this.loadBookings(true)  // 强制刷新
    }
  },

  // 刷新预约列表（供其他页面调用）
  refresh() {
    this.loadBookings(true)
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.setData({ page: 1 })  // 重置页码
    this.loadBookings(true).finally(() => {  // 传 true 表示重置数据
      wx.stopPullDownRefresh()
    })
  },

  async loadBookings(reset = false) {
    if (this.data.loading) return

    this.setData({ loading: true })

    const page = reset ? 1 : this.data.page

    try {
      const res = await app.request({
        url: '/booking/my-bookings',
        data: {
          page,
          page_size: this.data.pageSize,
          status: this.data.activeStatus
        }
      })

      if (res.code === 200) {
        const newBookings = reset ? res.data.bookings : [...this.data.bookings, ...res.data.bookings]
        
        this.setData({
          bookings: newBookings,
          page: page,
          isFirstLoad: false,  // 标记首次加载完成
          hasMore: newBookings.length >= this.data.pageSize && (page * this.data.pageSize) < res.data.total,
          loading: false
        })
      } else {
        this.setData({ loading: false })
      }
    } catch (error) {
      this.setData({ loading: false })
      console.error('加载预约列表失败', error)
    }
  },

  // 加载更多
  loadMore() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({
        page: this.data.page + 1
      })
      this.loadBookings()
    }
  },

  onStatusChange(e) {
    const status = e.currentTarget.dataset.status
    this.setData({
      activeStatus: status,
      page: 1,
      isFirstLoad: true  // 重置为首次加载状态
    })
    this.loadBookings(true)
  },

  viewDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/booking-detail/booking-detail?id=${id}`
    })
  },

  async submitBooking(e) {
    const id = e.currentTarget.dataset.id
    
    wx.showModal({
      title: '提示',
      content: '确认提交此预约？',
      success: async (res) => {
        if (res.confirm) {
          try {
            const result = await app.request({
              url: `/booking/submit/${id}`,
              method: 'POST'
            })
            
            if (result.code === 200) {
              wx.showToast({ title: '提交成功', icon: 'success' })
              this.loadBookings(true)  // 重置数据
            } else {
              wx.showToast({ title: result.message || '提交失败', icon: 'none' })
            }
          } catch (error) {
            wx.showToast({ title: '提交失败', icon: 'none' })
          }
        }
      }
    })
  },

  async cancelBooking(e) {
    const id = e.currentTarget.dataset.id
    
    wx.showModal({
      title: '提示',
      content: '确认取消此预约？',
      success: async (res) => {
        if (res.confirm) {
          try {
            const result = await app.request({
              url: `/booking/cancel/${id}`,
              method: 'POST'
            })
            
            if (result.code === 200) {
              wx.showToast({ title: '取消成功', icon: 'success' })
              this.loadBookings(true)  // 重置数据
            } else {
              wx.showToast({ title: result.message || '取消失败', icon: 'none' })
            }
          } catch (error) {
            wx.showToast({ title: '取消失败', icon: 'none' })
          }
        }
      }
    })
  },

  goToBooking() {
    wx.navigateTo({
      url: '/pages/booking/booking'
    })
  }
})

