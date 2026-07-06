// pages/auditor/audited-list/audited-list.js
const app = getApp()

Page({
  data: {
    bookings: [],
    page: 1,
    pageSize: 10,
    hasMore: true,
    loading: false,
    status: '',
    statusText: {
      approved: '已通过',
      rejected: '已拒绝',
      completed: '已完成',
      cancelled: '已取消'
    },
    showModal: false,
    currentBookingId: null,
    currentAction: null,
    comment: ''
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadAuditedBookings(true)
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadAuditedBookings(true).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadAuditedBookings(reset = false) {
    if (this.data.loading) return

    this.setData({ loading: true })

    const page = reset ? 1 : this.data.page

    try {
      const res = await app.request({
        url: '/auditor/bookings/audited',
        data: {
          page,
          page_size: this.data.pageSize,
          status: this.data.status === 'exception' ? '' : this.data.status
        }
      })

      if (res.code === 200) {
        let bookings = res.data.bookings
        console.log('[DEBUG] 获取到已审核预约:', bookings)

        // 如果筛选异常预约，需要额外过滤
        if (this.data.status === 'exception') {
          const today = new Date().toISOString().split('T')[0]
          bookings = bookings.filter(b => b.status === 'approved' && b.booking_date < today)
        }

        const newList = reset ? bookings : [...this.data.bookings, ...bookings]

        this.setData({
          bookings: newList,
          page: page,
          hasMore: newList.length < res.data.total && !reset,
          loading: false
        })
      }
    } catch (error) {
      console.error('加载已审核列表失败', error)
      this.setData({ loading: false })
    }
  },

  filterByStatus(e) {
    const status = e.currentTarget.dataset.status
    this.setData({
      status,
      page: 1,
      bookings: [],
      hasMore: true
    })
    this.loadAuditedBookings(true)
  },

  loadMore() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({
        page: this.data.page + 1
      })
      this.loadAuditedBookings()
    }
  },

  showExceptionAction(e) {
    const bookingId = e.currentTarget.dataset.id
    const action = e.currentTarget.dataset.action

    this.setData({
      showModal: true,
      currentBookingId: bookingId,
      currentAction: action,
      comment: ''
    })
  },

  hideModal() {
    this.setData({
      showModal: false,
      currentBookingId: null,
      currentAction: null,
      comment: ''
    })
  },

  onCommentInput(e) {
    this.setData({
      comment: e.detail.value
    })
  },

  async handleException() {
    if (!this.data.currentBookingId) return

    wx.showLoading({ title: '处理中...' })

    try {
      const res = await app.request({
        url: `/auditor/bookings/handle-exception/${this.data.currentBookingId}`,
        method: 'POST',
        data: {
          action: this.data.currentAction,
          comment: this.data.comment || (this.data.currentAction === 'complete' ? '手动标记完成' : '异常取消')
        }
      })

      wx.hideLoading()

      if (res.code === 200) {
        wx.showToast({
          title: '处理成功',
          icon: 'success'
        })

        this.hideModal()
        this.loadAuditedBookings(true)
      } else {
        wx.showToast({
          title: res.message || '处理失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: '处理失败',
        icon: 'none'
      })
    }
  }
})
